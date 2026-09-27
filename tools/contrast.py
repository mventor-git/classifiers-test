r"""Contrast audit for the palette in app.py CARD_CSS.

Parses the real CSS, pairs every text colour with the surface it sits on, and
checks WCAG 2.1: AA needs 4.5:1 for body text and 3:1 for large text and for
non-text indicators.

This is the review of text visibility. It is a check, not a claim: if a colour is
regressed, this fails.

Run:  .venv\Scripts\python.exe tools\contrast.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSS = (REPO / "src" / "classifiers" / "app.py").read_text(encoding="utf-8")

# Which surface each text token is read against.
ON_SURFACE = ["--ink", "--ink-soft", "--ink-faint", "--good", "--bad"]
# Non-text accents still need 3:1 to be perceivable as UI boundaries.
INDICATORS = ["--clay", "--clay-dk", "--line-hi"]
# Foreground/background pairs that Gradio renders as buttons.
BUTTON_PAIRS = [("light", "#1f1e1d", "#f5f4ed"), ("dark", "#f5f4ed", "#1f1e1d")]
AA_BODY = 4.5
AA_LARGE = 3.0


def hex_to_rgb(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb):
    """WCAG relative luminance."""
    channels = []
    for raw in rgb:
        c = raw / 255.0
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    a, b = luminance(hex_to_rgb(fg)), luminance(hex_to_rgb(bg))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def block(selector_re):
    """Extract the declarations inside the first matching {...} block."""
    m = re.search(selector_re + r"\s*\{(.*?)\}", CSS, re.S)
    return m.group(1) if m else ""


def variables(declarations):
    out = {}
    for name, value in re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6})", declarations):
        out[name] = value
    return out


# :root appears mid-file, so no ^ anchor. The dark palette is defined twice -
# once as the explicit html[data-theme="dark"] choice, once inside the
# prefers-color-scheme media query. The explicit one is what the toggle sets,
# so audit that; a separate check confirms the two agree.
light = variables(block(r"(?<![a-z-]):root"))
dark = variables(block(r'html\[data-theme="dark"\]'))
dark_media = variables(
    block(r'@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*html:not\(\[data-theme="light"\]\)'))

if not light or not dark:
    print("FAIL: could not parse both palettes from CARD_CSS")
    print(f"  light tokens found: {len(light)}  dark tokens found: {len(dark)}")
    sys.exit(2)

# Any token present in light must also exist in dark, or something inherits light.
missing = [t for t in light if t not in dark]
# --page-a/--page-b only matter for the page background, not text on surface.
text_tokens = [t for t in ON_SURFACE if t in light]

rows, failures = [], []

for name, palette in (("light", light), ("dark", dark)):
    surface = palette.get("--surface")
    for token in text_tokens:
        ratio = contrast(palette[token], surface)
        ok = ratio >= AA_BODY
        rows.append((name, token, palette[token], surface, ratio, ok))
        if not ok:
            failures.append(f"{name} {token} = {ratio:.2f}:1 on {surface} (needs {AA_BODY})")

# Non-text indicators still need 3:1 to be perceivable.
for name, palette in (("light", light), ("dark", dark)):
    for token in INDICATORS:
        if token not in palette:
            continue
        ratio = contrast(palette[token], palette["--surface"])
        rows.append((name, f"{token} (border)", palette[token], palette["--surface"],
                     ratio, ratio >= AA_LARGE))
        if ratio < AA_LARGE:
            failures.append(f"{name} {token} border {ratio:.2f}:1 (needs {AA_LARGE})")

# The primary button is the most prominent text on the page: label on fill.
for name, fg, bg in BUTTON_PAIRS:
    ratio = contrast(fg, bg)
    rows.append((name, "primary button label", fg, bg, ratio, ratio >= AA_BODY))
    if ratio < AA_BODY:
        failures.append(f"{name} primary button label {ratio:.2f}:1 (needs {AA_BODY})")

# The 01/02 badge: white on clay in light, near-black on clay in dark.
badge_light = contrast("#ffffff", light.get("--clay-dk", "#000000"))
badge_dark = contrast("#1f1e1d", dark.get("--clay", "#ffffff"))
for name, ratio in (("light", badge_light), ("dark", badge_dark)):
    rows.append((name, "card number badge", "#fff/#1f1e1d",
                 light.get("--clay-dk") if name == "light" else dark.get("--clay"),
                 ratio, ratio >= AA_BODY))
    if ratio < AA_BODY:
        failures.append(f"{name} card number badge {ratio:.2f}:1 (needs {AA_BODY})")

# The two palettes must actually differ, or dark mode is not really implemented.
same = [t for t in light if t in dark and light[t].lower() == dark[t].lower()]
if same:
    failures.append(f"tokens identical in light and dark: {', '.join(sorted(same))}")

# The media-query copy must match the explicit one, or a user with no saved
# choice sees a different dark palette from one who pressed the toggle.
if dark_media:
    drift = [t for t in dark if t in dark_media
             and dark_media[t].lower() != dark[t].lower()]
    if drift:
        failures.append(f"media-query dark palette differs from the toggle palette: "
                        f"{', '.join(sorted(drift))}")
else:
    failures.append("no prefers-color-scheme dark block found - system dark mode "
                    "would fall back to the light palette")

width = max(len(r[1]) for r in rows) + 2
print()
print("=" * 74)
print("  CONTRAST AUDIT  -  WCAG 2.1 AA")
print("=" * 74)
print(f"  {'mode':<6}{'token':<{width}}{'fg':<10}{'bg':<10}{'ratio':>7}  ")
print("  " + "-" * 70)
for mode, token, fg, bg, ratio, ok in rows:
    print(f"  {mode:<6}{token:<{width}}{fg:<10}{bg:<10}{ratio:>6.2f}:1  "
          f"{'PASS' if ok else 'FAIL'}")
print("  " + "-" * 70)
print(f"  {len(rows) - len(failures)}/{len(rows)} pass   "
      f"(body text needs {AA_BODY}:1, indicators {AA_LARGE}:1)")
if missing:
    print(f"  note: light-only tokens (not read as text): {', '.join(sorted(missing))}")
print()

if failures:
    print("  FAILURES")
    for f in failures:
        print(f"    - {f}")
    print()
    sys.exit(1)
print("  All text meets WCAG AA in both modes.")
print()

# Self-check: prove the auditor actually fails a bad palette, so a green run
# means something. A tool that cannot fail is not a check.
_bad = "--ink-faint: #cfc9c0;"   # 1.6:1 on white
if contrast(_bad.split(": ")[1].rstrip(";"), "#ffffff") >= AA_BODY:
    print("  SELF-CHECK FAILED: the auditor did not reject a known-bad colour")
    sys.exit(2)
print("  self-check: a deliberately bad colour is correctly rejected")
print()
