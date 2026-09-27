"""Frozen research configuration.

These values are fixed BEFORE any data is inspected and must not be tuned to results
(DESIGN.md §4, "No parameter tuning"). Changing any value requires bumping CONFIG_VERSION
and noting the reason in the research log.
"""
from decimal import Decimal

CONFIG_VERSION = "2026-09-27.1"

PUBLIC_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Rate limiting for the public read endpoints (well under the basic-tier read limit).
MAX_REQUESTS_PER_SECOND = 8

# Timing gates (nanoseconds).
# Max spread between the earliest request-sent and latest response-received across all legs.
MAX_LEG_SKEW_NS = 2_000_000_000          # 2 s
# Max age of the oldest leg at evaluation time.
MAX_SNAPSHOT_AGE_NS = 5_000_000_000      # 5 s
# A candidate that passes all gates is re-fetched once after this delay to test persistence.
PERSISTENCE_REFETCH_DELAY_S = 1.0

# Fixed size grid (contracts) at which every candidate is scored. Not optimized.
SIZE_GRID = (Decimal(1), Decimal(10), Decimal(100))

# Fees — see fees.py. Conservative defaults; audited at the UltraCode checkpoint.
TAKER_COEF = Decimal("0.07")
MAKER_COEF = Decimal("0.0175")
DEFAULT_FEE_ROUNDING_UNIT = Decimal("0.01")      # whole cent (conservative)
ALT_FEE_ROUNDING_UNIT = Decimal("0.0001")        # centicent (reported as sensitivity)
