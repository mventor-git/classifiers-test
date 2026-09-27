"""Configuration.

No version numbers live in this file. Python, CUDA and package versions are pinned
in requirements.lock.txt and selected by installer.ps1. Contract section 6.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
DATA = REPO / ".data" / "huggingface"
VENV = REPO / ".venv"

# ---- text engine ------------------------------------------------------------
TEXT_MODEL_ID = os.getenv("LAYA_MODEL", "convaiinnovations/laya-multilingual")

# ---- image engine -----------------------------------------------------------
IMAGE_MODEL_ID = os.getenv("IMAGE_MODEL", "Ateeqq/ai-vs-human-image-detector")
IMAGE_MODEL_PAGE = "https://huggingface.co/Ateeqq/ai-vs-human-image-detector"
IMAGE_SIZE = 224
# Its config maps class 0 -> "ai" and 1 -> "hum".
IMAGE_LABELS = {0: "ai", 1: "hum"}

# Allowlist, not a blocklist. The model repo also contains training_args.bin, a
# pickle that the Hub flags as unsafe: unpickling it executes arbitrary code, and
# inference does not need it. Fetching only these three files means no pickle ever
# reaches this machine. See contract section 6.
IMAGE_ALLOW_PATTERNS = ["config.json", "preprocessor_config.json", "model.safetensors"]

DEVICE = os.getenv("LAYA_DEVICE", "cuda")
HOST = os.getenv("LAYA_HOST", "127.0.0.1")
PORT = int(os.getenv("LAYA_PORT", "7860"))
API_PORT = int(os.getenv("LAYA_API_PORT", "8000"))
THREADS = os.getenv("LAYA_THREADS", "6")

# ---- which classifier this process is for ------------------------------------
# The user picks at startup. One model at a time is the point: measured, laya at
# 1884 MB and SigLIP at 2781 MB together leave 291 MB, and a 4096-token text call
# on top of both peaks at 2988 of 3072 MB - one allocation from an OOM. Picking
# one avoids the problem instead of managing it. start.ps1 sets this.
MODES = {
    "text":  {"label": "Laya text decisions", "text": True,  "image": False},
    "image": {"label": "AI vs human image detector", "text": False, "image": True},
    "both":  {"label": "Both classifiers", "text": True, "image": True},
}
_raw_mode = (os.getenv("CLASSIFIERS") or "text").strip().lower()
if _raw_mode not in MODES:
    _raw_mode = "text"
APP_MODE = _raw_mode
_CHOSEN = MODES[APP_MODE]
MODE_LABEL = _CHOSEN["label"]
WANT_TEXT = _CHOSEN["text"]
WANT_IMAGE = _CHOSEN["image"]

# Contract section 5, hardware boundary: 1024 interactive, 2048 batch.
# 8192 exhausts the 3 GB card and costs 10 s.
MAX_LEN_INTERACTIVE = int(os.getenv("LAYA_MAX_LEN", "1024"))
MAX_LEN_BATCH = int(os.getenv("LAYA_MAX_LEN_BATCH", "2048"))

# Both models resident at once is the worst case. Measured: laya 2164 MB,
# SigLIP ~400 MB plus a second CUDA context. Over budget on a 3 GB card, so the
# image engine is loaded lazily and unloaded on release (contract section 8).
IMAGE_VRAM_MB = 400

# Weights live inside the repo (contract section 6, goal 4). Must be set before
# huggingface_hub is imported anywhere in the process.
os.environ.setdefault("HF_HOME", str(DATA))
os.environ.setdefault("LAYA_THREADS", THREADS)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
