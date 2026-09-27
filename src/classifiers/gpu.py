"""VRAM budget guard.

Measured on a 3 GB GTX 1060 (sm_61):

    at rest (CUDA context only)      612 MB
    + laya, 322M text model        1884 MB
    + siglip, 88M image model      2781 MB
    + a 4096-token text call       2988 MB   <- 84 MB free

So both models fit, but only just, and a long text call on top of both is one
allocation away from an out-of-memory crash. This module makes the engine give
way instead: whoever needs the headroom gets it, and the other model is unloaded
and reloaded on demand.

The image model is the one that yields, because it reloads in about 3.5 s against
the text model's 21 s. Keeping the text model resident is the right trade.
"""
import torch

# Free VRAM a text call needs before we will let it run with both models loaded.
TEXT_HEADROOM_MB = 700
# What the text model needs for a 2-question, 2048-per-question batch.
BATCH_HEADROOM_MB = 900


def free_mb():
    if not torch.cuda.is_available():
        return None
    free, _ = torch.cuda.mem_get_info()
    return free / 1024**2


def used_mb():
    if not torch.cuda.is_available():
        return None
    free, total = torch.cuda.mem_get_info()
    return (total - free) / 1024**2


def ensure_headroom(needed_mb, release=None, what="this call"):
    """Make sure `needed_mb` of VRAM is free, calling `release()` if it must.

    `release` is a callable that unloads the other model. Returns True if there
    was room (or the release worked), False only when there is still not enough -
    in which case the caller should surface the problem rather than crash.
    """
    free = free_mb()
    if free is None:
        return True                      # CPU: no budget to manage
    if free >= needed_mb:
        return True
    if release is not None:
        release()
        free = free_mb()
        if free is not None and free >= needed_mb:
            return True
    return False


def report():
    free = free_mb()
    if free is None:
        return "CPU: no VRAM budget"
    return f"{used_mb():.0f} MB used, {free:.0f} MB free"
