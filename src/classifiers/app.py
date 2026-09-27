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

from classifiers import config  # noqa: E402
from classifiers.text import agent, engine, presets
from classifiers.image import presets as image_presets  # noqa: E402

import gradio as gr  # noqa: E402

CARD_CSS = """
/* ==========================================================================
   THEME - Anthropic / Claude visual language
   Two designed palettes, and the token set is mapped onto Gradio's OWN css
   variables so every built-in component follows. Overriding the variables
   rather than individual selectors is what makes the whole app consistent;
   the earlier version fought selectors one at a time and lost, which is why
   Gradio's default blue label pills were still showing.

   Every text/background pair is asserted in tools/contrast.py (WCAG AA).
   ========================================================================== */
:root {
    --page:        #f5f4ed;   /* the cream Claude sits on */
    --surface:     #ffffff;
    --surface-2:   #faf9f5;
    --line:        #e3e1d9;
    --line-hi:     #8f8b81;
    --ink:         #1f1e1d;
    --ink-soft:    #5c5b57;
    --ink-faint:   #6e6d67;
    --clay:        #d97757;   /* the signature Claude orange */
    --clay-dk:     #b85c3e;   /* passes AA with white text */
    --clay-soft:   #f6e6de;
    --good:        #2f7d4f;
    --bad:         #b3402e;
    --shadow:      0 1px 2px rgba(31,30,29,.04), 0 4px 14px rgba(31,30,29,.05);
    --shadow-hi:   0 2px 4px rgba(31,30,29,.06), 0 12px 30px rgba(31,30,29,.09);
    --ring:        rgba(217,119,87,.45);
    --radius:      14px;

    /* ---- map onto Gradio's variables ---- */
    --body-background-fill:        var(--page);
    --body-text-color:             var(--ink);
    --body-text-color-subdued:     var(--ink-soft);
    --block-background-fill:       var(--surface);
    --block-background-fill-soft:  var(--surface-2);
    --block-border-color:          var(--line);
    --block-border-width:          1px;
    --block-radius:                10px;
    --block-title-text-color:      var(--ink);
    --block-title-background-fill: transparent;
    --block-info-text-color:       var(--ink-soft);
    --block-info-background-fill:  var(--surface-2);
    --block-info-border-color:     var(--line);
    /* the blue pills: Claude labels are plain small muted text, no chip */
    --block-label-background-fill:     transparent;
    --block-label-background-fill-hover: transparent;
    --block-label-border-color:        transparent;
    --block-label-text-color:          var(--ink-soft);
    --block-label-padding:             2px 0 6px 0;
    --block-label-margin:              0;
    --block-label-radius:              0;
    --border-color-primary:        var(--line);
    --border-color-accent:        var(--clay);
    --border-color-accent-subdued: var(--clay-soft);
    --color-accent:                var(--clay);
    --color-accent-soft:           var(--clay-soft);
    --input-background-fill:         var(--surface-2);
    --input-background-fill-focus:   var(--surface);
    --input-background-fill-hover:   var(--surface-2);
    --input-border-color:            var(--line);
    --input-border-color-focus:      var(--clay);
    --checkbox-background-fill:      var(--surface-2);
    --checkbox-background-fill-selected: var(--clay);
    --table-even-background-fill:    var(--surface-2);
    --table-odd-background-fill:     var(--surface);
    --slider-color:                  var(--clay);
    --button-primary-background-fill:       #1f1e1d;
    --button-primary-background-fill-hover: #000000;
    --button-primary-text-color:            #f5f4ed;
    --button-primary-border-color:          #1f1e1d;
    --button-cancel-background-fill:        var(--surface-2);
    --button-cancel-background-fill-hover:  var(--line-hi);
    --button-cancel-text-color:             var(--ink);
    --button-cancel-border-color:           var(--line);
    --button-secondary-background-fill:     var(--surface-2);
    --button-secondary-text-color:          var(--ink);
    --button-secondary-border-color:        var(--line);
}

html[data-theme="dark"] {
    --page:        #1f1e1d;
    --surface:     #262624;
    --surface-2:   #30302e;
    --line:        #3e3e3c;
    --line-hi:     #78776f;
    --ink:         #f5f4ed;
    --ink-soft:    #c2c2c0;
    --ink-faint:   #94938e;
    --clay:        #e08a6a;
    --clay-dk:     #c97659;
    --clay-soft:   #3a2b25;
    --good:        #6fcf97;
    --bad:         #f08a7d;
    --shadow:      0 1px 2px rgba(0,0,0,.35), 0 4px 14px rgba(0,0,0,.4);
    --shadow-hi:   0 2px 4px rgba(0,0,0,.45), 0 12px 30px rgba(0,0,0,.5);
    --ring:        rgba(224,138,106,.5);
    --button-primary-background-fill:       #f5f4ed;
    --button-primary-background-fill-hover: #ffffff;
    --button-primary-text-color:            #1f1e1d;
    --button-primary-border-color:          #f5f4ed;
    color-scheme: dark;
}

@media (prefers-color-scheme: dark) {
    html:not([data-theme="light"]) {
        --page:        #1f1e1d;
        --surface:     #262624;
        --surface-2:   #30302e;
        --line:        #3e3e3c;
        --line-hi:     #78776f;
        --ink:         #f5f4ed;
        --ink-soft:    #c2c2c0;
        --ink-faint:   #94938e;
        --clay:        #e08a6a;
        --clay-dk:     #c97659;
        --clay-soft:   #3a2b25;
        --good:        #6fcf97;
        --bad:         #f08a7d;
        --shadow:      0 1px 2px rgba(0,0,0,.35), 0 4px 14px rgba(0,0,0,.4);
        --shadow-hi:   0 2px 4px rgba(0,0,0,.45), 0 12px 30px rgba(0,0,0,.5);
        --ring:        rgba(224,138,106,.5);
        --button-primary-background-fill:       #f5f4ed;
        --button-primary-background-fill-hover: #ffffff;
        --button-primary-text-color:            #1f1e1d;
        --button-primary-border-color:          #f5f4ed;
        color-scheme: dark;
    }
}

/* ---- page ---- */
html, body {
    background: var(--page) !important;
    color: var(--ink) !important;
    font-family: "Segoe UI", system-ui, -apple-system, "Noto Sans Arabic",
                 "Noto Sans", "Helvetica Neue", sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
h1 { font-weight: 650 !important; letter-spacing: -0.015em !important;
     color: var(--ink) !important; font-size: 1.6rem !important; }
h1 + p { color: var(--ink-soft) !important; font-size: .95rem !important;
         line-height: 1.6 !important; max-width: 62ch; }
footer, .gradio-container footer { display: none !important; }

/* ---- tabs: quiet, Claude-style underline ---- */
.tabs > .tab-nav { border-bottom: 1px solid var(--line) !important; gap: 4px !important; }
.tabs > .tab-nav button {
    font-weight: 550 !important; font-size: .9rem !important;
    color: var(--ink-soft) !important; background: transparent !important;
    border: none !important; padding: 10px 14px !important;
    transition: color .2s ease !important;
}
.tabs > .tab-nav button:hover { color: var(--ink) !important; }
.tabs > .tab-nav button.selected {
    color: var(--ink) !important; background: transparent !important;
    border: none !important; border-bottom: 2px solid var(--clay) !important;
}

/* ---- cards ---- */
.card {
    border: 1px solid var(--line) !important;
    border-radius: var(--radius) !important;
    padding: 22px 24px !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow) !important;
    height: 100%;
    transition: box-shadow .3s ease, transform .3s ease, border-color .3s ease,
                background-color .35s ease;
    animation: cardIn .6s cubic-bezier(.2,.7,.3,1) both;
}
.card:hover { box-shadow: var(--shadow-hi) !important; transform: translateY(-2px);
              border-color: var(--line-hi) !important; }
@keyframes cardIn {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: none; }
}
.card-top {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px; padding-bottom: 16px;
    border-bottom: 1px solid var(--line);
}
.card-num {
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 30px; height: 30px; padding: 0 9px;
    border-radius: 8px; color: #fff; background: var(--clay-dk);
    font-weight: 700; font-size: .74rem; letter-spacing: .08em;
}
html[data-theme="dark"] .card-num { color: #1f1e1d; }
.card-title { font-weight: 620; font-size: 1rem; color: var(--ink); flex: 1;
              letter-spacing: -0.005em; }

/* ---- example cards ---- */
.card-label { font-weight: 600; font-size: .85rem; margin-bottom: 8px; color: var(--ink); }
.card-msg {
    font-size: .85rem; line-height: 1.65; padding: 12px 14px; margin-bottom: 12px;
    border-radius: 8px; background: var(--surface-2); color: var(--ink-soft);
    min-height: 82px; max-height: 140px; overflow-y: auto;
    border-right: 2px solid var(--clay);
    transition: border-color .25s ease, background-color .35s ease;
}
.card-expect { font-size: .78rem; color: var(--ink-soft); margin-bottom: 12px;
               font-weight: 550; }

/* ---- answer panel ---- */
.anim-replay { animation: answerIn .45s cubic-bezier(.2,.7,.3,1) both; }
@keyframes answerIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: none; }
}
/* Card 02 has far less content than card 01. Without a floor it renders as a
   short stub beside a tall card and the row looks broken, so give the answer
   area a minimum height that balances the two. */
#answer { min-height: 330px; }
.placeholder { color: var(--ink-faint) !important; font-style: normal; padding: 40px 0;
               text-align: center; font-size: .92rem; }

/* ---- buttons ---- */
button {
    border-radius: 8px !important; font-weight: 560 !important;
    letter-spacing: 0 !important; font-size: .88rem !important;
    box-shadow: none !important;
    transition: transform .15s ease, box-shadow .2s ease, filter .2s ease,
                background-color .35s ease, color .35s ease !important;
}
button:hover:not(:disabled) { filter: brightness(.96); }
button.primary:hover:not(:disabled) { transform: translateY(-1px);
                                      box-shadow: 0 6px 18px rgba(0,0,0,.16) !important; }
button:active:not(:disabled) { transform: translateY(0) scale(.985); }
button:focus-visible, textarea:focus-visible, input:focus-visible,
select:focus-visible, [tabindex]:focus-visible {
    outline: 2px solid var(--ring) !important; outline-offset: 2px !important;
}
button.primary { font-weight: 600 !important; }

/* ---- inputs ---- */
textarea, input, select {
    border-radius: 8px !important; border-color: var(--line) !important;
    background: var(--surface-2) !important; color: var(--ink) !important;
    caret-color: var(--clay) !important;
    transition: border-color .2s ease, box-shadow .2s ease,
                background-color .35s ease !important;
}
textarea:focus, input:focus, select:focus {
    border-color: var(--clay) !important;
    box-shadow: 0 0 0 3px var(--ring) !important;
}
textarea::placeholder, input::placeholder { color: var(--ink-faint) !important;
                                            opacity: 1 !important; }
.block, .form, .panel, .gr-box { background: transparent !important; }
.spacer { background: transparent !important; }
#theme-toggle { min-width: 104px !important; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .001ms !important; animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
    }
}
"""

# Fills card 01 and presses Decide from the URL, so tools/snapshot.py can capture
# a REAL end-to-end result rather than an empty card. Not a mock: this drives the
# actual page, the actual button and the actual model.
PREFILL_JS = """
() => {
  const SAMPLE = {SAMPLE_JSON};
  const q = new URL(window.location.href).searchParams;
  if (q.get('sample') === null) return;
  const item = SAMPLE[parseInt(q.get('sample'), 10) || 0];
  if (!item) return;

  const put = (el, value) => {
    const proto = el instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement : HTMLInputElement;
    Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
  };

  const fire = () => {
    const areas = Array.from(document.querySelectorAll('textarea'));
    if (!areas.length) { setTimeout(fire, 300); return; }
    put(areas[0], item.text);
    const select = document.querySelector('select');
    if (select) {
      const opt = Array.from(select.options).find(o => o.value === item.preset);
      if (opt) { select.value = item.preset;
                 select.dispatchEvent(new Event('change', {bubbles: true})); }
    }
    setTimeout(() => {
      const btn = document.querySelector('#run button') ||
                  document.querySelector('#run') ||
                  document.querySelector('button.primary');
      if (btn) btn.click();
    }, 500);
  };
  setTimeout(fire, 900);
}
"""


# Applies the chosen theme before first paint, so there is no white flash.
THEME_BOOT_JS = """
() => {
  const KEY = 'laya-theme';
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  // A saved choice wins. Otherwise ?__theme= deep-links a theme, which is how
  // tools/snapshot.py captures light and dark deterministically.
  const q = new URL(window.location.href).searchParams.get('__theme');
  const want = (saved === 'dark' || saved === 'light') ? saved
             : (q === 'dark' || q === 'light') ? q : null;
  if (want) root.setAttribute('data-theme', want);
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

# The Claude palette, expressed as Gradio theme objects.
#
# This has to go through the theme API, not just CSS. Gradio styles its own
# components (buttons, labels, tabs, focus rings) from the theme object at
# runtime, so a CSS variable override never reaches them - which is exactly why
# the Decide button stayed blue and the label pills stayed blue however hard the
# stylesheet pushed. CARD_CSS then handles only the bespoke card chrome.
CLAY = gr.themes.Color(
    name="clay", c50="#fdf3ee", c100="#f9e3d8", c200="#f3c7b1", c300="#eba98a",
    c400="#e28a64", c500="#d97757", c600="#c05f40", c700="#9d4a31",
    c800="#7a3824", c900="#572616", c950="#2e130b")

WARM_NEUTRAL = gr.themes.Color(
    name="warm", c50="#faf9f5", c100="#f2f0e9", c200="#e3e1d9", c300="#d0cdc3",
    c400="#b0ada3", c500="#918e85", c600="#6e6d67", c700="#5c5b57",
    c800="#3d3d3a", c900="#1f1e1d", c950="#0e0e0d")

WARM_SECONDARY = gr.themes.Color(
    name="stone", c50="#f4f2ee", c100="#e8e4dc", c200="#d5cfc4", c300="#bcb3a4",
    c400="#a2977f", c500="#8a7d62", c600="#71664f", c700="#5a513f",
    c800="#433c2f", c900="#2d281f", c950="#171410")


def light_theme():
    """The Claude palette as a Gradio theme.

    Values are filtered against the keys this Gradio build actually accepts, so a
    Gradio upgrade that renames a variable degrades to "that one control keeps the
    default" instead of crashing the app on import. Everything the build does
    accept is applied.
    """
    import inspect

    clay, ink, soft, faint = "#d97757", "#1f1e1d", "#5c5b57", "#6e6d67"
    page, surface, raised = "#f5f4ed", "#ffffff", "#faf9f5"
    line = "#e3e1d9"
    dpage, dsurface, draised = "#1f1e1d", "#262624", "#30302e"
    dline, dink, dsoft = "#3e3e3c", "#f5f4ed", "#c2c2c0"

    want = {
        "body_background_fill": page, "body_background_fill_dark": dpage,
        "body_text_color": ink, "body_text_color_dark": dink,
        "body_text_color_subdued": soft, "body_text_color_subdued_dark": dsoft,
        "background_fill_primary": page, "background_fill_primary_dark": dpage,
        "block_background_fill": surface, "block_background_fill_dark": dsurface,
        "block_border_color": line, "block_border_color_dark": dline,
        "block_title_text_color": ink, "block_title_text_color_dark": dink,
        # Claude labels are plain small muted text, not coloured chips
        "block_label_background_fill": "transparent",
        "block_label_background_fill_dark": "transparent",
        "block_label_border_color": "transparent",
        "block_label_border_color_dark": "transparent",
        "block_label_text_color": soft, "block_label_text_color_dark": dsoft,
        "block_info_background_fill": raised,
        "block_info_background_fill_dark": draised,
        "border_color_primary": line, "border_color_primary_dark": dline,
        "input_background_fill": raised, "input_background_fill_dark": draised,
        "input_background_fill_focus": surface,
        "input_background_fill_focus_dark": dsurface,
        "input_border_color": line, "input_border_color_dark": dline,
        # near-black pill in light, cream pill in dark - Claude's primary button
        "button_primary_background_fill": ink,
        "button_primary_background_fill_dark": dink,
        "button_primary_background_fill_hover": "#000000",
        "button_primary_background_fill_hover_dark": "#ffffff",
        "button_primary_text_color": page,
        "button_primary_text_color_dark": ink,
        "button_primary_border_color": ink,
        "button_primary_border_color_dark": dink,
        "button_secondary_background_fill": raised,
        "button_secondary_background_fill_dark": draised,
        "button_secondary_text_color": ink, "button_secondary_text_color_dark": dink,
        "button_secondary_border_color": line,
        "button_secondary_border_color_dark": dline,
        "button_cancel_background_fill": raised,
        "button_cancel_background_fill_dark": draised,
        "table_even_background_fill": raised,
        "table_even_background_fill_dark": draised,
        "table_odd_background_fill": surface,
        "table_odd_background_fill_dark": dsurface,
    }

    base = gr.themes.Base(primary_hue=CLAY, secondary_hue=WARM_SECONDARY,
                          neutral_hue=WARM_NEUTRAL)
    accepted = set(inspect.signature(base.set).parameters)
    applied = {k: v for k, v in want.items() if k in accepted}
    dropped = sorted(set(want) - set(applied))
    if dropped:
        print(f"[laya] theme: this Gradio build has no {', '.join(dropped)}")
    return base.set(**applied)


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


def classify_url(url):
    """Fetch an image from a URL and classify it. Card 04 -> card 05.

    This is how Unsplash photos are used: the repository stores the URL, never
    the photograph, and the bytes are fetched on this machine only when asked.
    image/remote.py guards the request.
    """
    from classifiers.image import engine as image_engine, agent as image_agent, remote

    url = (url or "").strip()
    if not url:
        return image_agent.compose([])

    try:
        data, ctype, final = remote.fetch(url)
    except ValueError as exc:
        return (f"**Refused.**\n\n{exc}\n\n"
                f"<small>Only https, and only the hosts listed in "
                f"`classifiers/image/remote.py`.</small>", "", [])

    t0 = time.perf_counter()
    result = image_engine.classify(data)
    dt = (time.perf_counter() - t0) * 1000
    name = final.rsplit("/", 1)[-1].split("?")[0] or "image"
    result.update(name=name, url=final, ctype=ctype)
    markdown, meta, rows = image_agent.compose([result])
    return markdown, (f"{meta} · fetched + {dt:.0f} ms" if meta else ""), rows


# ------------------------------------------------------------------ image tab
def _collect(paths):
    """Gradio hands back a list of paths, a single path, or a tempfile object."""
    if not paths:
        return []
    if isinstance(paths, (str, Path)):
        return [paths]
    if isinstance(paths, (list, tuple)):
        return [p for p in paths if p]
    return [paths]


def classify_images(files):
    """Card 04 -> card 05. Delegates to the image agent; decides nothing."""
    from classifiers.image import engine as image_engine, agent as image_agent

    paths = _collect(files)
    if not paths:
        return image_agent.compose([])

    missing = image_engine.ensure_dependencies()
    if missing:
        return (f"**Missing dependencies:** `{'`, `'.join(missing)}`\n\n"
                f"Run `installer.ps1` again to install them.", "", [])

    t0 = time.perf_counter()
    try:
        results = image_engine.classify_many(paths)
    except Exception as exc:  # noqa: BLE001
        return f"**The image model failed.**\n\n`{type(exc).__name__}: {exc}`", "", []
    dt = (time.perf_counter() - t0) * 1000

    markdown, meta, rows = image_agent.compose(results)
    if meta:
        meta = f"{meta} · {dt:.0f} ms"
    return markdown, meta, rows


def free_image_model():
    """Manual VRAM release, for when the user wants the headroom back now."""
    from classifiers import gpu
    from classifiers.image import engine as image_engine
    was = image_engine.resident()
    image_engine.release()
    if not was:
        return f"The image model was not loaded. {gpu.report()}"
    return f"Image model unloaded. {gpu.report()}"


def image_status():
    from classifiers import gpu
    from classifiers.image import engine as image_engine, agent as image_agent
    d = image_engine.diagnostics()
    state = "resident in VRAM" if d["loaded"] else "not loaded"
    return (f"**{config.IMAGE_MODEL_ID}** — {image_agent.how_it_works()}\n\n"
            f"- state: {state}\n"
            f"- {gpu.report()}\n"
            f"- process RAM: {d['rss_gb']} GB\n\n"
            f"<small>Weights fetched with a three-file allowlist. The upstream "
            f"repository also contains `training_args.bin`, a pickle the Hub "
            f"flags as unsafe; it is never downloaded.</small>")




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

    with gr.Blocks(title="Laya", theme=light_theme(), css=CARD_CSS) as demo:
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
            # Only the selected classifier's tabs exist for this process. A hidden
            # tab cannot be reached, so its model is never loaded - which is the
            # whole point of choosing at startup rather than managing VRAM later.
            # ============================== cards 01 + 02 ==============================
            with gr.Tab("Decide", id="decide", visible=config.WANT_TEXT):
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=["card"], scale=1, min_width=430):
                        with gr.Row(elem_classes=["card-top"]):
                            gr.HTML('<span class="card-num">01</span>')
                            gr.HTML('<span class="card-title">The question</span>')
                            run_btn = gr.Button("Decide ▶", variant="primary", scale=0,
                                                min_width=130, elem_id="run")
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

                    with gr.Column(elem_classes=["card"], scale=1, min_width=430,
                                   variant="compact"):
                        with gr.Row(elem_classes=["card-top"]):
                            gr.HTML('<span class="card-num">02</span>')
                            gr.HTML('<span class="card-title">The answer</span>')
                            clear_btn = gr.Button("Clear", scale=0, min_width=84, size="sm")
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

            # ================================ image ================================
            with gr.Tab("Image", id="image", visible=config.WANT_IMAGE):
                gr.Markdown(
                    "## AI or human?\n\n"
                    "Attach one image or a whole folder's worth. The second model "
                    "here is a fine-tuned **SigLIP**: it looks at a 224×224 thumbnail "
                    "and returns `ai` or `hum` with probabilities."
                )
                with gr.Row(equal_height=True):
                    with gr.Column(elem_classes=["card"], scale=1, min_width=430):
                        with gr.Row(elem_classes=["card-top"]):
                            gr.HTML('<span class="card-num">04</span>')
                            gr.HTML('<span class="card-title">Attach images</span>')
                            img_run = gr.Button("Classify ▶", variant="primary",
                                                scale=0, min_width=130, elem_id="img-run")
                        upload = gr.File(
                            label="Attach images — drop, or browse",
                            file_count="multiple",
                            file_types=image_presets.IMAGE_EXTS,
                            type="filepath",
                            height=170)
                        preview = gr.Image(label="First image", height=170,
                                           interactive=False, visible=False)

                        gr.Markdown("**Or paste an image URL**")
                        url_box = gr.Textbox(
                            label="Image URL (https only)",
                            placeholder=image_presets.EXAMPLE_URLS[0],
                            lines=2)
                        with gr.Row():
                            url_run = gr.Button("Fetch and classify ▶",
                                                variant="primary", scale=0,
                                                min_width=170)
                        gr.Markdown(
                            "Try one: " + " · ".join(
                                f"<details><summary>{u.split('photo-')[-1][:18]}…</summary>"
                                f"`{u}`</details>" for u in image_presets.EXAMPLE_URLS[:2])
                            + f" — or any of the {len(image_presets.EXAMPLE_URLS)} in "
                              f"`classifiers/image/presets.py`.")

                        gr.Markdown("**Model**")
                        img_status = gr.Markdown(image_status())
                        free_btn = gr.Button("Unload the image model",
                                             size="sm", scale=0)

                    with gr.Column(elem_classes=["card"], scale=1, min_width=430,
                                   variant="compact"):
                        with gr.Row(elem_classes=["card-top"]):
                            gr.HTML('<span class="card-num">05</span>')
                            gr.HTML('<span class="card-title">The verdict</span>')
                            img_clear = gr.Button("Clear", scale=0, min_width=84,
                                                  size="sm")
                        img_answer = gr.Markdown(
                            '<div class="placeholder">Nothing yet. Press '
                            '<b>Classify</b> in card 04.</div>',
                            elem_id="img-answer", elem_classes=["anim-replay"])
                        img_meta = gr.Markdown("")
                        img_table = gr.Dataframe(
                            headers=["file", "size", "verdict", "confidence"],
                            interactive=False, visible=False, wrap=True)

            # ================================= batch =================================
            with gr.Tab("Batch", visible=config.WANT_TEXT):
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

        # ---- image tab wiring
        def _first(paths):
            got = _collect(paths)
            return gr.update(value=str(got[0]), visible=bool(got)) if got \
                else gr.update(value=None, visible=False)

        upload.change(_first, inputs=[upload], outputs=[preview])
        img_run.click(classify_images, inputs=[upload],
                      outputs=[img_answer, img_meta, img_table])
        url_run.click(classify_url, inputs=[url_box],
                      outputs=[img_answer, img_meta, img_table])
        img_clear.click(
            lambda: (gr.update(value=None), gr.update(value=None, visible=False),
                     gr.update(value=""), gr.update(value=[], visible=False),
                     gr.update(value='<div class="placeholder">Cleared.</div>'),
                     gr.update(value=""), gr.update(value="")),
            outputs=[upload, preview, img_status, img_table, img_answer, img_meta,
                     url_box])
        free_btn.click(free_image_model, outputs=[img_status])

        # Replay the answer animation whenever new results land in card 02.
        # A MutationObserver is the reliable way to do this: it fires after
        # Gradio has swapped the content, so no polling and no double-binding.
        demo.load(js=REPLAY_JS)
        demo.load(js=THEME_BOOT_JS)
        demo.load(js=PREFILL_JS.replace("{SAMPLE_JSON}", json.dumps(
            [{"text": e["text"], "preset": e["preset"]} for e in presets.EXAMPLES],
            ensure_ascii=False)))
        theme_btn.click(js="() => window.__layaToggleTheme && window.__layaToggleTheme()")
    return demo


if __name__ == "__main__":
    build().launch(
        server_name=config.HOST,
        server_port=config.PORT,
        inbrowser=True,
        share=False,
    )
