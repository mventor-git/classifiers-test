# Project Contract — classifiers-test

| | |
|---|---|
| **Project root** | `C:\Users\Mventor\github\repositories\local-classifiers-test` |
| **Remote** | `https://github.com/mventor-git/classifiers-test` |
| **Version** | **2.0.0** |
| **Status** | **ACTIVE.** Approved by Mventor, 2026-09-27. |
| **Date** | 2026-09-27 |
| **Owner** | Mventor |
| **Machine** | MSI MS-7B86 · Ryzen 5 2600 · 16 GB RAM · GTX 1060 3 GB · Windows 11 |

This document is the project's constitution. It is not a task list, a progress log,
or a research report.

---

## 1. Vision

A local page that puts **two small classifiers** behind one interface and asks you
which one you want before it loads anything:

1. **Text** — `laya-multilingual`. Read a message, get typed decisions about it.
2. **Image** — `Ateeqq/ai-vs-human-image-detector`. Drop in a picture, get `ai` or
   `hum` with probabilities.

Both run on this machine's GPU, neither sends anything anywhere, and neither
writes prose. A classifier answers a question; it does not compose.

## 2. Problem

Two useful models, two different shapes — text in, decisions out; image in, one
label out — and one hard constraint: a 3 GB graphics card. Measured, the text
model is 1884 MB and the image model pushes the total to 2781 MB; a 4096-token
text call with both resident peaks at **2988 of 3072 MB**, one allocation from an
out-of-memory crash.

So the choice of which model to run is made **before** anything loads, not
negotiated at runtime. The interface is the product; the models are interchangeable
parts behind it.

## 3. Goals

1. **Runs on this PC.** GPU-accelerated, no cloud, no API key.
2. **One model at a time by default.** Asking at startup removes the memory
   question instead of managing it.
3. **Multi-language text.** Arabic and English first-class; 100+ languages work.
4. **Any image format.** Drop in PNG, JPEG, WebP, BMP, GIF or TIFF, one or many.
5. **Self-contained.** Dependencies and both models live inside the project
   directory; `installer.ps1` recreates them from scratch.
6. **Explainable output.** Every answer carries its confidence and its full
   probability distribution.
7. **Safe by default.** Binds to `127.0.0.1`. No pickle is ever downloaded.

## 4. Non-goals

- **Not a text generator.** No prose, no summaries, no replies.
- **Not an image generator.** It classifies images; it does not make them.
- **Not a validated detector.** Neither model has been evaluated on this
  project's data. See §8.
- **Not multi-user, not authenticated, not internet-facing.**
- **Not a model zoo.** Two classifiers. Adding a third is an amendment.

## 5. Architecture boundaries

**Each classifier is a peer with its own folder.** Neither is embedded in the
other, and neither shares a module with the other's logic.

```
src/classifiers/
  config.py        paths, both model ids, the mode switch, safety allowlist
  gpu.py           the shared VRAM budget guard
  theme.py         palette, CSS, JS          (shared presentation only)
  app.py           the page. formats, decides nothing
  text/
    engine.py      owns laya. one forward pass.
    agent.py       composes a reply from engine values. never invents one.
    presets.py     question sets and worked examples
  image/
    engine.py      owns SigLIP. one forward pass per image.
    agent.py       composes the verdict from engine values. never invents one.
    presets.py     accepted formats, label wording, the caveats
```

**The agent rule, for both, unchanged since 1.0.0:** an agent layer may derive
questions from an input, call its engine, and compose the engine's returned values
into a reply. It may **not** invent a probability, override a verdict it dislikes,
or produce an answer for an input the engine could not read. This is enforced
structurally — every number in a reply is read out of the engine's result dict —
and asserted in `tests/test_agent.py`.

**Neither engine is modified.** They are upstream models behind a boundary.

**The mode switch (`CLASSIFIERS`)** decides which tabs exist:

| Mode | Decide | Batch | Image | Models loaded |
|---|---|---|---|---|
| `text` | yes | yes | no | laya only |
| `image` | no | no | yes | SigLIP only |
| `both` | yes | yes | yes | both, with the VRAM guard active |

`start.ps1` asks the question. A hidden tab cannot be reached, so its model is
never loaded.

**The VRAM guard** (`gpu.py`) is the safety net for `both`. Before a text call
needing 700 MB free (900 MB for a batch), the image model is unloaded — it
reloads in ~3.5 s against the text model's ~21 s, so the text model is the one
that stays. The text model yielding would be the wrong trade.

## 6. Data, safety and operational constraints

- **Local only.** Bind `127.0.0.1`. `share=False`. Never `0.0.0.0`. No auth, so
  it must never be exposed.
- **No pickle, ever.** The image model's repository contains `training_args.bin`,
  which the Hub flags as unsafe: unpickling executes arbitrary code, and inference
  does not need it. It is fetched with a three-file **allowlist**
  (`config.json`, `preprocessor_config.json`, `model.safetensors`) rather than a
  blocklist, so a `.bin` added upstream later cannot slip in. Asserted by
  `test_image_weights_use_an_allowlist_not_a_blocklist`.
- **No secrets in the repository.**
- **Weights are not committed.** The 647 MB and 363 MB checkpoints are
  gitignored; `installer.ps1` and `tools/fetch_models.py` fetch them, and report
  a model that is already present instead of re-downloading it.
- **Offline after first fetch.**
- **No bundled third-party photographs.** See §8, D1.

## 7. Acceptance gates

1. `installer.ps1` completes on a machine with no `.venv` and no `.data`, and
   reports both models present on a second run.
2. The text classifier answers an Arabic message correctly, under 200 ms.
3. Three languages batched in one call, all correct.
4. All questions answered in one forward pass.
5. Bound to `127.0.0.1` only.
6. No Python / CUDA / package version hard-coded in `src/`.
7. Lockfile plus one documented setup command.
8. Measured latency, VRAM and RAM recorded in `PROJECT_STATE.md`.
9. Every text colour meets **WCAG 2.1 AA** in **both** themes, proven by
   `tools/contrast.py`.
10. **Each mode shows only its own tabs**, proven by test.
11. **The image classifier returns a label for a real image**, and reports a
    readable error — not a verdict — for a file that is not an image.
12. **No `.bin` reaches `.data/`**, verified on disk after a real fetch.

## 8. Risks and known unknowns

| Risk | Status |
|---|---|
| **The image model is reported overfit by its own author.** The card claims 99.2% test accuracy and then says "Some users reported overfitting issues". It returned 99.5% on a synthetic gradient, which is not evidence of anything. | **Unresolved. The caveat is shown in the UI.** No accuracy claim is made anywhere. |
| Both models resident peak at 2988 of 3072 MB | **Mitigated** by the mode switch; guarded in `both`. |
| CUDA 13 removed Pascal, so a torch upgrade can drop `sm_61` | cu126 pinned. Re-verify `get_arch_list()` after any bump. |
| laya is over-confident, ECE 0.314 as shipped | **Accepted.** Calibration needs labelled data that does not exist. |
| laya Arabic macro accuracy 0.400 on 20-way intent | **Accepted.** Good for 3–8 buckets. |
| `score` questions have measured position bias | **Banned for non-English.** Use `choice`. |
| **D1 — no third-party test images are bundled.** | **OPEN, needs Mventor.** See below. |
| No `classification` on the text path has been evaluated on real data | The worked examples are a smoke test, not an evaluation. |

### D1 — test images, and why nothing is bundled

The request was to use Unsplash photographs as test data. Not done, deliberately:

- The Unsplash API needs an access key, and its terms govern bulk downloading.
- Committing third-party photographs into a **public** repository raises
  attribution and licensing questions that a code licence does not answer.

What exists instead: the attach button accepts any image the user has, the
classifier is proven end to end on generated images, and the app needs no bundled
data to be useful. Mventor chooses the source for a bundled sample set.

## 9. Open decisions

**D1 — where do bundled test images come from?** Options: a permissively licensed
dataset fetched on demand; the model authors' own example images; or nothing
bundled and the user supplies their own. **Mventor's call. Not blocking.**

## 10. Amendment history

| Version | Date | Change | Approved by |
|---|---|---|---|
| 0.1.0 | 2026-09-27 | Initial draft, as `laya-beta-chat`. | Mventor |
| 0.1.0 | 2026-09-27 | D1: rule-based agent, no LLM runtime. | Mventor |
| 1.0.0 | 2026-09-27 | D2 repo-local identity, D3 ports. Activated. | Mventor |
| 1.1.0 | 2026-09-27 | Renamed `laya-beta-chat` → `laya-beta-test`. Chat removed; stateless agent. | Mventor |
| 1.2.0 | 2026-09-27 | Dark mode as a second palette; gate 9, WCAG AA. | Mventor |
| **2.0.0** | 2026-09-27 | **Second classifier added: SigLIP AI-vs-human image detector, with an attach button accepting all common image formats. Startup now asks which classifier to load. Package restructured to two peer classifiers, `classifiers/text/` and `classifiers/image/`. Image weights fetched with a three-file allowlist so the unsafe pickle is never downloaded. Gates 10–12 added. Repo renamed to `mventor-git/classifiers-test`.** | Mventor |
