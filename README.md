# laya-beta-test

A local web app that reads a message and tells you things about it — which team
should handle it, is a refund being requested, what does the sender actually want —
with probabilities, in about 90 ms, on your own graphics card. Nothing leaves the
machine.

**It does not write replies.** `laya-multilingual` is a classifier, not a language
model. Every value on screen was returned by the model. Read
[`contract.md`](contract.md) before changing anything.

---

## Start it

```powershell
powershell -ExecutionPolicy Bypass -File start.ps1
```

Or double-click `start.ps1` and choose "Run with PowerShell" if prompted.

The browser opens by itself once the server is up. The first start takes about 20
seconds while the model loads onto the GPU; after that it is instant. Stop it with
`stop.ps1`, or close the window.

First-time setup on a fresh clone:

```powershell
.\setup.cmd
```

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

## Layout

```
start.ps1 / stop.ps1      run and stop
setup.cmd                 one-time environment install
contract.md               the constitution: vision, boundaries, acceptance gates
PROJECT_STATE.md          measured figures, gate results, what is not verified
requirements.lock.txt     61 pinned packages
src/laya_chat/
  engine.py               owns the model. one forward pass.
  agent.py                composes a reply from engine values. never invents one.
  presets.py              question sets and worked examples
  config.py               paths, device, ports, limits. no version numbers.
  app.py                  the Gradio page. formats only, decides nothing.
tests/test_agent.py       26 tests, including "never invents a value"
tools/acceptance.py       runs the 8 contract gates
.venv/  .data/            inside the repo, gitignored
```

## Verify it

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe tools\acceptance.py
```

## Hardware note

This was built for a **GTX 1060 (sm_61, Pascal)**. `setup.cmd` installs torch from
the `cu126` index on purpose: CUDA 13.0 removed Pascal, and `cu128`/`cu129` no longer
ship a current torch that runs on this card. A plain `pip install torch` gives a
**CPU-only** build on Windows and you will lose the GPU. See the header of
`requirements.lock.txt`.
