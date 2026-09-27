"""Question presets and worked examples.

The things you can actually hand the app. Each preset is a named set of typed
questions; each example is a real message with the answer the engine gives for it,
so you can check the app against something known rather than guessing.
"""
import json

TRIAGE = {
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this message?",
        "criteria": {
            "billing": "invoices, payments, charges, refunds",
            "technical": "bugs, outages, errors, login problems",
            "sales": "pricing, plans, quotes, upgrades",
        },
    },
    "refund_requested": {
        "type": "noul",
        "instructions": "Does the sender explicitly ask for money back?",
    },
}

TONE = {
    "tone": {
        "type": "choice",
        "instructions": "What is the emotional tone of the sender?",
        "criteria": {
            "calm": "neutral, factual, matter of fact",
            "frustrated": "annoyed but civil, repeating themselves",
            "angry": "hostile, accusatory, threatening",
        },
    },
    "polite": {
        "type": "noul",
        "instructions": "Is the sender being courteous?",
    },
}

# Deliberately NOT offering a `score` question here. The model has a measured
# position bias on ordinal questions in every language (contract section 8), so
# presets use `choice` instead. See the score preset below, which is opt-in only.
SCORE_DEMO = {
    "severity": {
        "type": "score",
        "instructions": "How severe is this incident?",
        "criteria": ["cosmetic", "degraded", "outage", "data loss"],
    },
}

INTENT = {
    "intent": {
        "type": "choice",
        "instructions": "What is the sender trying to achieve?",
        "criteria": {
            "get_refund": "recover money already paid",
            "fix_problem": "stop something from being broken",
            "cancel": "end a subscription or contract",
            "upgrade": "buy more or a better plan",
            "ask_about_product": "information only, no action needed",
        },
    },
    "needs_human": {
        "type": "noul",
        "instructions": "Does this need a person, not an automatic reply?",
    },
}

PRESETS = {
    "triage": {"label": "Ticket triage", "questions": TRIAGE,
               "note": "Route a ticket and detect a refund request. Start here."},
    "intent": {"label": "Sender intent", "questions": INTENT,
               "note": "What the sender actually wants, and whether it needs a human."},
    "tone": {"label": "Tone check", "questions": TONE,
             "note": "Polite or not. Weakest of the presets - see README."},
    "score": {"label": "Severity (opt-in)", "questions": SCORE_DEMO,
              "note": "WARNING: ordinal questions have a measured position bias. "
                      "Demonstration only, do not rely on it."},
}

DEFAULT_PRESET = "triage"

# ---------------------------------------------------------------------------
# Worked examples. `answer` is what the engine returned on this machine on
# 2026-09-27, measured, not assumed. Used by the UI and by tests/test_agent.py.
# ---------------------------------------------------------------------------
EXAMPLES = [
    {
        "preset": "triage",
        "label": "Arabic - refund complaint",
        "text": "تم تحصيل المبلغ مني مرتين لفاتورة رقم 4411 في هذا الشهر. "
                "أرجو إعادة المبلغ إلى حسابي اليوم.",
        "answer": {"department": "billing", "refund_requested": True},
    },
    {
        "preset": "triage",
        "label": "Arabic - service outage",
        "text": "الواجهة لا تعمل منذ أمس ولا أستطيع تسجيل الدخول، "
                "هناك خطأ 500 في كل مرة.",
        "answer": {"department": "technical", "refund_requested": False},
    },
    {
        "preset": "triage",
        "label": "English - refund complaint",
        "text": "I was charged twice for invoice 4411 this month. Please refund it today.",
        "answer": {"department": "billing", "refund_requested": True},
    },
    {
        "preset": "triage",
        "label": "English - service outage",
        "text": "The API returns 500 errors and nobody on my team can log in.",
        "answer": {"department": "technical", "refund_requested": False},
    },
    {
        "preset": "intent",
        "label": "Arabic - cancel subscription",
        "text": "أريد إلغاء اشتراكي نهائياً، كيف أفعل ذلك؟",
        "answer": {"intent": "cancel"},
    },
    {
        "preset": "intent",
        "label": "German - double charge",
        "text": "Ich habe mein Konto zweimal belastet. Bitte um Rückerstattung.",
        "answer": {"intent": "get_refund"},
    },
    {
        "preset": "intent",
        "label": "French - double charge",
        "text": "La facture 4411 m'a ete facturee deux fois. Merci de rembourser.",
        "answer": {"intent": "get_refund"},
    },
    {
        "preset": "tone",
        "label": "Arabic - angry",
        "text": "للمرة الثالثة أبلغكم أن الخدمة لا تعمل! هذا غير مقبول إطلاقاً.",
        "answer": {"tone": "angry"},
    },
    {
        "preset": "tone",
        "label": "Arabic - calm",
        "text": "أين يمكنني رؤية قائمة الأسعار الخاصة بكم؟",
        "answer": {"tone": "calm"},
    },
]


def questions_for(preset):
    return json.loads(json.dumps(PRESETS[preset]["questions"]))


def validate(questions):
    """Return (ok, message). Rejects shapes the engine cannot answer."""
    if not isinstance(questions, dict) or not questions:
        return False, "Questions must be a non-empty JSON object."
    for key, q in questions.items():
        if not isinstance(q, dict):
            return False, f"Question '{key}' must be an object."
        kind = q.get("type")
        if kind not in ("choice", "noul", "score"):
            return False, f"Question '{key}' has unknown type {kind!r}. " \
                           "Use choice, noul or score."
        if not q.get("instructions"):
            return False, f"Question '{key}' needs an 'instructions' string."
        if kind == "choice":
            crit = q.get("criteria")
            if not isinstance(crit, dict) or len(crit) < 2:
                return False, f"Choice question '{key}' needs a 'criteria' " \
                               "object with at least 2 options."
            if len(crit) > 20:
                return False, f"Choice question '{key}' has {len(crit)} options. " \
                               "Keep it at 20 or fewer; accuracy falls off sharply."
        if kind == "score":
            crit = q.get("criteria")
            if not isinstance(crit, list) or len(crit) < 2:
                return False, f"Score question '{key}' needs a 'criteria' list " \
                               "with at least 2 levels."
    return True, "ok"
