r"""Screenshot the real page in both themes, for visual review.

Serves the actual Gradio app on a throwaway port, drives headless Chromium to
capture it, then shuts the server down. Everything terminates inside this one
script - nothing is left listening.

Run:  .venv\Scripts\python.exe tools\snapshot.py
Out:  docs\screenshots\light.png  and  dark.png
"""
import os
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

OUT = REPO / "docs" / "screenshots"
WIDTH, HEIGHT = 1560, 1180

BROWSERS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for p in BROWSERS:
        if Path(p).exists():
            return p
    return None


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(demo, port):
    """Run the real app on a daemon thread via the documented launch().

    create_app() alone leaves the page template without its config and every
    request 500s, so use launch() and let it do the setup. The thread is a
    daemon and this script is one-shot, so nothing survives it.
    """
    import gradio as gr
    box = {}

    def run():
        try:
            box["app"] = demo.launch(server_name="127.0.0.1", server_port=port,
                                     prevent_thread_lock=True, quiet=True,
                                     inbrowser=False, share=False,
                                     show_error=False)
        except Exception as exc:  # noqa: BLE001
            box["error"] = exc

    threading.Thread(target=run, daemon=True).start()
    for _ in range(200):
        if "app" in box or "error" in box:
            break
        time.sleep(0.25)
    if "error" in box:
        raise RuntimeError(f"launch failed: {box['error']}")
    if "app" not in box:
        raise RuntimeError("launch never returned")
    return box["app"]


def shoot(browser, url, png, theme, profile):
    cmd = [
        browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        # No --run-all-compositor-stages-before-draw: it makes headless wait
        # forever on a page with ongoing animations. The combination that
        # reliably terminates is headless=new + a finite virtual-time-budget.
        "--disable-features=Translate,MediaRouter", "--force-device-scale-factor=1",
        f"--user-data-dir={profile}",
        f"--window-size={WIDTH},{HEIGHT}",
        "--virtual-time-budget=12000",
        f"--screenshot={png}",
        url,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        out, err = (res.stdout or "")[-200:], (res.stderr or "")[-300:]
    except subprocess.TimeoutExpired as exc:
        # headless=new sometimes lingers after writing the file; that is fine.
        out = (exc.stdout or b"")[-200:] if isinstance(exc.stdout, bytes) else ""
        err = "timed out (file may still have been written)"
    ok = Path(png).exists() and Path(png).stat().st_size > 5000
    return ok, out, err


def profile_dir():
    """One persistent browser profile, created once and never deleted.

    Brave HANGS in headless on a brand-new profile - it wants to show the
    first-run / shields onboarding, which never completes without a window. An
    existing profile shoots fine. Deleting the profile between shots (an earlier
    version of this file) put every run back into that state.
    """
    p = OUT / "_brave_profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


SHOTS = [
    # name,        theme,  sample index or None, needs the model
    ("light",      "light", None,  False),
    ("dark",       "dark",  None,  False),
    ("light-result", "light", 0,   True),
    ("dark-result",  "dark",  0,   True),
]


def main():
    browser = find_browser()
    if not browser:
        print("FAIL: no Chromium browser found. Looked in:")
        for p in BROWSERS:
            print("   ", p)
        return 2
    print(f"browser: {browser}")

    OUT.mkdir(parents=True, exist_ok=True)
    # The model-backed shots need the real engine, so this runs on the GPU.
    # It loads once and stays resident for the whole run.
    os.environ["LAYA_DEVICE"] = "cuda"
    os.environ["LAYA_THREADS"] = "6"

    from classifiers import engine  # noqa: E402
    from classifiers.app import build  # noqa: E402
    import gradio as gr  # noqa: E402

    print("warming the model up (needed for the result shots)...")
    t0 = time.perf_counter()
    engine.get_agent()
    print(f"  model ready in {time.perf_counter() - t0:.1f} s")

    port = free_port()
    demo = build()
    app = serve(demo, port)
    base = f"http://127.0.0.1:{port}/"
    print(f"serving the real app on {base} (throwaway port)")

    # Prove the page actually answers and carries its config before spending a
    # browser on it. The title sits well past the <head>, so read a real chunk.
    with urllib.request.urlopen(base, timeout=20) as r:
        status = r.status
        page = r.read(20000).decode("utf-8", "replace")
    if status != 200 or "gradio_config" not in page:
        print(f"FAIL: page did not render (status {status}). "
              f"Has gradio_config: {'gradio_config' in page}")
        return 2
    print(f"page responds (HTTP {status}, config embedded)")

    results = []
    prof = str(profile_dir())
    try:
        for name, theme, sample, _needs_model in SHOTS:
            png = OUT / f"{name}.png"
            if png.exists():
                png.unlink()
            url = f"{base}?__theme={theme}"
            if sample is not None:
                url += f"&sample={sample}"
            # Sequential and unhurried: two headless runs cannot share a profile
            # at once, and the first one on a profile always does one-time init.
            time.sleep(2.0)
            ok, out, err = shoot(browser, url, str(png), name, prof)
            if not ok:
                print(f"  {name}: first attempt hung, retrying...")
                time.sleep(4.0)
                ok, out, err = shoot(browser, url, str(png), name, prof)
            size = png.stat().st_size if png.exists() else 0
            results.append((name, ok, size))
            print(f"  {name:<14} {'OK ' if ok else 'FAIL'}  {size/1024:8.1f} KB  {png}")
            if not ok:
                print(f"    stdout: {out}")
                print(f"    stderr: {err}")
    finally:
        # Daemon thread + one-shot script: exiting releases the port.
        print("done - the throwaway server dies with this process")

    if all(ok for _, ok, _ in results):
        print(f"\nall {len(results)} screenshots captured")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
