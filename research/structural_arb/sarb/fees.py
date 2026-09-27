"""Kalshi trading-fee mathematics, following official sources only (see sources/SOURCES.md).

Formula (Fee Schedule PDF, effective 2026-07-07, p.2):
    taker model fee = M x 0.07 x C x P x (1 - P)
    M = the multiplier in force at the snapshot time for the series/event, from the
    time-versioned fee ledger (sarb/fee_ledger.py). No maximum or historical substitution.

Rounding (docs.kalshi.com/getting_started/fee_rounding), for each fill k of ONE order:
    revenue_k    = -P_k * c_k                        (buyer)
    trade_fee_k  = ceil_6dp(model_fee_k)
    aligned_k    = floor_g(revenue_k - trade_fee_k)  (g = member balance precision)
    rounding_k   = (revenue_k - trade_fee_k) - aligned_k
    accumulator += rounding_k; rebate_k = g x min(floor(acc/g), floor((trade_fee_k+rounding_k)/g))
    net_fee_k    = trade_fee_k + rounding_k - rebate_k   (>= 0)
    g = $0.0001 for direct members, $0.01 for non-direct (FCM-cleared) members.

PROVEN BOUNDS (tests/test_fees.py checks them against the exact algorithm on randomized fill
splits). Take an order that consumes quantity c_L at each price level P_L, in n fills.
  (B1) sum_L model(P_L,c_L) <= sum_k trade_fee_k < sum_L model(P_L,c_L) + n x 1e-6
       (the model fee is linear in c, and ceil_6dp adds < 1e-6 per fill)
  (B2) On-grid case: if every fill's revenue is a multiple of g, then
       sum_k trade_fee_k <= total_net_fee < sum_k trade_fee_k + g.
       Proof: rounding_k = ceil_g(tf_k) - tf_k, and tf_k + rounding_k = ceil_g(tf_k), which is
       >= g whenever tf_k > 0, so the rebate cap never binds for a single increment. By
       induction the accumulator stays below g after every fill, and total net fee =
       sum tf_k + final accumulator.
  (B3) General case: sum tf_k <= total_net_fee < sum tf_k + n x g   (each rounding_k < g)
  The number of fills n is unknown: displayed levels aggregate resting orders. Fills are
  bounded by assuming each is at least `min_fill_unit` contracts. That is 1 when every
  consumed level shows an integer quantity (assumption A_INTEGER_RESTING_ORDERS). Otherwise
  it is 0.01, the documented minimum granularity.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from typing import Iterable, Sequence

from .orderbook import Level

TAKER_COEF = Decimal("0.07")                 # Fee Schedule PDF p.2
MAKER_COEF = Decimal("0.0175")               # Fee Schedule PDF p.2 (not used: all legs are taker)
FEE_QUANTUM = Decimal("0.000001")            # docs: trade fee rounded up to $0.000001
DIRECT_PRECISION = Decimal("0.0001")         # docs: direct member balance precision
NON_DIRECT_PRECISION = Decimal("0.01")       # docs: non-direct (FCM) balance precision
MIN_CONTRACT_UNIT = Decimal("0.01")          # docs: fixed-point minimum granularity

# Taker formula is identical for these types (API docs FeeType description + PDF). 'flat' is
# described by a "Specific Trading Fees Table" that is not in the PDF, so it is UNRESOLVED.
SUPPORTED_TAKER_TYPES = frozenset({"quadratic", "quadratic_with_maker_fees",
                                   "quadratic_with_combo_maker_fees"})

# NOTE: the PDF's non-standard multiplier table is NOT used. The multiplier in force comes only
# from the time-versioned fee ledger (sarb/fee_ledger.py). Substituting historical or maximum
# values was removed on 2026-09-27: it can overstate AND understate the actual fee.


class UnsupportedFee(ValueError):
    pass


def ceil_to(x: Decimal, q: Decimal) -> Decimal:
    return (x / q).to_integral_value(rounding=ROUND_CEILING) * q


def floor_to(x: Decimal, q: Decimal) -> Decimal:
    return (x / q).to_integral_value(rounding=ROUND_FLOOR) * q


def model_fee(price: Decimal, qty: Decimal, multiplier: Decimal) -> Decimal:
    """Exact (unrounded) taker model fee in dollars."""
    return multiplier * TAKER_COEF * qty * price * (1 - price)


@dataclass(frozen=True)
class OrderFee:
    net_fee: Decimal          # total fee charged for the order
    trade_fees: Decimal       # sum of ceil_6dp model fees
    rounding: Decimal         # sum of rounding fees
    rebates: Decimal          # sum of rebates
    principal: Decimal        # sum P*c
    accumulator_left: Decimal

    @property
    def cash_out(self) -> Decimal:
        return self.principal + self.net_fee


def order_fee_exact(fills: Sequence[Level], multiplier: Decimal, precision: Decimal) -> OrderFee:
    """Documented per-order algorithm, given an explicit fill sequence."""
    acc = tf_sum = rf_sum = rb_sum = principal = Decimal(0)
    for f in fills:
        revenue = -(f.price * f.qty)
        tf = ceil_to(model_fee(f.price, f.qty, multiplier), FEE_QUANTUM)
        aligned = floor_to(revenue - tf, precision)
        rf = (revenue - tf) - aligned
        acc += rf
        cap_units = ((tf + rf) / precision).to_integral_value(rounding=ROUND_FLOOR)
        acc_units = (acc / precision).to_integral_value(rounding=ROUND_FLOOR)
        rebate = precision * min(acc_units, cap_units)
        acc -= rebate
        tf_sum += tf; rf_sum += rf; rb_sum += rebate; principal += f.price * f.qty
    return OrderFee(tf_sum + rf_sum - rb_sum, tf_sum, rf_sum, rb_sum, principal, acc)


def _is_integer(x: Decimal) -> bool:
    return x == x.to_integral_value()


@dataclass(frozen=True)
class FeeBound:
    lower: Decimal            # net fee >= lower
    upper: Decimal            # net fee <  upper (strict)
    n_fills_max: int
    min_fill_unit: Decimal
    on_grid: bool
    principal: Decimal


def order_fee_bound(levels_taken: Sequence[Level], multiplier: Decimal, precision: Decimal,
                    min_fill_unit: Decimal | None = None) -> FeeBound:
    """Bound on one order's net fee when the split of each level into fills is unknown.
    levels_taken: (price, quantity consumed) per price level."""
    if min_fill_unit is None:
        min_fill_unit = Decimal(1) if all(_is_integer(l.qty) for l in levels_taken) else MIN_CONTRACT_UNIT
    model = sum((model_fee(l.price, l.qty, multiplier) for l in levels_taken), Decimal(0))
    n = sum(int((l.qty / min_fill_unit).to_integral_value(rounding=ROUND_CEILING)) for l in levels_taken)
    on_grid = all((l.price * min_fill_unit) % precision == 0 for l in levels_taken)
    tf_upper = model + n * FEE_QUANTUM
    upper = tf_upper + (precision if on_grid else n * precision)
    principal = sum((l.price * l.qty for l in levels_taken), Decimal(0))
    return FeeBound(model, upper, n, min_fill_unit, on_grid, principal)


@dataclass(frozen=True)
class ResolvedFee:
    fee_type: str
    multiplier: Decimal
    source: str               # provenance for the research log (see fee_ledger.py)


# ------------------------------------------------------------------ scenarios

@dataclass(frozen=True)
class FeeScenario:
    name: str
    precision: Decimal
    exact_single_fill_per_level: bool   # True: exact algorithm, one fill per level (estimate)


DIRECT_EXPECTED = FeeScenario("direct_expected", DIRECT_PRECISION, True)
DIRECT_BOUND = FeeScenario("direct_bound", DIRECT_PRECISION, False)
NONDIRECT_CONSERVATIVE = FeeScenario("nondirect_conservative", NON_DIRECT_PRECISION, False)
SCENARIOS = (DIRECT_EXPECTED, DIRECT_BOUND, NONDIRECT_CONSERVATIVE)
# The RULE_DEFINED_LOCK label requires edge > 0 under EVERY scenario (NONDIRECT_CONSERVATIVE is the binding one).


def leg_cash_out(levels_taken: Sequence[Level], series_ticker: str, fee: ResolvedFee,
                 scenario: FeeScenario) -> Decimal:
    """Principal plus fee. For bound scenarios this is a strict upper bound on the fee."""
    m = fee.multiplier      # the multiplier actually in force at the snapshot (fee_ledger)
    if scenario.exact_single_fill_per_level:
        return order_fee_exact(levels_taken, m, scenario.precision).cash_out
    b = order_fee_bound(levels_taken, m, scenario.precision)
    return b.principal + b.upper
