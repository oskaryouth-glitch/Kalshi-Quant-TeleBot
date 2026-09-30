"""Unit size parsing and size buckets (INFERRED from observed dimensions)."""

from __future__ import annotations

import re

DEFAULT_HEIGHT_FT = 8.0

# Buckets by floor area. Boundaries sit between standard sizes so odd sizes
# (5x15 = 75 sq ft, 7.5x10) land in a documented place; raw dims are always kept.
SIZE_BUCKETS = (
    ("5x5", 30.0),
    ("5x10", 60.0),
    ("10x10", 110.0),
    ("10x15", 160.0),
    ("10x20+", float("inf")),
)

_DIM_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(?:'|ft|feet)?\s*(?:[xX×*]|by)\s*(\d+(?:\.\d+)?)\s*(?:'|ft|feet)?"
    r"(?:\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:'|ft|feet)?)?\s*$"
)


def parse_size(text: str) -> tuple[float, float, float | None]:
    """'10x10' / "5' x 10'" / '10 X 15 x 8' -> (width, length, height|None)."""
    m = _DIM_RE.match(text)
    if not m:
        raise ValueError(f"unrecognised unit size: {text!r}")
    w, l = float(m.group(1)), float(m.group(2))
    h = float(m.group(3)) if m.group(3) else None
    if w <= 0 or l <= 0 or (h is not None and h <= 0):
        raise ValueError(f"non-positive unit dimension: {text!r}")
    return (min(w, l), max(w, l), h)


def size_bucket(width_ft: float, length_ft: float) -> str:
    area = width_ft * length_ft
    for name, upper in SIZE_BUCKETS:
        if area <= upper:
            return name
    raise AssertionError("unreachable")


def unit_volume_cuft(width_ft: float, length_ft: float, height_ft: float | None) -> float:
    return width_ft * length_ft * (height_ft or DEFAULT_HEIGHT_FT)
