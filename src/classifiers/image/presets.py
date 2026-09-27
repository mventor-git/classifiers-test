"""Image presets: accepted formats, label wording, and the known caveats.

The counterpart of text/presets.py. Nothing here decides anything about an
image; it is the vocabulary the image agent and the page share.
"""
from classifiers import config

# What the attach button accepts. Gradio filters on this list, and the engine
# re-checks the file rather than trusting the filter.
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"]

# The model's own id2label is {0: "ai", 1: "hum"}. config.IMAGE_LABELS is the
# authority; this is only how we say it to a person.
LABEL_TEXT = {
    "ai": "AI-generated",
    "hum": "Real photograph",
}

# Below this, the agent says the model is unsure instead of picking a side.
UNSURE_BELOW = 0.60

# The model card for Ateeqq/ai-vs-human-image-detector reports 99.2% test
# accuracy and then, in the same breath, says "Some users reported overfitting
# issues". Treat the number as unproven. This is surfaced in the UI on purpose:
# a classifier that answers 99.5% on a synthetic gradient has learned something
# about gradients, not about AI images.
CAVEAT = (
    "This model is reported as overfit by its own author and returns very high "
    "confidences. It is a hint, not proof, and it has never been evaluated on "
    "your data."
)

HOW_IT_WORNS = (
    "A fine-tuned **SigLIP** base model. It resizes your image to 224×224, runs "
    "one forward pass, and returns two logits - `ai` and `hum` - which are "
    "softmaxed into probabilities. 88M parameters, about 70 ms per image on a "
    "GTX 1060."
)

MODEL_PAGE = config.IMAGE_MODEL_PAGE

# ---------------------------------------------------------------------------
# Example image URLs, all verified to return HTTP 200 with an image/* type on
# 2026-09-27. These are Unsplash CDN links, which serve the photograph itself.
#
# The repository stores these URLs and never the photographs. Nothing is
# downloaded at build time and no third-party image is committed, so there is no
# attribution or licensing question in the git history. The bytes are fetched on
# the user's own machine, at the moment they press the button, through
# classifiers/image/remote.py - which is the guard that makes that acceptable.
#
# Unsplash blocks automated access to its HTML pages (a plain fetch of a photo
# page returns HTTP 401), which is why the direct CDN host is used and why this
# project does not scrape unsplash.com. For your own specific photos, use the
# official API with an access key, or just paste any https image URL.
# ---------------------------------------------------------------------------
EXAMPLE_URLS = [
    "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800&q=80",
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
    "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80",
]

