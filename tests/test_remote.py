r"""Tests for the URL guard. A security control nobody tests is not a control.

These matter more than the rest of the suite combined: the failure mode is a
local app reaching addresses it was never meant to.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from classifiers.image import remote  # noqa: E402


@pytest.mark.parametrize("url,why", [
    ("", "empty"),
    ("   ", "whitespace"),
    ("http://images.unsplash.com/x.jpg", "plain http"),
    ("file:///C:/Windows/win.ini", "local file"),
    ("ftp://images.unsplash.com/x.jpg", "ftp"),
    ("gopher://images.unsplash.com/", "gopher"),
    ("data:image/png;base64,iVBOR", "data uri"),
    ("javascript:alert(1)", "javascript"),
    ("https://user:pass@images.unsplash.com/x.jpg", "embedded credentials"),
    ("https://evil.example.com/x.jpg", "host not on the allowlist"),
    ("https://169.254.169.254/latest/meta-data/", "cloud metadata"),
    ("https://localhost:8000/", "loopback by name"),
    ("https://127.0.0.1/", "loopback literal"),
    ("https://10.0.0.5/x.jpg", "private range"),
    ("https://192.168.1.1/x.jpg", "private range"),
    ("https://[::1]/", "ipv6 loopback"),
    ("x" * 3000, "absurd length"),
])
def test_bad_urls_are_refused(url, why):
    ok, reason = remote.check_url(url)
    assert not ok, f"{why} should have been refused"


def test_public_unsplash_cdn_is_allowed():
    ok, reason = remote.check_url(
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80")
    assert ok, reason


def test_subdomain_suffix_cannot_be_spoofed():
    # "notimages.unsplash.com" must not pass a naive endswith check.
    ok, _ = remote.check_url("https://notimages.unsplash.com.evil.test/x.jpg")
    assert not ok
    ok2, _ = remote.check_url("https://evil-unsplash.com/x.jpg")
    assert not ok2


def test_allowlist_is_narrow_on_purpose():
    assert remote.ALLOWED_HOST_SUFFIXES == (
        "images.unsplash.com", "unsplash.com", "picsum.photos",
        "fastly.picsum.photos")
    assert len(remote.ALLOWED_HOST_SUFFIXES) <= 4


def test_size_cap_is_finite():
    assert remote.MAX_BYTES <= 25 * 1024 * 1024
    assert remote.MAX_REDIRECTS <= 3
    assert remote.TIMEOUT <= 30


def test_no_redirect_handler_is_installed():
    # If this ever goes back to the default opener, redirects would be followed
    # without re-validating each hop.
    handler = remote._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://x/") is None


def test_fetch_raises_value_error_with_a_reason(monkeypatch):
    with pytest.raises(ValueError) as exc:
        remote.fetch("https://evil.example.com/x.jpg")
    assert "allowlist" in str(exc.value)


def test_real_unsplash_fetch_is_an_image():
    """The one network test. Skipped if there is no connection."""
    from PIL import Image
    import io
    url = "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=400&q=70"
    try:
        data, ctype, _ = remote.fetch(url)
    except ValueError as exc:
        pytest.skip(f"no network or blocked: {exc}")
    assert ctype.startswith("image/")
    assert len(data) < remote.MAX_BYTES
    img = Image.open(io.BytesIO(data))
    img.load()          # a truncated download fails here
    assert img.width > 0 and img.height > 0
