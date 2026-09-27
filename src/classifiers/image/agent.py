"""Image agent - the verdict composer.

The counterpart of text/agent.py, and bound by the same rule from contract
section 5: this layer may render what the engine returned, and may not invent a
verdict, a probability, or an answer for an image it could not read.

Every number below is read out of the engine's result dict. There is no
arithmetic, no thresholding dressed up as a decision, and no fallback wording
that could imply a verdict we do not have.
"""
from classifiers.image import presets


def compose_one(result):
    """One image -> one markdown line. Says so plainly when there is no verdict."""
    if not result.get("ok"):
        return f"`{result.get('name', '?')}` -> **not classified**, {result.get('error', 'unknown error')}"

    label = result.get("label")
    confidence = result.get("confidence")
    probs = result.get("probabilities") or {}
    wording = presets.LABEL_TEXT.get(label, str(label))

    spread = " · ".join(f"{k} {v:.1%}" for k, v in probs.items())
    line = (f"`{result.get('name', '?')}` -> **{wording}** at "
            f"**{confidence:.1%}**  \n<small>{spread} · {result.get('detail', '')}</small>")

    if isinstance(confidence, (int, float)) and confidence < presets.UNSURE_BELOW:
        line += ("\n<small>Below the 60% line this agent treats as uncertain, "
                 "so treat it as a coin flip.</small>")
    return line


def compose(results):
    """A batch of results -> (markdown, meta_line, table_rows)."""
    if not results:
        return ('<div class="placeholder">Attach an image, then press '
                '<b>Classify</b>.</div>'), "", []

    good = [r for r in results if r.get("ok")]
    bad = [r for r in results if not r.get("ok")]

    if not good:
        lines = ["**None of those could be read as an image.**", ""]
        lines += [f"- `{r.get('name', '?')}` — {r.get('error', 'unknown error')}"
                  for r in bad]
        return "\n".join(lines), f"0 of {len(results)} readable", []

    lines = [compose_one(r) for r in good]
    lines += [compose_one(r) for r in bad]
    lines += ["", f"<small>{presets.CAVEAT}</small>"]

    rows = []
    for r in good:
        rows.append([r.get("name", "?"), r.get("size", "?"),
                     r.get("label", "?"), f"{r.get('confidence', 0):.1%}"])

    counts = {}
    for r in good:
        counts[r.get("label")] = counts.get(r.get("label"), 0) + 1
    meta = (f"{len(good)} of {len(results)} readable · "
            f"{counts.get('ai', 0)} ai · {counts.get('hum', 0)} hum")
    return "\n\n".join(lines), meta, rows


def how_it_works():
    return presets.HOW_IT_WORNS


def caveat():
    return presets.CAVEAT
