r"""Acceptance tests for the agent layer.

The important one is test_never_invents_a_value: contract section 5 says the agent
may not fabricate an answer. These tests check that structurally, plus the
question validation and the worked examples.

Run:  .venv\Scripts\python.exe -m pytest tests -q
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from classifiers.text import agent, presets  # noqa: E402
from classifiers.image import agent as image_agent  # noqa: E402
from classifiers.image import presets as image_presets  # noqa: E402
from classifiers import config  # noqa: E402


# ---------------------------------------------------------------- validation
def test_presets_all_valid():
    for name, preset in presets.PRESETS.items():
        ok, why = presets.validate(preset["questions"])
        assert ok, f"preset {name} is invalid: {why}"


def test_choice_needs_two_options():
    ok, why = presets.validate({"q": {"type": "choice", "instructions": "x",
                                      "criteria": {"only": "one"}}})
    assert not ok and "at least 2" in why


def test_choice_rejects_too_many_options():
    crit = {f"o{i}": f"desc {i}" for i in range(21)}
    ok, why = presets.validate({"q": {"type": "choice", "instructions": "x",
                                      "criteria": crit}})
    assert not ok and "20 or fewer" in why


def test_unknown_type_rejected():
    ok, why = presets.validate({"q": {"type": "sentiment_guess", "instructions": "x"}})
    assert not ok and "unknown type" in why


def test_missing_instructions_rejected():
    ok, why = presets.validate({"q": {"type": "noul"}})
    assert not ok and "instructions" in why


def test_questions_from_rejects_bad_json():
    q, err = agent.questions_from("triage", "{not json")
    assert q is None and "valid JSON" in err


def test_questions_from_blank_uses_preset():
    q, err = agent.questions_from("triage", "")
    assert err is None and set(q) == set(presets.TRIAGE)


def test_questions_from_rejects_unknown_preset():
    q, err = agent.questions_from("nope", "")
    assert q is None and "No question set" in err


# ---------------------------------------------------------------- no fabrication
def test_never_invents_a_value(monkeypatch):
    """If the engine returns nothing, the agent must say so and invent nothing."""
    monkeypatch.setattr(agent.engine, "decide",
                        lambda *a, **k: {"answers": {}, "usage": {"input_tokens": 3}})
    reply, result = agent.compose("any text at all", presets.questions_for("triage"))
    assert result["answers"] == {}
    assert "no answers" in reply.lower()
    # Nothing invented: no percentage, no option rendered as a verdict, no
    # yes/no verdict. Checked as the exact markup the agent emits, not as bare
    # substrings - "no" occurs inside "not", "nothing" and "one".
    assert "%" not in reply
    assert "**yes**" not in reply and "**no**" not in reply
    for option in presets.TRIAGE["department"]["criteria"]:
        assert f"`{option}`" not in reply


def test_missing_field_is_reported_not_guessed(monkeypatch):
    """An answer that omits the chosen option must not have one supplied."""
    monkeypatch.setattr(agent.engine, "decide", lambda *a, **k: {
        "answers": {"department": {"type": "choice", "answer_confidence": 0.9}},
        "usage": {"input_tokens": 3}})
    reply, _ = agent.compose("x", presets.questions_for("triage"))
    assert "no choice" in reply.lower()
    assert "billing" not in reply          # did not invent the obvious default


def test_every_number_in_reply_comes_from_the_engine(monkeypatch):
    payload = {"answers": {
        "department": {"type": "choice", "choice": "billing",
                       "answer_confidence": 0.9123,
                       "probabilities": {"billing": 0.9123, "sales": 0.0877}},
        "refund_requested": {"type": "noul", "noul": 0.6543,
                             "answer_confidence": 0.6543}},
        "usage": {"input_tokens": 128}}
    monkeypatch.setattr(agent.engine, "decide", lambda *a, **k: payload)
    reply, _ = agent.compose("x", presets.questions_for("triage"))
    assert "billing" in reply
    assert "91%" in reply                 # 0.9123 rendered, from the engine
    assert "0.6543" in reply              # the noul value, verbatim
    assert "yes" in reply.lower()         # 0.6543 >= 0.5
    assert "128" in reply


def test_noul_below_half_reads_as_no(monkeypatch):
    monkeypatch.setattr(agent.engine, "decide", lambda *a, **k: {
        "answers": {"refund_requested": {"type": "noul", "noul": 0.2,
                                         "answer_confidence": 0.2}},
        "usage": {"input_tokens": 5}})
    reply, _ = agent.compose("x", {"refund_requested": presets.TRIAGE["refund_requested"]})
    assert "**no**" in reply


# ---------------------------------------------------------------- the bias guard
def test_score_on_non_english_raises_the_warning(monkeypatch):
    monkeypatch.setattr(agent.engine, "decide", lambda *a, **k: {
        "answers": {"severity": {"type": "score", "score": 2.0,
                                 "answer_confidence": 0.5}},
        "usage": {"input_tokens": 9}})
    reply, _ = agent.compose("العطل مستمر منذ أمس", presets.SCORE_DEMO)
    assert "position bias" in reply


def test_score_on_english_does_not_warn(monkeypatch):
    monkeypatch.setattr(agent.engine, "decide", lambda *a, **k: {
        "answers": {"severity": {"type": "score", "score": 2.0,
                                 "answer_confidence": 0.5}},
        "usage": {"input_tokens": 9}})
    reply, _ = agent.compose("the site has been down all week", presets.SCORE_DEMO)
    assert "position bias" not in reply


@pytest.mark.parametrize("text,expected", [
    ("hello there", False),
    ("I was charged twice", False),
    ("مرحبا", True),
    ("मैंने दो बार भुगतान किया", True),
    ("二重に請求されました", True),
    ("双重收费", True),
    ("이중 청구되었습니다", True),
    ("Υπερβολή", True),
    ("невозврат", True),
])
def test_script_detection(text, expected):
    assert agent.looks_non_english(text) is expected


# ---------------------------------------------------------------- examples
def test_every_example_is_well_formed():
    for e in presets.EXAMPLES:
        assert e["label"] and e["text"] and e["answer"]
        assert e["preset"] in presets.PRESETS
        assert presets.validate(presets.questions_for(e["preset"]))[0]


def test_every_example_key_exists_in_its_preset():
    for e in presets.EXAMPLES:
        questions = presets.questions_for(e["preset"])
        for key in e["answer"]:
            assert key in questions, f"{e['label']} expects unknown key {key}"


def test_presets_are_json_serialisable():
    json.dumps(presets.PRESETS)
    json.dumps(presets.EXAMPLES)


# ================================================================= image agent
# Same no-fabrication rule as the text agent (contract section 5): the image
# agent renders engine values and never invents a verdict.
def _good(name="a.png", label="ai", conf=0.9, **kw):
    d = {"ok": True, "name": name, "label": label, "confidence": conf,
         "probabilities": {"ai": conf if label == "ai" else 1 - conf,
                           "hum": 1 - conf if label == "ai" else conf},
         "detail": "224x224 input", "size": "900x600"}
    d.update(kw)
    return d


def test_image_agent_empty_says_so():
    md, meta, rows = image_agent.compose([])
    assert rows == [] and meta == ""
    assert "Classify" in md


def test_image_agent_renders_the_engine_label():
    md, meta, rows = image_agent.compose([_good(label="ai", conf=0.93)])
    assert "AI-generated" in md
    assert "93.0%" in md
    assert meta == "1 of 1 readable · 1 ai · 0 hum"
    assert rows == [["a.png", "900x600", "ai", "93.0%"]]


def test_image_agent_flags_low_confidence():
    md, _, _ = image_agent.compose([_good(label="hum", conf=0.42)])
    assert "uncertain" in md.lower()


def test_image_agent_does_not_invent_a_verdict_for_a_bad_file():
    md, meta, rows = image_agent.compose([
        _good(), {"ok": False, "name": "bad.bin", "error": "UnidentifiedImageError"}])
    assert "not classified" in md
    assert rows == [["a.png", "900x600", "ai", "90.0%"]]   # only the good one
    assert meta == "1 of 2 readable · 1 ai · 0 hum"


def test_image_agent_all_bad_is_not_a_verdict():
    md, meta, rows = image_agent.compose([
        {"ok": False, "name": "a.bin", "error": "boom"},
        {"ok": False, "name": "b.bin", "error": "boom"}])
    assert "None of those" in md
    assert rows == []
    assert "%" not in md                 # no confidence invented


def test_image_agent_carries_the_overfitting_caveat():
    md, _, _ = image_agent.compose([_good()])
    assert "overfit" in md.lower()


def test_image_presets_cover_common_formats():
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"):
        assert ext in image_presets.IMAGE_EXTS


def test_image_presets_label_every_model_label():
    for idx, label in config.IMAGE_LABELS.items():
        assert label in image_presets.LABEL_TEXT


# ================================================================== mode logic
@pytest.mark.parametrize("mode,want_text,want_image", [
    ("text", True, False),
    ("image", False, True),
    ("both", True, True),
])
def test_mode_enables_the_right_tabs(monkeypatch, mode, want_text, want_image):
    monkeypatch.setenv("CLASSIFIERS", mode)
    import importlib
    fresh = importlib.reload(config)
    assert fresh.APP_MODE == mode
    assert fresh.WANT_TEXT is want_text
    assert fresh.WANT_IMAGE is want_image
    monkeypatch.setenv("CLASSIFIERS", "text")
    importlib.reload(config)


def test_unknown_mode_falls_back_to_text(monkeypatch):
    monkeypatch.setenv("CLASSIFIERS", "nonsense")
    import importlib
    fresh = importlib.reload(config)
    assert fresh.APP_MODE == "text"
    monkeypatch.setenv("CLASSIFIERS", "text")
    importlib.reload(config)


# ==================================================================== safety
def test_image_weights_use_an_allowlist_not_a_blocklist():
    assert config.IMAGE_ALLOW_PATTERNS == [
        "config.json", "preprocessor_config.json", "model.safetensors"]
    # Nothing that could be a pickle is on the list.
    assert not any(p.endswith((".bin", ".pt", ".pth", ".ckpt", ".pkl"))
                   for p in config.IMAGE_ALLOW_PATTERNS)


def test_vram_budget_is_documented_in_gpu():
    from classifiers import gpu
    assert gpu.TEXT_HEADROOM_MB > 0
    assert gpu.BATCH_HEADROOM_MB >= gpu.TEXT_HEADROOM_MB