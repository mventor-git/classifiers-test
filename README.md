# laya-beta-test

A local web app that reads a message and tells you things about it — which team
should handle it, is a refund being requested, what does the sender actually want —
with probabilities, in about 90 ms, on your own graphics card. Nothing leaves the
machine.

**It does not write replies.** [`laya-multilingual`](https://huggingface.co/convaiinnovations/laya-multilingual)
is a classifier, not a language model. Every value on screen was returned by the
model. Read [`contract.md`](contract.md) before changing anything.

---

## Screenshots

### Light mode

![The Laya app in light mode: card 01 on the left holds the question and the Decide button, card 02 on the right is where the answer lands, and a grid of example cards sits underneath](docs/screenshots/light.png)

*The default theme: warm cream page, white cards, the signature clay-orange
accents. **Card 01** (left) takes the message and holds the **Decide** button in its
header. **Card 02** (right) is where the model's answers land. Below both, a grid of
**example cards** — each one loads its message into card 01 with a single click.*

### Dark mode

![The same Laya app in dark mode: charcoal surfaces, cream text, the same clay-orange accents on the 01, 02 and 03 badges](docs/screenshots/dark.png)

*Dark mode is a second designed palette, not an inversion. The accent moves to a
lighter clay so it stays visible against charcoal, and labels become cream on
near-black. Toggle it with the button in the top right; the choice is remembered.*

---

## Try it

```powershell
git clone https://github.com/mventor-git/laya-beta-test
cd laya-beta-test
powershell -ExecutionPolicy Bypass -File installer.ps1
powershell -ExecutionPolicy Bypass -File start.ps1
```

`installer.ps1` does everything: it detects whether you have an NVIDIA GPU,
creates a Python 3.12 environment, installs the right PyTorch build, installs the
pinned dependencies, downloads the ~647 MB of model weights, and verifies the
result. Then `start.ps1` serves the app and opens your browser.

No API key. No account. No cloud call. Nothing is uploaded.

<details>
<summary>Already have the environment? What each piece does</summary>

| Step | What happens |
|---|---|
| device detection | NVIDIA present → CUDA build, otherwise CPU |
| PyTorch | from the **cu126** index on a GPU, plain PyPI on CPU |
| dependencies | `requirements.lock.txt`, 61 pinned packages |
| weights | `snapshot_download` of `convaiinnovations/laya-multilingual` into `.data/huggingface` |
| verify | prints torch / laya / gradio versions, CUDA status, free VRAM |

Force a specific device with `installer.ps1 -Device cpu`, or skip the download with
`-SkipWeights` if you want to fetch it yourself.
</details>

### Why the weights are not in this repository

The checkpoint is 647 MB of binaries. Committing it would put 647 MB in git history
forever, where it can never be garbage-collected and every clone pays for it.
`.gitignore` excludes `.data/` and `.venv/`; `installer.ps1` fetches the weights
instead. That is the difference between "self-contained" and "a repository nobody
wants to clone".

---

## The page

**Card 01 — the question.** Paste a message, pick a question set (or write your own
JSON), and press **Decide** at the top.

**Card 02 — the answer.** The model's answers land here, with a confidence for each
and the full probability spread. The line underneath shows the token count and how
long it took.

**Example cards.** Below them, one card per example. Each shows a real message and
the decision it should produce. Press **Use this** to load it into card 01.

Two more tabs: **Batch** (one message per line, ~9 ms each) and **About**.

## Question sets

| Set | Asks |
|---|---|
| `triage` | Which team, and is a refund requested |
| `intent` | What the sender wants, and whether it needs a human |
| `tone` | Polite or not — **weakest set, treat as a hint** |
| `score` | Severity on a scale — **opt-in, has a known bias, see below** |

Write your own in the Questions box. Three types:

- `choice` — pick one option. Keep it under 20 options.
- `noul` — true or false.
- `score` — a 0..top scale. **Avoid on non-English text.**

## Honest limits

- **Over-confident as shipped.** It will say 100% and be wrong. Calibration needs
  labelled data this project does not have yet.
- **Arabic macro accuracy measured at 0.400** on 20-way intent. Good for 3–8
  buckets, not 20 fine labels.
- **`score` questions have a measured position bias** in every language — 0 of 290
  runs picked the first-listed option. The app warns you when you use one on
  non-English text.
- **`noul` can under-report "true".** Cross-check with a 2-option `choice`.
- **Weak on low-resource languages**: Swahili, Tamil, Amharic.
- **Routing is reliable; tone is not.** `department` was correct 10/10 in testing.
  `tone` called a calm refund request "angry" at 61%.

## Safety

Bound to `127.0.0.1`. Reachable from this machine only — not your network, not the
internet. There is no authentication, so **do not** change the host to `0.0.0.0`.

## Appearance

**Dark mode** — press the button in the header, or let it follow your OS. Your
choice is remembered.

Every text colour in both modes is checked against WCAG AA by
`tools/contrast.py` — currently **20/20 pass**, worst case 4.53:1 against a 4.5:1
bar. That audit has already caught two real regressions: a faint grey at 3.35:1 on
placeholders, and a hover border at 1.51:1.

## Layout

```
installer.ps1             one-command setup for a new machine
start.ps1 / stop.ps1      run and stop
setup.cmd                 the same install, for people who double-click
contract.md               the constitution: vision, boundaries, acceptance gates
PROJECT_STATE.md          measured figures, gate results, what is not verified
requirements.lock.txt     61 pinned packages
src/laya_chat/
  engine.py               owns the model. one forward pass.
  agent.py                composes a reply from engine values. never invents one.
  presets.py              question sets and worked examples
  config.py               paths, device, ports, limits. no version numbers.
  app.py                  the Gradio page and the theme. formats only.
tests/test_agent.py       26 tests, including "never invents a value"
tools/acceptance.py       runs the 9 contract gates
tools/contrast.py         WCAG audit of both palettes
tools/snapshot.py         headless screenshots of both themes
docs/screenshots/         the images used in this README
.venv/  .data/            created by the installer, gitignored
```

## Verify it

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe tools\contrast.py
.\.venv\Scripts\python.exe tools\acceptance.py
```

## Hardware note

Built and measured on an **RTX-free GTX 1060 (sm_61, Pascal)** with 16 GB of RAM.
`installer.ps1` installs PyTorch from the `cu126` index on purpose: CUDA 13.0
removed Pascal, and `cu128`/`cu129` no longer ship a current torch that runs on that
card. A plain `pip install torch` on Windows silently gives you a **CPU-only** build
and you lose the GPU. Roughly 90 ms per decision with the GPU, 1–3 s without.

## Licence and model terms

This project is Apache-2.0. The model,
[`convaiinnovations/laya-multilingual`](https://huggingface.co/convaiinnovations/laya-multilingual),
is Apache-2.0 and carries a commercial-use tag. It is downloaded at install time and
is not redistributed here.
