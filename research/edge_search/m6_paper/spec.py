"""M6 paper experiment: every frozen parameter in one place (DESIGN.md v2).

Changing any value here after collection starts is a recorded deviation (PREREG_M6_PAPER.md).
"""
from __future__ import annotations

from decimal import Decimal as D

SPEC_VERSION = "m6-paper-v3"

# ---------------------------------------------------------------- data sources (public GETs only)
API = "https://api.elections.kalshi.com/trade-api/v2"
BUCKET_URL = "https://kalshi-public-docs.s3.amazonaws.com/"
MAX_REQUESTS_PER_S = 2.0              # reviewer decision 2026-09-29 (was 3.0)
BOOKS_PER_CALL = 100            # GET /markets/orderbooks?tickers=... (API maximum)
MARKETS_PER_CALL = 100          # GET /markets?tickers=...

# ---------------------------------------------------------------- cadences (seconds)
EPOCH_HOURS_UTC = (0, 6, 12, 18)            # Arm P selection epochs
U_EPOCH_HOUR_UTC = 0                         # Arm U draws (daily)
BOOK_POLL_MEAN_S = 10.0                      # Poisson (exponential inter-arrival), independent of book state
TRADES_POLL_S = 5.0
TRADES_OVERLAP_S = 30
PROGRAMS_POLL_S = 600
MARKETS_POLL_S = 300
FEESTATE_POLL_S = 6 * 3600
COMPLETENESS_S = 600
COMPLETENESS_GAP = D("0.01")                 # > 1% volume unexplained by recorded trades -> backfill + flag
RULES_WATCH_S = 3600
FEES_NEW_PER_LOOP = 2                        # newly tracked markets' event/series fee objects fetched per loop pass
LOOP_STALL_GAP_S = 30                        # a main-loop pass longer than this is recorded as a collection gap
POST_SETTLEMENT_POLL_S = 6 * 3600            # market state + book for ever-tracked markets after they stop quoting

# ---------------------------------------------------------------- selection (DESIGN §4)
MIN_REMAINING_S = 24 * 3600
PAYOUT_TARGET = D("1.50")                    # x15: projected remaining-period payout >= $1.50
PAYOUT_FLOOR = D("1.00")
MAX_X = 20000
TOP_TRACK = 100
U_PER_STRATUM = 10
U_SEED_BASE = 20261001
U_MAX_CSTAR = D("200")
U_START_WINDOW_S = 24 * 3600                 # Arm U: program started within the previous 24 h
ACCOUNTS = {"P30": D("30"), "P100": D("100"), "P200": D("200")}
UNKNOWN_FEE_STATE = ("quadratic_with_maker_fees", D("1"))   # conservative

# ---------------------------------------------------------------- quoting / fills (DESIGN §5-6)
LATENCY_NS = 1_000_000_000
PRICE_MIN, PRICE_MAX = D("0.01"), D("0.99")
JOIN_IF_BID_SUM_GE = D("0.90")
IMPROVE_HALF_WIDTH = D("0.05")
VARIANTS = ("V_T", "V_P", "V_C")

# ---------------------------------------------------------------- fees (DESIGN §6)
TAKER_COEF, MAKER_COEF = D("0.07"), D("0.0175")
FEE_6DP = D("0.000001")
DIRECT_G, NONDIRECT_G = D("0.0001"), D("0.01")      # direct member (primary) / non-direct (reported)

# ---------------------------------------------------------------- rewards (DESIGN §7)
GAP_S = 60                                   # a poll covers at most 60 s; longer silences are gaps (earn 0)
Z_CONSERVATIVE = D("1.645")                  # conservative payout: P - 1.645*SE >= $1.00
BATCH_S = 3600                               # SE from hourly batch means

# ---------------------------------------------------------------- stopping and decision (DESIGN §10 v2)
CHECKPOINT_DAY = 35
MAX_DAY = 60
MIN_EPISODES = 20
SETTLEMENT_CUTOFF_DAYS = 30
BOOT_N = 10_000
BOOT_SEED = 20261001
INVALID_DOWNTIME_S = 24 * 3600
INVALID_TRADE_FEED_LOSS_S = 6 * 3600
CAPITAL_COST_APR = D("0.04")                 # reported sensitivity only
