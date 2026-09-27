"""Interface layer.

Contract section 5: renders engine and agent output, holds no domain logic. Every
value shown here came from the engine via agent.py; this file formats and displays.

Page shape:
  01  The question  - the Decide button sits on top
  02  The answer    - filled in when the button is pressed
  03  Examples      - a card per example; each one loads into card 01

Binds to 127.0.0.1 only (contract section 6). No tunnel, no auth - which is exactly
why it must never be exposed.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from laya_chat import config  # noqa: E402
from laya_chat import agent, engine, presets  # noqa: E402

import gradio as gr  # noqa: E402

CARD_CSS = """
/* ==========================================================================
   PALETTE
   Light and dark are two designed palettes, not one inverted.
   Every text/background pair below is asserted in tools/contrast.py against
   WCAG AA (4.5:1 body, 3:1 large). Light --ink-faint was #9a8a76 at 3.35:1
   and FAILED; it is #7d6e5c at 4.93:1 now.
   ========================================================================== */
:root {
    --page-a:      #fbf8f3;
    --page-b:      #f3ebe0;
    --surface:     #ffffff;
    --surface-2:   #fdfaf6;
    --line:        #e8dfd1;
    --line-hi:     #dccfb9;
    --ink:         #2b2119;   /* 15.7:1 on surface */
    --ink-soft:    #6b5b49;   /*  6.5:1 */
    --ink-faint:   #7d6e5c;   /*  4.9:1  (was 3.35:1 - failed AA) */
    --copper:      #a85a1c;   /*  5.1:1 with white text */
    --copper-dk:   #8a4410;
    --teal:        #0f6f66;   /*  6.0:1 */
    --good:        #2f7d4f;   /*  5.0:1 */
    --bad:         #b3402e;   /*  5.7:1 */
    --shadow:      0 1px 2px rgba(43,33,25,.05), 0 6px 18px rgba(43,33,25,.06);
    --shadow-hi:   0 2px 4px rgba(43,33,25,.07), 0 14px 34px rgba(43,33,25,.11);
    --ring:        rgba(168,90,28,.45);
    --radius:      16px;
}

/* Dark rules come after :root so they win on equal specificity.
   html[data-theme="dark"] is an explicit user choice and beats the media query. */
html[data-theme="dark"] {
    --page-a:      #14110e;
    --page-b:      #0d0b0a;
    --surface:     #211c18;
    --surface-2:   #2a2420;
    --line:        #3a322b;
    --line-hi:     #4d4239;
    --ink:         #f4eee6;   /* 14.6:1 on surface */
    --ink-soft:    #c9bcae;   /*  9.1:1 */
    --ink-faint:   #a89a8c;   /*  6.2:1 */
    --copper:      #e8964f;   /*  7.1:1 */
    --copper-dk:   #d07f3a;
    --teal:        #5ecfbe;   /*  9.0:1 */
    --good:        #6fcf97;
    --bad:         #f08a7d;
    --shadow:      0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.45);
    --shadow-hi:   0 2px 4px rgba(0,0,0,.5), 0 14px 34px rgba(0,0,0,.55);
    --ring:        rgba(232,150,79,.55);
    color-scheme: dark;
}
@media (prefers-color-scheme: dark) {
    html:not([data-theme="light"]) {
        --page-a:      #14110e;
        --page-b:      #0d0b0a;
        --surface:     #211c18;
        --surface-2:   #2a2420;
        --line:        #3a322b;
        --line-hi:     #4d4239;
        --ink:         #f4eee6;
        --ink-soft:    #c9bcae;
        --ink-faint:   #a89a8c;
        --copper:      #e8964f;
        --copper-dk:   #d07f3a;
        --teal:        #5ecfbe;
        --good:        #6fcf97;
        --bad:         #f08a7d;
        --shadow:      0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.45);
        --shadow-hi:   0 2px 4px rgba(0,0,0,.5), 0 14px 34px rgba(0,0,0,.55);
        --ring:        rgba(232,150,79,.55);
        color-scheme: dark;
    }
}

/* ---- page ---- */
body {
    background:
        radial-gradient(1100px 520px at 12% -8%, rgba(255,246,233,.9) 0%, transparent 60%),
        radial-gradient(900px 460px at 88% 4%, rgba(238,246,244,.9) 0%, transparent 55%),
        linear-gradient(180deg, var(--page-a) 0%, var(--page-b) 100%) !important;
    background-attachment: fixed !important;
    color: var(--ink) !important;
    font-family: "Segoe UI", system-ui, -apple-system, "Noto Sans Arabic",
                 "Noto Sans", "Helvetica Neue", sans-serif !important;
}
html[data-theme="dark"] body,
html:not([data-theme="light"]) body { transition: background-color .3s ease; }
@media (prefers-color-scheme: dark) {
    html:not([data-theme="light"]) body {
        background:
            radial-gradient(1100px 520px at 12% -8%, rgba(60,44,28,.55) 0%, transparent 60%),
            radial-gradient(900px 460px at 88% 4%, rgba(24,54,52,.5) 0%, transparent 55%),
            linear-gradient(180deg, var(--page-a) 0%, var(--page-b) 100%) !important;
    }
}
h1 { font-weight: 800 !important; letter-spacing: -0.02em !important;
     color: var(--ink) !important; }
h1 + p, .prose p { color: var(--ink-soft) !important; }
code, pre { border-radius: 8px !important; }
footer, .gradio-container footer { display: none !important; }

/* ---- cards ---- */
.card {
    border: 1px solid var(--line) !important;
    border-radius: var(--radius) !important;
    padding: 20px 22px !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow) !important;
    color: var(--ink) !important;
    height: 100%;
    transition: box-shadow .28s ease, transform .28s ease, border-color .28s ease,
                background-color .3s ease;
    animation: cardIn .55s cubic-bezier(.2,.7,.3,1) both;
}
.card:hover { box-shadow: var(--shadow-hi) !important; transform: translateY(-2px);
              border-color: var(--line-hi) !important; }
@keyframes cardIn {
    from { opacity: 0; transform: translateY(14px) scale(.995); }
    to   { opacity: 1; transform: none; }
}
.card-top {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 15px; padding-bottom: 13px;
    border-bottom: 1px solid var(--line);
}
.card-num {
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 32px; height: 32px; padding: 0 9px;
    border-radius: 9px; color: #fff;
    font-weight: 800; font-size: .78rem; letter-spacing: .08em;
    background: linear-gradient(140deg, var(--copper) 0%, var(--copper-dk) 100%);
    box-shadow: 0 2px 7px rgba(0,0,0,.22);
}
.card-title { font-weight: 750; font-size: 1.06rem; color: var(--ink); flex: 1;
              letter-spacing: -0.01em; }

/* ---- example cards ---- */
.card-label { font-weight: 700; font-size: .88rem; margin-bottom: 7px; color: var(--ink); }
.card-msg {
    font-size: .85rem; line-height: 1.55; padding: 11px 13px; margin-bottom: 11px;
    border-radius: 10px; background: var(--surface-2); color: var(--ink-soft);
    min-height: 78px; max-height: 132px; overflow-y: auto;
    border-right: 3px solid var(--copper);
    transition: background .25s ease, border-color .25s ease;
}
.card:hover .card-msg { border-right-color: var(--teal); }
.card-expect { font-size: .78rem; color: var(--teal); margin-bottom: 11px;
               font-weight: 650; }

/* ---- answer panel: fades in on every new result ---- */
.anim-replay { animation: answerIn .42s cubic-bezier(.2,.7,.3,1) both; }
@keyframes answerIn {
    from { opacity: 0; transform: translateY(7px); }
    to   { opacity: 1; transform: none; }
}
.placeholder { color: var(--ink-faint) !important; font-style: italic; padding: 30px 0;
               text-align: center; }

/* ---- buttons ---- */
button {
    border-radius: 11px !important;
    font-weight: 650 !important;
    letter-spacing: .005em !important;
    color: var(--ink) !important;
    transition: transform .16s ease, box-shadow .2s ease, filter .2s ease,
                background-color .3s ease !important;
}
button:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.04); }
button:active:not(:disabled) { transform: translateY(0) scale(.985); }
button:focus-visible, textarea:focus-visible, input:focus-visible, select:focus-visible {
    outline: 3px solid var(--ring) !important;
    outline-offset: 2px !important;
}
button.primary {
    background: linear-gradient(135deg, var(--copper) 0%, var(--copper-dk) 100%) !important;
    border: none !important; color: #fff !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.24) !important;
}
button.primary:hover:not(:disabled) { box-shadow: 0 6px 20px rgba(0,0,0,.32) !important; }
button.primary::after {
    content: ""; position: absolute; inset: 0; border-radius: 11px;
    background: linear-gradient(115deg, transparent 30%, rgba(255,255,255,.34) 50%,
                                transparent 70%);
    background-size: 220% 100%;
    animation: sheen 3.6s ease-in-out infinite;
    pointer-events: none;
}
@keyframes sheen {
    0%, 62% { background-position: 190% 0; }
    100%    { background-position: -60% 0; }
}

/* ---- inputs ---- */
textarea, input, select {
    border-color: var(--line) !important;
    border-radius: 11px !important;
    background: var(--surface-2) !important;
    color: var(--ink) !important;
    caret-color: var(--copper) !important;
    transition: border-color .2s ease, box-shadow .2s ease, background-color .3s ease !important;
}
textarea:focus, input:focus, select:focus {
    border-color: var(--copper) !important;
    box-shadow: 0 0 0 3px var(--ring) !important;
}
textarea::placeholder, input::placeholder { color: var(--ink-faint) !important;
                                            opacity: 1 !important; }
.block, .form, .panel, .gr-box { background: transparent !important; }
.tabs > .tab-nav { border-bottom: 1px solid var(--line) !important; }
.tabs > .tab-nav button { font-weight: 650 !important; color: var(--ink-soft) !important; }
.tabs > .tab-nav button.selected { color: var(--copper) !important;
                                   border-bottom: 2px solid var(--copper) !important; }

/* ---- answer typography ---- */
.anim-replay strong, .anim-replay b { color: var(--ink) !important; }
.anim-replay small { color: var(--ink-faint) !important; }
.anim-replay a { color: var(--teal) !important; }

/* ---- theme toggle ---- */
#theme-toggle { min-width: 108px; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .001ms !important; animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
    }
}
"""

# Applies the chosen theme before first paint, so there is no white flash.
THEME_BOOT_JS = """
() => {
  const KEY = 'laya-theme';
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved === 'dark' || saved === 'light') {
    root.setAttribute('data-theme', saved);
  }
  const paint = () => {
    const dark = root.getAttribute('data-theme') === 'dark' ||
      (!root.getAttribute('data-theme') &&
       window.matchMedia('(prefers-color-scheme: dark)').matches);
    const b = document.getElementById('theme-toggle');
    if (b) b.textContent = dark ? 'Light mode' : 'Dark mode';
  };
  window.__layaToggleTheme = () => {
    const now = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', now);
    try { localStorage.setItem(KEY, now); } catch (e) {}
    // Gradio 6 reads ?__theme= for its own components. Keep the URL in step.
    const u = new URL(window.location.href);
    u.searchParams.set('__theme', now);
    window.history.replaceState(null, '', u);
    paint();
  };
  window.addEventListener('load', paint);
  setTimeout(paint, 60);
}
"""

PRESET_CHOICES = list(presets.PRESETS)

# Restarts the answer fade on every update. Runs in the browser, once, on load.
REPLAY_JS = """
() => {
  const target = () => document.getElementById('answer');
  let frame = 0;
  const replay = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      const el = target();
      if (!el) return;
      el.style.animation = 'none';
      void el.offsetWidth;            // force reflow so the animation restarts
      el.style.animation = '';
    });
  };
  const attach = () => {
    const el = target();
    if (!el || el.dataset.watched) return;
    el.dataset.watched = '1';
    new MutationObserver(replay).observe(el, {childList: true, subtree: true});
  };
  attach();
  new MutationObserver(attach).observe(document.body, {childList: true, subtree: true});
}
"""


def _expect_text(example):
    parts = []
    for key, want in example["answer"].items():
        mark = "yes" if want is True else "no" if want is False else str(want)
        parts.append(f"`{key}` → **{mark}**")
    return " · ".join(parts)


# ------------------------------------------------------------------ actions
def decide(message, preset_name, questions_json):
    """Card 01 -> Card 02. One forward pass, all questions, timing shown."""
    text = (message or "").strip()
    if not text:
        return ('<div class="placeholder">Card 01 is empty. Paste a message, or pick '
                'one of the example cards below, then press <b>Decide</b>.</div>', "")

    questions, err = agent.questions_from(preset_name, questions_json or "")
    if err or not questions:
        return f"**Cannot run.**\n\n{err or 'No questions were resolved.'}", ""

    t0 = time.perf_counter()
    try:
        reply, _result = agent.compose(text, questions)
    except Exception as exc:  # noqa: BLE001
        return f"**The engine failed.**\n\n`{type(exc).__name__}: {exc}`", ""
    dt = (time.perf_counter() - t0) * 1000

    n = len(questions)
    slow = " · ⚠️ **over the 200 ms gate**" if dt > 200 else ""
    meta = f"{n} question{'s' if n != 1 else ''} · {len(text)} characters · " \
           f"**{dt:.0f} ms**{slow}"
    return reply, meta


def use_example(label):
    for e in presets.EXAMPLES:
        if e["label"] == label:
            return e["text"], e["preset"]
    return "", presets.DEFAULT_PRESET


def batch_decide(lines, preset_name, questions_json):
    """The throughput path: one question set over many messages."""
    texts = [ln.strip() for ln in (lines or "").splitlines() if ln.strip()]
    if not texts:
        return [], "Paste one message per line."
    questions, err = agent.questions_from(preset_name, questions_json or "")
    if err or not questions:
        return [], f"❌ {err or 'No questions were resolved.'}"
    t0 = time.perf_counter()
    results = engine.decide_batch(texts, questions)
    dt = time.perf_counter() - t0
    items = results
    if isinstance(results, dict):
        items = results.get("results")
    items = items or []
    rows = []
    for text, item in zip(texts, items):
        ans = (item.get("answers") if isinstance(item, dict) else None) or {}
        row = [text.replace("\n", " ")[:70]]
        for key in questions:
            a = ans.get(key) or {}
            if a.get("type") == "choice":
                row.append(f"{a.get('choice')} ({a.get('answer_confidence', 0):.0%})")
            elif a.get("type") == "noul":
                p = a.get("noul") or 0
                row.append(f"{'yes' if p >= 0.5 else 'no'} ({p:.0%})")
            else:
                row.append(str(a.get("score")))
        rows.append(row)
    return rows, f"{len(texts)} messages in **{dt:.2f} s** " \
                 f"({dt / len(texts) * 1000:.0f} ms each)"


def run_all_examples():
    """Score the shipped examples against the engine on this machine."""
    rows, hits, total = [], 0, 0
    for e in presets.EXAMPLES:
        answers = engine.decide(e["text"], presets.questions_for(e["preset"]))["answers"]
        for key, want in e["answer"].items():
            a = answers.get(key) or {}
            got = (a.get("choice") if a.get("type") == "choice"
                   else bool((a.get("noul") or 0) >= 0.5)
                   if a.get("type") == "noul" else a.get("score"))
            total += 1
            hits += got == want
            rows.append([e["label"], key, str(want), str(got), "✅" if got == want else "❌"])
    return rows, f"**{hits}/{total}** expected decisions reproduced on this machine."


# ------------------------------------------------------------------ page
def build():
    preset_info = "\n".join(
        f"- **{n}** — {p['label']}: {p['note']}" for n, p in presets.PRESETS.items())

    with gr.Blocks(title="Laya", theme=gr.themes.Soft(), css=CARD_CSS) as demo:
        with gr.Row():
            gr.Markdown(
                "# Laya\n\n"
                "Put a message in **card 01**, press **Decide**, and the model's "
                "answers land in **card 02** — about 90 ms later, on your own "
                "graphics card.\n\n"
                "> It does **not** write replies. Every value in card 02 is "
                "returned by the model, not written by it."
            )
            theme_btn = gr.Button("Dark mode", elem_id="theme-toggle",
                                  scale=0, min_width=108, size="sm")

        with gr.Tabs():
            # ============================== cards 01 + 02 ==============================
            with gr.Tab("Decide", id="decide"):
                with gr.Row(equal_height=False):
                    with gr.Column(elem_classes=["card"], scale=1, min_width=430):
                        with gr.Row(elem_classes=["card-top"]):
                            gr.HTML('<span class="card-num">01</span>')
                            gr.HTML('<span class="card-title">The question</span>')
                            run_btn = gr.Button("Decide ▶", variant="primary", scale=0,
                                                min_width=130)
                        message = gr.Textbox(
                            label="Message", lines=10, show_label=False,
                            placeholder="Paste a ticket, email or message here...")
                        gr.Markdown("**Ask about it**")
                        preset_box = gr.Dropdown(PRESET_CHOICES,
                                                 value=presets.DEFAULT_PRESET,
                                                 label="Question set")
                        questions_box = gr.Textbox(
                            label="Your own questions (JSON, blank = use the set above)",
                            lines=4,
                            placeholder='{"my_key": {"type": "noul", "instructions": "..."}}')

                    with gr.Column(elem_classes=["card"], scale=1, min_width=430):
                        with gr.Row(elem_classes=["card-top"]):
                            gr.HTML('<span class="card-num">02</span>')
                            gr.HTML('<span class="card-title">The answer</span>')
                            clear_btn = gr.Button("Clear", scale=0, min_width=90)
                        answer = gr.Markdown(
                            '<div class="placeholder">Nothing yet. Press '
                            '<b>Decide</b> in card 01.</div>',
                            elem_id="answer", elem_classes=["anim-replay"])
                        meta = gr.Markdown("")

                # ============================== card 03 ==============================
                with gr.Column(elem_classes=["card"]):
                    with gr.Row(elem_classes=["card-top"]):
                        gr.HTML('<span class="card-num">03</span>')
                        gr.HTML(
                            f'<span class="card-title">Examples '
                            f'({len(presets.EXAMPLES)})</span>')
                        gr.HTML(
                            '<span style="font-size:0.85rem;color:var(--body-text-color-subdued)">'
                            'each card loads its message into card 01</span>')
                    cards = []
                    for i in range(0, len(presets.EXAMPLES), 3):
                        with gr.Row(equal_height=False):
                            for e in presets.EXAMPLES[i:i + 3]:
                                with gr.Column(elem_classes=["card"], scale=1,
                                               min_width=250, variant="compact"):
                                    gr.HTML(f'<div class="card-label">{e["label"]}</div>')
                                    gr.HTML(
                                        f'<div class="card-msg">{e["text"]}</div>')
                                    gr.HTML(
                                        f'<div class="card-expect">should give '
                                        f'{_expect_text(e)}</div>')
                                    btn = gr.Button("Use this", size="sm")
                                    cards.append((btn, e["label"]))

                for btn, label in cards:
                    btn.click(use_example, inputs=[gr.State(label)],
                              outputs=[message, preset_box])

            # ================================= batch =================================
            with gr.Tab("Batch"):
                gr.Markdown("## Batch\n\nOne message per line, the same questions "
                            "applied to all of them in shared forward passes.")
                b_preset = gr.Dropdown(PRESET_CHOICES, value=presets.DEFAULT_PRESET,
                                       label="Question set")
                b_questions = gr.Textbox(label="Your own questions (JSON, blank = preset)",
                                         lines=3)
                b_input = gr.Textbox(lines=10, label="Messages, one per line")
                b_run = gr.Button("Decide all of them", variant="primary")
                b_summary = gr.Markdown()
                b_out = gr.Dataframe(interactive=False, label="Decisions")

            # ================================= about =================================
            with gr.Tab("About"):
                gr.Markdown(
                    "## What this is\n\n"
                    "A local decision engine over `laya-multilingual`: 322M "
                    "parameters, non-autoregressive, 100+ languages, one forward "
                    "pass answers every question at once.\n\n"
                    "**It cannot generate text.** That is what the model is, not a "
                    "limitation of this app. A generator would be a different engine "
                    "and an amendment to `contract.md`.\n\n"
                    "### Question sets\n\n" + preset_info + "\n\n"
                    "### Honest limits\n\n"
                    "- Over-confident as shipped. It will say 100% and be wrong.\n"
                    "- Arabic macro accuracy measured at 0.400 on 20-way intent. "
                    "Good for 3-8 buckets, not 20 fine labels.\n"
                    "- Ordinal `score` questions have a measured position bias in "
                    "every language. Using one on non-English text raises a warning.\n"
                    "- `noul` can under-report \"true\". Cross-check with a "
                    "2-option `choice`.\n"
                    "- Weak on low-resource languages: Swahili, Tamil, Amharic.\n\n"
                    "### Safety\n\n"
                    f"Bound to `{config.HOST}`. Reachable from this machine only. "
                    "No authentication, so it must never be exposed.\n\n"
                    f"Chat `{config.PORT}` · API `{config.API_PORT}` · n8n is on 8888."
                )
                score_btn = gr.Button("Score all shipped examples", variant="primary")
                score_summary = gr.Markdown()
                score_out = gr.Dataframe(headers=["example", "question", "expected",
                                                  "got", "ok"],
                                         interactive=False, label="Result")
                score_btn.click(run_all_examples, outputs=[score_out, score_summary])

        run_btn.click(decide, inputs=[message, preset_box, questions_box],
                      outputs=[answer, meta])
        message.submit(decide, inputs=[message, preset_box, questions_box],
                       outputs=[answer, meta])
        clear_btn.click(
            lambda: ("", '<div class="placeholder">Cleared.</div>', ""),
            outputs=[message, answer, meta])
        b_run.click(batch_decide, inputs=[b_input, b_preset, b_questions],
                    outputs=[b_out, b_summary])

        # Replay the answer animation whenever new results land in card 02.
        # A MutationObserver is the reliable way to do this: it fires after
        # Gradio has swapped the content, so no polling and no double-binding.
        demo.load(js=REPLAY_JS)
        demo.load(js=THEME_BOOT_JS)
        theme_btn.click(js="() => window.__layaToggleTheme && window.__layaToggleTheme()")
    return demo


if __name__ == "__main__":
    build().launch(
        server_name=config.HOST,
        server_port=config.PORT,
        inbrowser=True,
        share=False,
    )
