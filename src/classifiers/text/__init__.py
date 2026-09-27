"""The text classifier: laya-multilingual, 322M params, 100+ languages.

engine.py  owns the model, one forward pass
agent.py   composes a reply from engine values, never invents one
presets.py question sets and worked examples
"""
__all__ = ["agent", "engine", "presets"]
