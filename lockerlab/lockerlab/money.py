"""Money helpers. All money is integer cents; never floats in storage.

Rounding is deliberately asymmetric: costs round *up* and proceeds round *down*,
so accumulated rounding can only make results look worse, never better.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation

_MONEY_RE = re.compile(r"^\s*\$?\s*(-?[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*$")


def parse_dollars(text: str) -> int:
    """'$1,234.5' -> 123450 cents. Raises ValueError on anything ambiguous."""
    m = _MONEY_RE.match(text)
    if not m:
        raise ValueError(f"not a dollar amount: {text!r}")
    try:
        d = Decimal(m.group(1).replace(",", ""))
    except InvalidOperation as e:  # pragma: no cover - regex already guards
        raise ValueError(f"not a dollar amount: {text!r}") from e
    return int(d * 100)


def cost_cents(x: float) -> int:
    """Round a computed cost up to whole cents."""
    return math.ceil(round(x, 6))


def proceeds_cents(x: float) -> int:
    """Round computed proceeds down to whole cents."""
    return math.floor(round(x, 6))


def fmt(cents: int | None) -> str:
    if cents is None:
        return "n/a"
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"
