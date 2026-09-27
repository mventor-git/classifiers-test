"""Fetch an image from a URL, safely.

The page lets you paste an image URL instead of attaching a file, which is how
Unsplash photos are used here: the repo stores no third-party image, only the
URL, and the bytes are fetched on the user's machine at the moment they ask.

That makes this a server-side request to an address the user typed, which is the
classic SSRF shape. A local app is still a network client: without these guards
someone could point it at 169.254.169.254 (cloud metadata), at 127.0.0.1:8000 (the
app's own admin port), or at a file:// path. So:

  * https only - no http, no file, no ftp, no gopher
  * no credentials embedded in the URL
  * the hostname is resolved and EVERY address it resolves to is checked; if any
    one of them is private, loopback, link-local, reserved or multicast, refuse
  * redirects are followed at most 3 times and each hop is re-validated
  * the body is capped, so a hostile URL cannot stream gigabytes into memory
  * connect and read timeouts, and no cookies or auth headers are ever sent

The allowlist is deliberately narrow. If you want to fetch from a new host, add
it to ALLOWED_HOST_SUFFIXES rather than loosening the checks.
"""
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 20 * 1024 * 1024
MAX_REDIRECTS = 3
TIMEOUT = 20
USER_AGENT = "classifiers-test/2.0 (local image classifier)"

# Hostnames permitted. Images served from the Unsplash CDN, plus a couple of
# well-known developer image hosts. Anything else is refused.
ALLOWED_HOST_SUFFIXES = (
    "images.unsplash.com",
    "unsplash.com",
    "picsum.photos",
    "fastly.picsum.photos",
)

BLOCKED_SCHEMES = ("http:", "file:", "ftp:", "gopher:", "data:", "javascript:")


def _host_ok(host):
    """True only if every address this host resolves to is public."""
    if not host:
        return False, "no host in the URL"
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        return False, f"cannot resolve {host}: {exc.strerror or exc}"
    if not infos:
        return False, f"cannot resolve {host}"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False, (f"{host} resolves to {ip}, which is not a public "
                           f"address. Refusing to fetch it.")
    return True, None


def check_url(url):
    """Validate without fetching. Returns (ok, reason)."""
    raw = (url or "").strip()
    if not raw:
        return False, "no URL given"
    if len(raw) > 2048:
        return False, "URL is unreasonably long"
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError as exc:
        return False, f"not a usable URL: {exc}"
    if parts.scheme.lower() in BLOCKED_SCHEMES or parts.scheme.lower() != "https":
        return False, "only https:// URLs are accepted"
    if parts.username or parts.password:
        return False, "URLs with embedded credentials are refused"
    host = (parts.hostname or "").lower()
    if not any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES):
        return False, (f"{host or 'that host'} is not on the allowlist. "
                       f"Add it to image/remote.py if you trust it.")
    return _host_ok(host)


def fetch(url):
    """Return (bytes, content_type, final_url). Raises ValueError with a reason."""
    current = (url or "").strip()
    for _ in range(MAX_REDIRECTS + 1):
        ok, why = check_url(current)
        if not ok:
            raise ValueError(why)
        req = urllib.request.Request(current, headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/*",
        })
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(req, timeout=TIMEOUT) as resp:
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                if not ctype.startswith("image/"):
                    raise ValueError(f"that URL returned {ctype or 'no type'}, "
                                     f"not an image")
                data = resp.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError(f"image is larger than "
                                     f"{MAX_BYTES // (1024 * 1024)} MB")
                if not data:
                    raise ValueError("the URL returned an empty body")
                return data, ctype, current
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    raise ValueError(f"redirect {exc.code} with no target")
                current = urllib.parse.urljoin(current, location)
                continue
            raise ValueError(f"the server returned HTTP {exc.code}") from None
        except urllib.error.URLError as exc:
            raise ValueError(f"could not reach the host: {exc.reason}") from None
    raise ValueError(f"too many redirects (limit {MAX_REDIRECTS})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Surface redirects instead of following them, so each hop is re-checked."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
