"""Order book normalization and depth walking (Decimal only, never floats, never mids).

Kalshi order books expose BIDS ONLY, for YES and for NO. The executable ask for one side is
derived from the opposite side's bids:  yes_ask = 1 - no_bid,  no_ask = 1 - yes_bid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

ONE = Decimal(1)
ZERO = Decimal(0)


class OrderBookFormatError(ValueError):
    pass


@dataclass(frozen=True)
class Level:
    price: Decimal   # dollars, 0 < price < 1
    qty: Decimal     # contracts (fixed-point allowed)


@dataclass(frozen=True)
class OrderBook:
    ticker: str
    yes_bids: tuple[Level, ...]   # sorted best (highest) first
    no_bids: tuple[Level, ...]    # sorted best (highest) first
    source_format: str

    def asks(self, side: str) -> tuple[Level, ...]:
        """Executable ask ladder for buying `side` ('yes'|'no'), best (lowest) first."""
        opp = self.no_bids if side == "yes" else self.yes_bids if side == "no" else None
        if opp is None:
            raise ValueError(side)
        return tuple(Level(ONE - lv.price, lv.qty) for lv in opp)

    def best_bid(self, side: str) -> Level | None:
        b = self.yes_bids if side == "yes" else self.no_bids
        return b[0] if b else None

    def best_ask(self, side: str) -> Level | None:
        a = self.asks(side)
        return a[0] if a else None

    def is_crossed(self) -> bool:
        """True if yes_bid + no_bid > 1 (should never be displayed; indicates bad/stale data)."""
        yb, nb = self.best_bid("yes"), self.best_bid("no")
        return bool(yb and nb and yb.price + nb.price > ONE)


def _to_levels(raw: Iterable, scale: Decimal) -> tuple[Level, ...]:
    agg: dict[Decimal, Decimal] = {}
    for item in raw or ():
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            raise OrderBookFormatError(f"bad level {item!r}")
        price = Decimal(str(item[0])) * scale
        qty = Decimal(str(item[1]))
        if qty <= 0:
            continue
        if not (ZERO < price < ONE):
            raise OrderBookFormatError(f"price out of (0,1): {price}")
        agg[price] = agg.get(price, ZERO) + qty
    return tuple(Level(p, agg[p]) for p in sorted(agg, reverse=True))


def parse_orderbook(ticker: str, body: dict) -> OrderBook:
    """Accepts the fixed-point dollars format (`orderbook_fp.{yes,no}_dollars`) and the legacy
    format (`orderbook.{yes,no}` in cents, or `orderbook.{yes,no}_dollars`). Level ordering in the
    payload is not trusted; levels are re-sorted and duplicate prices aggregated."""
    if not isinstance(body, dict):
        raise OrderBookFormatError("body is not an object")
    if isinstance(body.get("orderbook_fp"), dict):
        ob = body["orderbook_fp"]
        return OrderBook(ticker, _to_levels(ob.get("yes_dollars"), ONE),
                         _to_levels(ob.get("no_dollars"), ONE), "orderbook_fp")
    if isinstance(body.get("orderbook"), dict):
        ob = body["orderbook"]
        if "yes_dollars" in ob or "no_dollars" in ob:
            return OrderBook(ticker, _to_levels(ob.get("yes_dollars"), ONE),
                             _to_levels(ob.get("no_dollars"), ONE), "orderbook_dollars")
        return OrderBook(ticker, _to_levels(ob.get("yes"), Decimal("0.01")),
                         _to_levels(ob.get("no"), Decimal("0.01")), "orderbook_cents")
    raise OrderBookFormatError("no orderbook/orderbook_fp key")


@dataclass(frozen=True)
class Fill:
    """Result of walking an ask ladder for a target quantity."""
    requested: Decimal
    filled: Decimal
    cost: Decimal                     # sum(price*qty), before fees
    fills: tuple[Level, ...] = field(default=())   # per-price-level fills

    @property
    def complete(self) -> bool:
        return self.filled >= self.requested

    @property
    def vwap(self) -> Decimal | None:
        return self.cost / self.filled if self.filled else None

    @property
    def worst_price(self) -> Decimal | None:
        return self.fills[-1].price if self.fills else None


def walk(ladder: tuple[Level, ...], qty: Decimal) -> Fill:
    remaining, cost, fills = qty, ZERO, []
    for lv in ladder:
        if remaining <= 0:
            break
        take = min(remaining, lv.qty)
        fills.append(Level(lv.price, take))
        cost += take * lv.price
        remaining -= take
    return Fill(qty, qty - remaining, cost, tuple(fills))


def displayed_depth(ladder: tuple[Level, ...]) -> Decimal:
    return sum((lv.qty for lv in ladder), ZERO)
