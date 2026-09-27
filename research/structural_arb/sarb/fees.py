"""Kalshi trading-fee model.

STATUS: provisional — the rounding unit and scope are to be audited at the UltraCode checkpoint
(the official fee schedule could not be fetched from this environment).

Taker fee per fill:  roundup_to_unit( M * 0.07 * C * P * (1 - P) )
  * M = series fee_multiplier (from GET /series), default 1
  * fee_type 'quadratic' / 'quadratic_with_maker_fees' use this taker formula
  * any other fee_type (e.g. 'flat') is UNSUPPORTED -> raises, so the candidate is rejected
    rather than scored with a guessed fee.

Conservative defaults: round up to a whole cent, and apply rounding to EACH price-level fill
separately (more rounding events -> higher total fee). This biases against finding arbitrage.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from typing import Iterable

from . import config
from .orderbook import Level

SUPPORTED_TAKER_TYPES = {"quadratic", "quadratic_with_maker_fees"}


class UnsupportedFee(ValueError):
    pass


def round_up(x: Decimal, unit: Decimal) -> Decimal:
    if x <= 0:
        return Decimal(0)
    return (x / unit).to_integral_value(rounding=ROUND_CEILING) * unit


@dataclass(frozen=True)
class FeeSchedule:
    fee_type: str = "quadratic"
    multiplier: Decimal = Decimal(1)
    taker_coef: Decimal = config.TAKER_COEF
    rounding_unit: Decimal = config.DEFAULT_FEE_ROUNDING_UNIT
    per_fill_rounding: bool = True   # True: round each level fill; False: round once per leg

    @classmethod
    def from_series(cls, series_body: dict, **overrides) -> "FeeSchedule":
        s = series_body.get("series", series_body) if isinstance(series_body, dict) else {}
        fee_type = s.get("fee_type")
        mult = s.get("fee_multiplier")
        if fee_type is None or mult is None:
            raise UnsupportedFee(f"series missing fee_type/fee_multiplier: {sorted(s)[:20]}")
        return cls(fee_type=str(fee_type), multiplier=Decimal(str(mult)), **overrides)

    def raw_taker_fee(self, price: Decimal, qty: Decimal) -> Decimal:
        if self.fee_type not in SUPPORTED_TAKER_TYPES:
            raise UnsupportedFee(f"fee_type {self.fee_type!r} not modelled")
        return self.multiplier * self.taker_coef * qty * price * (1 - price)

    def taker_fee(self, fills: Iterable[Level]) -> Decimal:
        fills = list(fills)
        if self.per_fill_rounding:
            return sum((round_up(self.raw_taker_fee(f.price, f.qty), self.rounding_unit) for f in fills),
                       Decimal(0))
        return round_up(sum((self.raw_taker_fee(f.price, f.qty) for f in fills), Decimal(0)),
                        self.rounding_unit)

    def with_rounding(self, unit: Decimal, per_fill: bool) -> "FeeSchedule":
        return FeeSchedule(self.fee_type, self.multiplier, self.taker_coef, unit, per_fill)
