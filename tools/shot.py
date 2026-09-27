"""Capture one screenshot with a hard process timeout.

tools/snapshot.py takes four shots and warms the model, which is a long run.
This does exactly one, and kills the browser if it overstays, so a wedged
headless run cannot hang the session.

Usage:  .venv\Scripts\python.exe tools\shot.py light
        .venv\Scripts\python.exe tools\shot.py dark
"""
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

THEME = sys.argv[1] if len(sys.argv) > 1 else "light"
OUT = REPO / "docs" / "screenshots"
PROFILE = OUT / "_brave_profile"
BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
WIDTH, HEIGHT, KILL_AFTER = 1560, 1180, 70000

OUT.mkdir(parents=True, exist_ok=True)
PROFILE.mkdir(parents=True, exist_ok=True)   # never delete: fresh profile hangs

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]

from classifiers.app import build  # noqa: E402

demo = build()
box = {}


def run():
    box["a"] = demo.launch(server_name="127.0.0.1", server_port=port,
                           prevent_thread_lock=True, quiet=True, inbrowser=False,
                           share=False, show_error=False)


threading.Thread(target=run, daemon=True).start()
for _ in range(200):
    if "a" in box:
        break
    time.sleep(0.25)

base = f"http://127.0.0.1:{port}/"
with urllib.request.urlopen(base, timeout=20) as r:
    body = r.read(20000).decode("utf-8", "replace")
if "gradio_config" not in body:
    print("FAIL: page did not render")
    sys.exit(2)
print(f"page ok, shooting {THEME}...")

png = OUT / f"{THEME}.png"
if png.exists():
    png.unlink()

args = (f'--headless=new --disable-gpu --no-first-run --no-default-browser-check '
        f'--disable-extensions --disable-sync --disable-background-networking '
        f'--force-device-scale-factor=1 --user-data-dir="{PROFILE}" '
        f'--window-size={WIDTH},{HEIGHT} --virtual-time-budget=12000 '
        f'--screenshot="{png}" "{base}?__theme={THEME}"')

ok = False
for attempt in (1, 2):
    # No shell=True: with a shell, proc.kill() kills cmd.exe and leaves the
    # browser alive holding the profile lock, which is what wedged this tool.
    proc = subprocess.Popen([BRAVE] + args.split(), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=KILL_AFTER)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
        try:
            proc.wait(timeout=5000)
        except subprocess.TimeoutExpired:
            pass
    if png.exists() and png.stat().st_size > 5000:
        ok = True
        break
    print(f"  attempt {attempt}: browser overstayed {KILL_AFTER/1000:.0f}s, killed")
    time.sleep(4)

for stray in PROFILE.glob("Singleton*"):
    stray.unlink(missing_ok=True)

if ok:
    print(f"OK {png}  {png.stat().st_size/1024:.1f} KB")
    sys.exit(0)
print(f"FAILED: no {THEME}.png")
sys.exit(1)
