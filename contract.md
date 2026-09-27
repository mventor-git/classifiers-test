# Project Contract — laya-beta-chat

| | |
|---|---|
| **Project root** | `C:\Users\Mventor\github\repositories\laya-beta-test` |
| **Version** | **1.1.0** |
| **Status** | **ACTIVE.** Approved by Mventor, 2026-09-27. |
| **Date** | 2026-09-27 |
| **Owner** | Mventor |
| **Machine** | MSI MS-7B86 · Ryzen 5 2600 · 16 GB RAM · GTX 1060 3 GB · Windows 11 |

This document is the project's constitution. It is not a task list, a progress log,
or a research report.

---

## 1. Vision

A local, single-user web app that reads a message, email or ticket and returns
**typed decisions** about it — routed team, refund requested, language, tone — with
probabilities, in under 200 ms, with no cloud calls and no data leaving the machine.

It is a **decision engine with a conversational interface**, not a writer. It answers
questions about text. It does not produce prose.

## 2. Problem

Ticket triage and inbound-message routing are mechanical classification problems
wearing a chat costume. Existing options either send data to a cloud API, or require
a machine with more VRAM than this one has. `laya-multilingual` is a 322M-parameter
non-autoregressive classifier that answers typed questions in a single forward pass
across 100+ languages — and it runs on this PC's GTX 1060 in 85–95 ms.

The product gap is the interface, not the model.

## 3. Goals

1. **Runs on this PC.** GPU-accelerated, no cloud dependency, no API key.
2. **Answers every question in one forward pass.** Never loop one call per question.
3. **Multi-language by default.** Arabic and English are first-class; 100+ languages work.
4. **Self-contained repository.** Dependencies and model data live inside the project
   directory, so the project runs from one folder on one machine.
5. **Explainable output.** Every answer carries its confidence and its full probability
   distribution. No hidden judgement.
6. **Safe by default.** Binds to `127.0.0.1` only. No tunnel, no public link.

## 4. Non-goals

- **Not a text generator.** No prose, no summaries, no replies, no rewriting.
- **Not a general-purpose LLM chat.** It does not hold a conversation for its own sake.
- **Not a fine-tuned production classifier.** Uncalibrated, and known-weak on
  low-resource languages. Accuracy work is out of scope.
- **Not multi-user, not authenticated, not internet-facing.**
- **Not mobile-first.** Desktop browser on localhost.

## 5. Architecture boundaries

**The model is fixed.** `convaiinnovations/laya-multilingual` is the only engine. It is
non-autoregressive and has **no text-generation capability**. Nothing in this project may
assume otherwise. Any design that needs generated prose requires a different engine and
therefore an amendment to this contract.

**Layers, and who owns what:**

| Layer | Owns | Boundary |
|---|---|---|
| Engine | `laya` SDK + `laya-multilingual` weights | Single forward pass → typed answers. Never modified. |
| Agent | Reply composition from engine values, question validation | Calls the engine, renders its returned values. **Stateless** (v1.1.0). Must not fabricate answers. |
| Interface | Gradio page: cards 01, 02 and the example grid | Renders engine and agent output. Holds no domain logic. |
| Data | Model weights, venv, question presets | Lives inside the project directory. |

**The agent layer may only:** derive structured questions from a message, call the
engine, and compose the engine's returned values into a reply. **It may not:** invent
probabilities, override an answer it dislikes, or fabricate an answer when the engine
returns none. That rule is enforced structurally — every number printed in a reply is
read out of the engine's result dict, and `tests/test_agent.py` asserts it.

**No conversation state.** Contract v1.1.0 removed the chat interface at Mventor's
direction, so the agent is a pure function of (message, questions) → reply. There is no
transcript, no history, no multi-turn memory.

**Hardware boundary (measured, not assumed):**

| Constraint | Value | Consequence |
|---|---|---|
| VRAM | 2148 MB of 3072 MB for one checkpoint | One engine resident. Never preload a second. |
| Interactive latency | 80–95 ms | Budget is 200 ms. |
| Max sequence | 1024 tokens interactive, 2048 batch | 8192 exhausts VRAM. |
| `max_len` is per question | 2 questions at 8192 = 16384 tokens | Multi-question calls scale memory. |
| Threads | 6 physical cores | Cap torch to 6, not 12. |

## 6. Data and operational constraints

- **Local only.** Bind `127.0.0.1`. `share=False`. Never `0.0.0.0`. These apps have no
  authentication and would be open to the whole network.
- **No secrets in the repo.** No API keys, no tokens, no `.env` committed.
- **Weights are not committed.** The self-contained requirement is about the *directory*,
  not the git history. Multi-gigabyte binaries are gitignored; reproducibility is a
  lockfile plus a documented fetch step.
- **Offline after first fetch.** Once weights are cached, the app runs with no network.
- **n8n integration is optional**, via HTTP against the local API on `127.0.0.1`, not
  by embedding n8n logic in the app.

## 7. Acceptance gates

The project is done when all of these are observably true:

1. `START` from a cold start, with no console typing, opens a working page in a browser.
2. A pasted Arabic message returns the correct routing decision **and** correct
   probabilities, in under 200 ms, on the GPU.
3. At least three languages in one batch produce individually correct decisions.
4. All questions in a single call are answered in that single call.
5. `127.0.0.1` is confirmed as the only bound address; the app is unreachable from the LAN.
6. No Python, CUDA, or laya version is hard-coded anywhere in the source; all are pinned
   in a lockfile.
7. A clean `git status` on a fresh clone plus one documented setup command reproduces
   the environment.
8. The measured latency, VRAM and RAM figures are recorded in `PROJECT_STATE.md` and
   match a re-run.

## 8. Risks and known unknowns

| Risk | Status |
|---|---|
| Model is over-confident; ECE 0.314 as shipped | **Accepted.** Calibration needs labelled data that does not exist yet. Documented, not fixed. |
| Arabic macro accuracy 0.400 on 20-way intent | **Accepted.** In-scope use is 3–8 buckets. |
| `score` questions have measured position bias | **Banned for non-English.** Use `choice`. |
| `noul` can under-report "true" | Documented. Cross-check with a 2-option `choice`. |
| GPU driver or CUDA update could drop Pascal | cu126 pinned. CUDA 13 removed sm_61. Re-verification needed after any torch bump. |
| venv inside a repo is unconventional | Accepted deliberately: self-containment was the requirement. Mitigated by gitignore. |

## 9. Open decisions

**D1. What does "real chat agent" mean here? — RESOLVED 2026-09-27, narrowed by v1.1.0.**
`laya-multilingual` cannot generate text. Decision: **a rule-based agent, no new
dependencies.** The agent validates the question set, calls the engine, and composes
its reply from the engine's returned values. It is a conversational interface over a
classifier, and the contract says so plainly rather than implying generation. No LLM
runtime is added. A generator, if ever wanted, is a separate engine and therefore an
amendment to §5. **v1.1.0 removed the chat interface entirely** at Mventor's direction
("no full chat"), so the agent holds no conversation state.

**D2. Git identity — RESOLVED 2026-09-27.** Global git config on this machine is empty
and stays that way. A **repository-local** identity was set for `laya-beta-chat` only:
`Mventor <mventor@localhost>`. This repo is local and never pushed, so the address is a
placeholder. Change it with `git config user.email "..."` from inside the repo.

**D3. Port — RESOLVED 2026-09-27.** Chat interface on `127.0.0.1:7860`, HTTP API on
`127.0.0.1:8000`. Neither collides with n8n on `:8888`.

## 10. Amendment history

| Version | Date | Change | Approved by |
|---|---|---|---|
| 0.1.0 | 2026-09-27 | Initial draft. New project. | Mventor |
| 0.1.0 | 2026-09-27 | D1 resolved: rule-based agent, no new dependencies. | Mventor |
| 1.0.0 | 2026-09-27 | D2 resolved: repo-local identity. D3 resolved: ports 7860/8000. Contract activated. | Mventor |
| 1.1.0 | 2026-09-27 | Project renamed `laya-beta-chat` → `laya-beta-test`. Full chat interface removed (§5, D1): the agent is now a stateless reply composer. Interface is cards 01/02 plus a grid of example cards. | Mventor |

