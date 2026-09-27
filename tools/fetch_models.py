r"""Fetch both models, and say clearly which are already on disk.

Idempotent. A model already present is reported and left alone unless
CLASSIFIERS_FORCE=1, so re-running installer.ps1 costs a second, not 1 GB.

The image model is fetched with a three-file allowlist, not a blocklist. Its
repository also ships training_args.bin, a pickle the Hub flags as unsafe;
unpickling executes arbitrary code and inference does not need it. An allowlist
means no pickle reaches this machine even if the author adds another .bin later.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FORCE = os.environ.get("CLASSIFIERS_FORCE") == "1"
HF_HOME = Path(os.environ.setdefault(
    "HF_HOME", str(Path(__file__).resolve().parents[1] / ".data" / "huggingface")))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from huggingface_hub import snapshot_download  # noqa: E402
from huggingface_hub.utils import LocalEntryNotFoundError  # noqa: E402

from classifiers import config  # noqa: E402

# name -> (repo id, human size, allowlist, page)
MODELS = [
    ("text", config.TEXT_MODEL_ID, "~647 MB",
     None,  # the laya loader fetches its own files; no allowlist needed
     "https://huggingface.co/convaiinnovations/laya-multilingual"),
    ("image", config.IMAGE_MODEL_ID, "~363 MB",
     config.IMAGE_ALLOW_PATTERNS, config.IMAGE_MODEL_PAGE),
]


def folder_for(repo_id):
    slug = "models--" + repo_id.replace("/", "--")
    return HF_HOME / "hub" / slug / "snapshots"


def present(repo_id, allow):
    """Is a usable copy already on disk?"""
    d = folder_for(repo_id)
    if not d.is_dir():
        return False
    snaps = [p for p in d.iterdir() if p.is_dir()]
    if not snaps:
        return False
    snap = snaps[0]
    if allow:
        return all((snap / name).exists() for name in allow)
    return (snap / "model.safetensors").exists()


def fetch(repo_id, allow, label):
    from huggingface_hub import hf_hub_download
    if allow:
        t = time.perf_counter()
        for name in allow:
            hf_hub_download(repo_id=repo_id, filename=name)
        print(f"    {label}: downloaded in {time.perf_counter() - t:.0f}s")
        return
    # No allowlist: let the model's own loader decide what it needs.
    import laya
    t = time.perf_counter()
    laya.load(repo_id, device="cpu")
    print(f"    {label}: downloaded in {time.perf_counter() - t:.0f}s")


def main():
    print(f"  models go in: {HF_HOME}")
    missing = []
    for label, repo_id, size, allow, page in MODELS:
        print()
        print(f"  {label}: {repo_id}  ({size})")
        print(f"    page: {page}")
        if allow:
            print(f"    allowlist: {', '.join(allow)}")
        try:
            if present(repo_id, allow) and not FORCE:
                print("    ALREADY INSTALLED - not downloading again")
                continue
            if present(repo_id, allow) and FORCE:
                print("    already on disk, but -ForceModels was given, refetching")
            else:
                print("    not found here, downloading...")
            fetch(repo_id, allow, label)
        except LocalEntryNotFoundError:
            print("    not found here, downloading...")
            fetch(repo_id, allow, label)
        except Exception as exc:  # noqa: BLE001
            print(f"    FAILED: {type(exc).__name__}: {exc}")
            missing.append((label, page))

    print()
    if missing:
        print("  Some models could not be fetched. Download them by hand from:")
        for label, page in missing:
            print(f"    {label}: {page}")
        return 1

    print("  All models present.")
    for label, repo_id, size, allow, page in MODELS:
        state = "present" if present(repo_id, allow) else "MISSING"
        print(f"    {state:<8} {label:<6} {repo_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
