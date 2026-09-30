"""Epistemic labels. Every number the system shows carries one of these.

OBSERVED   read directly from a source (a bid shown on an auction page)
INFERRED   derived deterministically from observed data (size bucket from 5x10)
ESTIMATED  a model or human judgement (expected resale value)
SIMULATED  a counterfactual (paper win at a paper max bid)
REALIZED   money that actually changed hands (a real sale)

ESTIMATED and SIMULATED results must never be presented as REALIZED.
"""

from __future__ import annotations

from enum import Enum


class Label(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    ESTIMATED = "ESTIMATED"
    SIMULATED = "SIMULATED"
    REALIZED = "REALIZED"
