"""Frozen research configuration.

These values are fixed BEFORE any data is inspected and must not be tuned to results
(DESIGN.md §4, "No parameter tuning"). Changing any value requires bumping CONFIG_VERSION
and noting the reason in the research log.
"""
from decimal import Decimal

CONFIG_VERSION = "2026-09-27.2-validation"

PUBLIC_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Rate limiting for the public read endpoints (well under the basic-tier read limit).
MAX_REQUESTS_PER_SECOND = 8
MAX_REQUEST_BURST = 16          # lets a candidate's legs be re-fetched back-to-back (low skew)

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

# Collector protocol (frozen before the long collection; see DESIGN.md §E.2 / COLLECTOR.md)
CYCLE_TARGET_S = 60                      # screening cycle cadence
MAX_PHASE2_CANDIDATES_PER_CYCLE = 40     # budget cap; skipped candidates are counted, not dropped silently
AUDIT_FAMILIES_PER_CYCLE = 2             # random families fetched from books regardless of the summary screen
AUDIT_MAX_MARKETS_PER_FAMILY = 30
SERIES_REFRESH_S = 6 * 3600
TERMS_REFRESH_S = 3600
FEE_CHANGES_REFRESH_S = 300
EVENTS_PAGE_MIN_INTERVAL_S = 0.25        # summary pages paced <= 4/s (run1 saw 429s only on /events pages)
STATSCREEN_REWRITE_S = 1800              # a given summary-only statistical hit is re-logged at most every 30 min
