# PROJECT_STATE

**Project:** classifiers-test · **Contract:** v2.0.0 ACTIVE
**Last measured:** 2026-09-27 · **Status:** 12/12 acceptance gates pass, 64 tests

---

## Environment (pinned in `requirements.lock.txt`, 65 packages)

| | |
|---|---|
| Python | 3.12.14, inside `.venv` |
| torch | **2.14.0+cu126** |
| torchvision | 0.29.0+cu126 — required, `AutoImageProcessor` will not load without it |
| laya | 0.3.20 |
| transformers | 5.17.0 |
| gradio | 6.28.0 |
| Weights | `laya-multilingual` 647 MB, `ai-vs-human-image-detector` 363 MB, in `.data/huggingface` |

**Why cu126:** CUDA 13.0 removed Pascal. `cu128` stops at torch 2.11.0 and `cu129`
at 2.9.0, so cu126 is the only index with a current torch that runs on this card.
A plain `pip install torch` on Windows is CPU-only. Re-verify
`torch.cuda.get_arch_list()` after any upgrade — it currently reports `sm_61`.

## Latency and memory, measured

| | |
|---|---|
| Text decision, warm, 2 questions | 85 ms |
| Text, 3 languages batched | 88 ms (29 ms each) |
| Image, warm classify | 71 ms |
| Image, 4 fixtures batched | 186 ms including model load |
| URL fetch + classify | 376–1375 ms, network dominated |
| Model load, cold | 21 s text · 13 s image · 3.5 s image reload after release |



Two local classifiers behind one page. You pick which one before anything loads.

| | Text | Image |
|---|---|---|
| Model | `convaiinnovations/laya-multilingual` | `Ateeqq/ai-vs-human-image-detector` |
| Architecture | mmBERT-base, 322M | SigLIP base, 88M |
| Input | text, 1024 tokens | any image, 224×224 |
| Output | typed decisions + probabilities | `ai` / `hum` + probabilities |
| Latency | 85 ms | 71 ms |
| VRAM | 1884 MB | 402 MB |

Neither writes prose. Both are classifiers.

## Why you are asked which one

Measured on a 3 GB GTX 1060:

| State | VRAM of 3072 MB |
|---|---|
| CUDA context at rest | 612 MB |
| + laya | 1884 MB |
| + SigLIP | 2781 MB |
| + a 4096-token text call with both resident | **2988 MB — 84 MB free** |

84 MB of headroom is one allocation from a crash. So the choice is made at startup,
and the app has a `gpu.py` guard that unloads the image model when a text call needs
the room (it reloads in ~3.5 s against laya's ~21 s, so laya is the one that stays).

## The image model's accuracy is not established — measured, not assumed

The upstream card reports **99.2% test accuracy** and then, in the same paragraph,
says *"Some users reported overfitting issues"*. Running it here:

| Input | Verdict | Confidence |
|---|---|---|
| Unsplash: cat | `hum` (real) | **100.0%** |
| Unsplash: forest | `hum` (real) | **100.0%** |
| Unsplash: Yosemite lake | **`ai`** | **99.9%** |
| Unsplash: mountain | `hum` (real) | **100.0%** |
| generated: flat blue rectangle | **`ai`** | **99.8%** |
| generated: warm gradient | **`ai`** | **99.7%** |
| generated: concentric rings | `hum` | 99.7% |
| generated: noise field | `hum` | 100.0% |

Two things stand out. A real landscape photograph is called AI-generated at 99.9%.
And a **flat blue rectangle** — the least photographic image that could exist — is
called AI at 99.8%, while a warm gradient is also called AI at 99.7% but a noise
field is called human at 100%. The labels are being driven by something other than
what the picture is.

**No accuracy claim is made anywhere in this project, and the caveat is shown in
the UI on every result.** This model is a demo. Treat its output as a hint.

## The text model's measured behaviour

| | |
|---|---|
| `department` routing, 3-8 buckets | **10/10 correct** across Arabic, English, German, French |
| `noul` refund detection | correct on every case tried |
| Arabic macro accuracy, 20-way intent (upstream) | 0.400 — fine for 3-8 buckets, not 20 |
| `tone` | **unreliable**: a calm refund request was called "angry" at 61% |
| Calibration | uncalibrated, ECE 0.314 as shipped |

## Test images, and why none are bundled

The repository contains **no third-party photograph**. Two reasons:

1. Unsplash blocks automated access to its HTML pages — a plain fetch of a photo
   page returns **HTTP 401**. Their sanctioned route is an API access key, which
   this project does not have or want to require.
2. Committing third-party images into a public repository raises attribution and
   licensing questions.

Instead, in order of preference:

- **Paste an image URL** in the app. The repository stores the *URL*, never the
  photograph, and the bytes are fetched on your machine only when you press the
  button. Four working Unsplash CDN URLs ship in `image/presets.py`.
- **Drop any image file** you have — PNG, JPEG, WebP, BMP, GIF, TIFF, one or many.
- **Generated fixtures** in `samples/`, drawn by `tools/make_samples.py`. No
  licensing question at all. They exercise the pipeline and say nothing about
  accuracy.

## Fetching a URL is a security boundary

Letting the app fetch a user-supplied URL is the classic SSRF shape — a local app
is still a network client. `classifiers/image/remote.py` therefore enforces:

- `https` only — no `http`, `file`, `ftp`, `gopher`, `data`, `javascript`
- no credentials embedded in the URL
- the hostname is resolved and **every** address it resolves to is checked;
  any private, loopback, link-local, reserved or multicast address is refused
- a 4-host allowlist, so `notimages.unsplash.com.evil.test` cannot spoof a suffix
- redirects are surfaced, not followed blindly, and each hop is re-validated
  (limit 3)
- a 20 MB body cap, 20 s timeouts, no cookies or auth headers sent

`tests/test_remote.py` covers 17 refused URLs including `169.254.169.254`,
`127.0.0.1`, `localhost`, `file://` and the suffix-spoofing attempt. A guard
without tests is not a guard.

## No pickle was ever downloaded

The image model's repository contains `training_args.bin`, which the Hub flags as
unsafe: unpickling executes arbitrary code, and inference does not need it. It is
fetched with a three-file **allowlist** — `config.json`, `preprocessor_config.json`,
`model.safetensors` — rather than a blocklist, so a `.bin` added upstream later
cannot slip in. Verified on disk: 363 MB, three files, zero pickles. Gate 12.

## Acceptance gates — 12/12

| Gate | Result |
|---|---|
| 1. `installer.ps1` completes from nothing | PASS |
| 2. Arabic → correct routing under 200 ms | PASS — 85 ms |
| 3. Three languages batched, all correct | PASS — 88 ms |
| 4. All questions in one forward pass | PASS |
| 5. Bound to `127.0.0.1` only | PASS |
| 6. No version string in `src/` | PASS |
| 7. Lockfile + one documented setup command | PASS — 65 packages |
| 8. Measured figures recorded | PASS |
| 9. WCAG AA in light and dark | PASS — 20/20 |
| 10. Each mode shows only its own tabs | PASS |
| 11. Real image labels; non-image gets an error, not a verdict | PASS |
| 12. No pickle in the model cache | PASS |

64 tests pass.

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe tools\contrast.py
.\.venv\Scripts\python.exe tools\acceptance.py
```

## Not verified

- **Gate 1 is not proven.** This repo's `.venv` and `.data` were copied from the
  previous project, not built here. Nobody has run `installer.ps1` on a machine
  with neither. The smart "already installed" path is likewise unproven.
- **The image tab has never been photographed.** Brave's headless mode began
  hanging on this machine and the screenshot tool could not recover it, so
  `docs/screenshots/` holds the *text* tab only. The image tab has been verified
  by driving its functions directly, not by looking at it.
- **No accuracy evaluation exists** for either model, on any dataset.
- **Grading is not implemented.** Nothing compares model output to a known answer.
- **A URL is fetched over the network on request.** That is a deliberate exception
  to "nothing leaves this machine" — it is a request *out*, initiated by you, with
  no data sent. Worth stating plainly.
- Dark mode is not supported by dark **mode** detection beyond the explicit
  toggle; there is no `prefers-color-scheme` in the packaged app's own test.

## Clean-machine install, verified 2026-09-27

Cloned to a bare folder with no `.venv` and no `.data`, then ran
`installer.ps1` exactly as a new user would.

| | |
|---|---|
| Fresh clone | `e51a4f4`, 15 files, no `.venv`, no `.data` |
| **First run** | **8.7 min** — venv, torch 2.14.0+cu126, torchvision, 65 pinned packages, both models downloaded (text 305 s, image 107 s), environment verified |
| **Second run** | **35.2 s** — `torch already installed`, 65 packages already satisfied, both models reported `ALREADY INSTALLED - not downloading again` |
| Tests from that clone | **64 passed** |
| Gates from that clone | **12/12** |
| A real Unsplash photo fetched and classified from that clone | `hum` at 100.0% |
| URL guard from that clone | still refuses `http://`, `127.0.0.1` and `169.254.169.254` |

### The bug this found

The first attempt **died after 6 seconds**. `installer.ps1` set
`$ErrorActionPreference = 'Stop'`, then probed for torch by running
`python -c "import torch"`. Torch was not installed yet, so python wrote a
traceback to stderr, PowerShell raised `NativeCommandError`, and *checking for
a missing module killed the install*. It would have hit every new user on the
very first step.

Fixed two ways: the probe now uses `importlib.util.find_spec` and reads an exit
code instead of parsing output, and `$ErrorActionPreference` is `Continue`,
because every failure path in the script already checks `$LASTEXITCODE`
explicitly — `Stop` only ever got in the way of a diagnostic line.

**Acceptance gate 1 is now genuinely satisfied. It was not before this run.**