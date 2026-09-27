"""The image classifier: SigLIP, 88M params, 224x224, labels ai / hum.

engine.py  owns the model, one forward pass per image
agent.py   composes the verdict from engine values, never invents one
presets.py accepted formats, labels, and the known caveats
"""
__all__ = ["agent", "engine", "presets"]
