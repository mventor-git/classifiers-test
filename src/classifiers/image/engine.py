"""Image engine - is this image AI-generated or a real photograph?

Contract section 5. Second engine beside the text one. Owns the model and
nothing else: one forward pass per image, in, a label and probabilities out.

Safety: the upstream repository also ships training_args.bin, a pickle the Hub
flags as unsafe. Inference does not need it, and unpickling executes arbitrary
code, so this module downloads an allowlist of three files and never touches a
.bin. See config.IMAGE_ALLOW_PATTERNS.

Honesty about the model: the card reports 99.2% test accuracy and then says
"Some users reported overfitting issues". Treat that number as unproven. This
module reports what the model says; it does not claim the model is right.
"""
from .. import config  # noqa: F401  first import, sets HF_HOME

import io  # noqa: E402
from pathlib import Path  # noqa: E402

import torch  # noqa: E402

_model = None
_processor = None


def available():
    """True when torch sees a usable device. Never raises."""
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def ensure_dependencies():
    """Tell the caller what to install rather than dying with a stack trace."""
    missing = []
    for mod, pip in (("transformers", "transformers"), ("PIL", "pillow")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pip)
    return missing


def fetch_weights():
    """Download only the three files inference needs. Returns the local folder.

    allow_patterns, not ignore_patterns: a blocklist would silently pull any new
    .bin the author adds later.
    """
    from huggingface_hub import snapshot_download
    return snapshot_download(repo_id=config.IMAGE_MODEL_ID,
                             allow_patterns=config.IMAGE_ALLOW_PATTERNS)


def get_model(device=None):
    """Load SigLIP on first use, keep it resident. ~400 MB of VRAM."""
    global _model, _processor
    if _model is not None:
        return _model, _processor
    from transformers import AutoImageProcessor, SiglipForImageClassification

    device = device or config.DEVICE
    _processor = AutoImageProcessor.from_pretrained(config.IMAGE_MODEL_ID)
    _model = SiglipForImageClassification.from_pretrained(config.IMAGE_MODEL_ID)
    _model.to(device)
    _model.eval()
    return _model, _processor


def resident():
    """True when the model is currently holding VRAM."""
    return _model is not None


def release():
    """Free the image model's VRAM. The text model is untouched."""
    global _model, _processor
    model, processor = _model, _processor
    _model = _processor = None
    if model is not None:
        model.to("cpu")
        del model, processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def classify(source, device=None):
    """Classify one image. Returns a dict; raises nothing on a bad file.

    `source` may be a path, raw bytes, or a file-like object, because the UI can
    hand over any of those depending on how the image arrived.
    """
    from PIL import Image, UnidentifiedImageError

    model, processor = get_model(device)
    device = device or config.DEVICE

    try:
        if isinstance(source, (bytes, bytearray)):
            image = Image.open(io.BytesIO(bytes(source)))
        elif isinstance(source, str):
            image = Image.open(source)
        else:
            image = Image.open(source)
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return {"ok": False, "error": f"Not a readable image: {type(exc).__name__}: {exc}"}

    try:
        inputs = processor(images=image, return_tensors="pt").to(device)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Preprocessing failed: {type(exc).__name__}: {exc}"}

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = torch.softmax(logits, dim=-1)[0]
    pairs = {config.IMAGE_LABELS.get(i, str(i)): float(p)
             for i, p in enumerate(probs.tolist())}
    winner, best = max(pairs.items(), key=lambda kv: kv[1])
    return {
        "ok": True,
        "label": winner,
        "confidence": best,
        "probabilities": pairs,
        "size": f"{image.width}x{image.height}",
        "detail": f"224x224 input, resized from {image.width}x{image.height}",
    }


def classify_many(paths, device=None):
    """Classify a list of paths. Bad files are reported, not fatal."""
    out = []
    for p in paths or []:
        result = classify(p, device=device)
        result["path"] = str(p)
        result["name"] = Path(str(p)).name
        out.append(result)
    return out


def diagnostics():
    import psutil
    info = {
        "model": config.IMAGE_MODEL_ID,
        "device": config.DEVICE,
        "torch": torch.__version__,
        "loaded": _model is not None,
        "rss_gb": round(psutil.Process().memory_info().rss / 1024**3, 2),
    }
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        info["gpu"] = torch.cuda.get_device_name(0)
        info["vram_used_mb"] = round((total - free) / 1024**2)
        info["vram_total_mb"] = round(total / 1024**2)
    return info
