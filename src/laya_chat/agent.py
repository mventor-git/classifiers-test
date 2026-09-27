"""Agent layer - the decision composer.

Contract section 5. This layer may: derive structured questions from a message,
call the engine, compose a reply from the engine's returned values. It may not
invent probabilities, override an answer, or fabricate an answer when the engine
returns none.

That last rule is enforced structurally, not by convention: every number printed
below is read straight out of the engine's result dict. There is no arithmetic
here, no scoring, no fallback wording that could imply an answer we do not have.

There is no conversation state. Contract v1.1.0 removed the chat interface, so the
agent is a pure function of (message, questions) -> reply.
"""
import json

from . import engine, presets


def looks_non_english(text):
    """True if the text carries a non-Latin script.

    Contract section 8: ordinal `score` questions have a measured position bias in
    every language, and the model card bans them for non-English. Cheap range test,
    no dependency, no language-ID model.
    """
    for ch in text:
        o = ord(ch)
        if 0x0600 <= o <= 0x06FF:      # Arabic
            return True
        if 0x0900 <= o <= 0x097F:      # Devanagari
            return True
        if 0x0980 <= o <= 0x09FF:      # Bengali
            return True
        if 0x3040 <= o <= 0x30FF:      # Japanese kana
            return True
        if 0x4E00 <= o <= 0x9FFF:      # CJK
            return True
        if 0xAC00 <= o <= 0xD7AF:      # Hangul
            return True
        if 0x0370 <= o <= 0x03FF:      # Greek
            return True
        if 0x0400 <= o <= 0x04FF:      # Cyrillic
            return True
    return False


def _line_choice(key, asked, ans):
    chosen = ans.get("choice")
    if chosen is None:
        return f"- **{asked}** → _the engine returned no choice._"
    out = f"- **{asked}** → `{chosen}`"
    conf = ans.get("answer_confidence")
    if isinstance(conf, (int, float)):
        out += f" at {conf:.0%}"
    dist = ans.get("probabilities") or {}
    if dist:
        spread = " · ".join(f"{k} {v:.0%}"
                            for k, v in sorted(dist.items(), key=lambda kv: -kv[1]))
        out += f"\n  <small>{spread}</small>"
    return out


def _line_noul(key, asked, ans):
    p = ans.get("noul")
    if not isinstance(p, (int, float)):
        return f"- **{asked}** → _the engine returned no value._"
    return (f"- **{asked}** → **{'yes' if p >= 0.5 else 'no'}** "
            f"<small>(P(true) = {p:.4f})</small>")


def _line_score(key, asked, ans, spec):
    score = ans.get("score")
    if score is None:
        return f"- **{asked}** → _the engine returned no score._"
    levels = spec.get("criteria") or []
    top = max(len(levels) - 1, 1)
    return f"- **{asked}** → `{score}` on a 0–{top} scale"


def compose(text, questions):
    """Run the engine on one message and return the reply as markdown.

    Returns (reply_markdown, engine_result) so callers can assert on the raw
    values without re-parsing the rendered text.
    """
    result = engine.decide(text, questions)
    answers = result.get("answers") or {}
    usage = result.get("usage") or {}

    if not answers:
        return ("The engine returned no answers for this message. "
                "I am not going to guess at one."), result

    lines = []
    for key, ans in answers.items():
        spec = questions.get(key, {})
        kind = ans.get("type") or spec.get("type")
        asked = spec.get("instructions") or key
        if kind == "choice":
            lines.append(_line_choice(key, asked, ans))
        elif kind == "noul":
            lines.append(_line_noul(key, asked, ans))
        else:
            lines.append(_line_score(key, asked, ans, spec))

    header = (f"Decisions about your message "
              f"({usage.get('input_tokens', '?')} tokens, all questions in one pass):")
    out = [header, ""] + lines

    if any(q.get("type") == "score" for q in questions.values()) and looks_non_english(text):
        out += ["", "> ⚠️ These questions include an ordinal `score` and the message "
                    "is not English. The model has a measured position bias on "
                    "`score` in every language. Use a `choice` question instead."]

    out += ["", "<small>I do not write prose. Everything above is a value the model "
                "returned, not text it generated.</small>"]
    return "\n".join(out), result


def questions_from(preset_name, questions_json=""):
    """Blank box means use the preset. Otherwise the caller's questions win.

    Returns (questions, error_message). Exactly one is ever None.
    """
    if questions_json and questions_json.strip():
        try:
            q = json.loads(questions_json)
        except json.JSONDecodeError as exc:
            return None, f"**Not valid JSON:** {exc.msg} (line {exc.lineno})."
        ok, why = presets.validate(q)
        if not ok:
            return None, f"{why}"
        return q, None
    if preset_name not in presets.PRESETS:
        return None, f"No question set called {preset_name!r}."
    return presets.questions_for(preset_name), None
