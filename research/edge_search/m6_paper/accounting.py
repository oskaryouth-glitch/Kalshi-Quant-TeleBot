"""Fees, positions, netting, settlement and liquidation marks (DESIGN §6, §8).

Fee schedule (copied from structural_arb/PT1, not imported): fee = M * coef * C * P * (1 - P), rounded
up to 6 dp, then up to the balance precision g ($0.0001 direct member = primary; $0.01 non-direct =
reported). Maker fees are charged only in `quadratic_with_maker_fees` series. We never take, so the
taker coefficient is used only for liquidation marks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal as D

from . import spec as S

ZERO, ONE = D(0), D(1)


def ceil_to(x: D, q: D) -> D:
    return (x / q).to_integral_value(rounding=ROUND_CEILING) * q


def fee(price: D, count: D, mult: D, coef: D, g: D = S.DIRECT_G) -> D:
    if mult == 0 or count == 0:
        return ZERO
    return ceil_to(ceil_to(mult * coef * count * price * (ONE - price), S.FEE_6DP), g)


def maker_fee(fee_type: str, mult: D, price: D, count: D, g: D = S.DIRECT_G) -> D:
    return fee(price, count, mult, S.MAKER_COEF, g) if fee_type == "quadratic_with_maker_fees" else ZERO


@dataclass
class Fill:
    t_ns: int
    side: str            # 'yes' (our YES bid filled -> +YES) or 'no' (our NO bid filled -> +NO)
    price: D
    count: D
    fee_direct: D
    fee_nondirect: D
    episode: str
    kind: str            # 'queue' or 'through'


@dataclass
class Position:
    """One account's inventory in one market. YES count a, NO count b; pairs net to $1 as they form."""
    a: D = ZERO
    b: D = ZERO
    cost_a: D = ZERO     # cost basis of the a YES contracts still held
    cost_b: D = ZERO
    pairs_redeemed: D = ZERO
    fills: list = field(default_factory=list)

    @property
    def q(self) -> D:
        return self.a - self.b

    @property
    def inventory_cost(self) -> D:
        return self.cost_a + self.cost_b

    def apply(self, f: Fill) -> None:
        self.fills.append(f)
        if f.side == "yes":
            self.a += f.count
            self.cost_a += f.price * f.count
        else:
            self.b += f.count
            self.cost_b += f.price * f.count
        p = min(self.a, self.b)
        if p > 0:                                      # netting: a YES+NO pair is worth exactly $1
            self.cost_a -= self.cost_a * p / self.a
            self.cost_b -= self.cost_b * p / self.b
            self.a -= p
            self.b -= p
            self.pairs_redeemed += p


def contract_values(settled_value: D | None, yes_bid: D | None, no_bid: D | None, q: D, mult: D) -> tuple[D, D, str]:
    """Per-contract values (YES, NO) used to value every fill, consistent with $1 netting.

    Settled (value v): YES = v, NO = 1 - v.
    Unsettled at the cutoff, net YES inventory: YES = m_yes = best YES bid - taker fee per contract
    (0 if no bid), NO = 1 - m_yes; net NO inventory: NO = m_no, YES = 1 - m_no. The market-account total
    is then pairs*$1 + net*liquidation mark, exactly. Flat (q = 0): YES = best-bid mid if both bids
    exist, else 0.5 (any split gives the same total)."""
    if settled_value is not None:
        return settled_value, ONE - settled_value, "settled"

    def mark(bid):
        if bid is None or bid <= 0:
            return ZERO
        return max(ZERO, bid - fee(bid, ONE, mult, S.TAKER_COEF))
    if q > 0:
        m = mark(yes_bid)
        return m, ONE - m, "liquidation"
    if q < 0:
        m = mark(no_bid)
        return ONE - m, m, "liquidation"
    if yes_bid is not None and no_bid is not None:
        y = (yes_bid + (ONE - no_bid)) / 2
        return y, ONE - y, "flat"
    return D("0.5"), D("0.5"), "flat"


def fill_pnl(f: Fill, v_yes: D, v_no: D, direct: bool = True) -> D:
    v = v_yes if f.side == "yes" else v_no
    return (v - f.price) * f.count - (f.fee_direct if direct else f.fee_nondirect)
