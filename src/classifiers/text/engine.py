"""Engine layer.

Owns the model and nothing else. Contract section 5: this layer is fixed, is never
modified, and performs a single forward pass returning typed answers. It has no
notion of conversation, memory, or phrasing.

Import order matters: .config must be imported first so HF_HOME points at the
repo-local weights before huggingface_hub reads it.
"""
from .. import config  # noqa: F401  first import, sets HF_HOME
from .. import gpu

import laya  # noqa: E402
import torch  # noqa: E402

_agent = None


def get_agent():
    """Load the checkpoint on first use, then keep it resident.

    One engine at a time is the design, but the image engine is allowed to be
    resident alongside this one. gpu.ensure_headroom decides who gives way.
    """
    global _agent
    if _agent is None:
        _agent = laya.load(config.TEXT_MODEL_ID, device=config.DEVICE)
    return _agent


def _make_room(needed_mb):
    """Unload the image model if this call needs the VRAM it is holding.

    Imported lazily: the text engine must not drag the image engine in at module
    load, and the image engine imports this module.
    """
    from ..image import engine as image_engine
    if not image_engine.resident():
        return True
    return gpu.ensure_headroom(needed_mb, release=image_engine.release,
                               what="a text call")


def decide(text, questions, max_len=None):
    """One forward pass. Every question in `questions` is answered in that pass.

    Returns the engine's own result dict, unmodified. The agent layer is the only
    thing permitted to interpret it, and it may not alter any value in it.
    """
    kw = {"max_len": max_len or config.MAX_LEN_INTERACTIVE}
    _make_room(gpu.TEXT_HEADROOM_MB)
    return get_agent().predict({"body": text}, questions, **kw)


def decide_batch(texts, questions, max_len=None, batch_size=None):
    """Same questions over many states, sharing forward passes.

    max_len applies per question, so a multi-question call scales memory
    (contract section 5). This is the throughput path: ~9 ms per ticket measured.
    """
    kwargs = {"max_len": max_len or config.MAX_LEN_BATCH}
    if batch_size:
        kwargs["batch_size"] = batch_size
    _make_room(gpu.BATCH_HEADROOM_MB)
    return get_agent().predict_batch([{"body": t} for t in texts], questions, **kwargs)


def diagnostics():
    """Facts about the running engine, for PROJECT_STATE.md and the UI footer."""
    import psutil
    info = {
        "model": config.TEXT_MODEL_ID,
        "device": config.DEVICE,
        "torch": torch.__version__,
        "laya": laya.__version__,
        "cuda_available": torch.cuda.is_available(),
        "threads": config.THREADS,
    }
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        info["gpu"] = torch.cuda.get_device_name(0)
        info["vram_used_mb"] = round((total - free) / 1024**2)
        info["vram_total_mb"] = round(total / 1024**2)
    info["rss_gb"] = round(psutil.Process().memory_info().rss / 1024**3, 2)
    return info
