"""Truthful numeric labels for animated 3D comparison bars."""
from __future__ import annotations
import math

def comparison_label_value(target: float, animation_progress: float) -> float:
    """Show scenario value, not the animated bar's interim height."""
    value = float(target)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Comparison target must be a finite nonnegative value")
    if not math.isfinite(float(animation_progress)):
        raise ValueError("Animation progress must be finite")
    return value
