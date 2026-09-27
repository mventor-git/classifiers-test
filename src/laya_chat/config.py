"""Configuration.

No version numbers live in this file. Python, CUDA and package versions are pinned
in requirements.lock.txt and selected by setup.cmd. Contract section 6.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
DATA = REPO / ".data" / "huggingface"
VENV = REPO / ".venv"

MODEL_ID = os.getenv("LAYA_MODEL", "convaiinnovations/laya-multilingual")
DEVICE = os.getenv("LAYA_DEVICE", "cuda")
HOST = os.getenv("LAYA_HOST", "127.0.0.1")
PORT = int(os.getenv("LAYA_PORT", "7860"))
API_PORT = int(os.getenv("LAYA_API_PORT", "8000"))
THREADS = os.getenv("LAYA_THREADS", "6")

# Contract section 5, hardware boundary: 1024 interactive, 2048 batch.
# 8192 exhausts the 3 GB card and costs 10 s.
MAX_LEN_INTERACTIVE = int(os.getenv("LAYA_MAX_LEN", "1024"))
MAX_LEN_BATCH = int(os.getenv("LAYA_MAX_LEN_BATCH", "2048"))

# Weights live inside the repo (contract section 6, goal 4). Must be set before
# huggingface_hub is imported anywhere in the process.
os.environ.setdefault("HF_HOME", str(DATA))
os.environ.setdefault("LAYA_THREADS", THREADS)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
