r"""Generate the synthetic sample images shipped in samples/.

These are drawn by this script, not downloaded, so there is no licensing question
and no third-party photograph in the repository. They are plumbing fixtures: they
prove the attach button, the pipeline and the verdict rendering work end to end.

They are NOT a test of accuracy. A model that calls a flat blue rectangle
"AI-generated" at 99.8% is telling you about its own confidence, not about the
image - which is exactly why no accuracy claim is made anywhere in this project.

Regenerate with:  .venv\Scripts\python.exe tools\make_samples.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "samples"
OUT.mkdir(parents=True, exist_ok=True)


def gradient(name, w, h, stops, bands=0):
    """A smooth vertical gradient, optionally with banding across it."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    top, bottom = stops[0], stops[-1]
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)],
               fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    for b in range(bands):
        x = int(w * (b + 1) / (bands + 1))
        d.line([(x, 0), (x, h)], fill=(255, 255, 255), width=2)
    img.save(OUT / name)
    return name


def concentric(name, size, bg, fg):
    """Concentric rings on a flat ground."""
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    c = min(size) // 2
    for r in range(c - 4, 0, -9):
        d.ellipse([c - r, c - r, c + r, c + r], outline=fg, width=2)
    img.save(OUT / name)
    return name


def noise_field(name, w, h, seed=7):
    """Deterministic pseudo-noise: smooth blobs, no RNG dependency."""
    import math
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = (math.sin(x / 17.0 + seed) * math.cos(y / 23.0 - seed)
                 + math.sin((x + y) / 31.0))
            n = int((v + 2) / 4 * 127)
            px[x, y] = (n, 255 - n, (n * 3) % 256)
    img.save(OUT / name)
    return name


def main():
    made = [
        gradient("gradient_warm.png", 960, 540, [(255, 214, 165), (216, 108, 84), (86, 44, 62)]),
        gradient("gradient_band.png", 800, 800, [(20, 30, 60), (200, 215, 240), (15, 20, 40)],
                 bands=6),
        concentric("rings.png", (700, 700), (250, 248, 242), (40, 44, 52)),
        noise_field("noise_field.png", 640, 480),
    ]
    print(f"  wrote {len(made)} synthetic fixtures to {OUT}")
    for m in made:
        size = (OUT / m).stat().st_size
        print(f"    {m:<22} {size/1024:7.1f} KB")
    print()
    print("  These are generated, not photographs. They exercise the pipeline;")
    print("  they say nothing about accuracy on real images.")


if __name__ == "__main__":
    main()
