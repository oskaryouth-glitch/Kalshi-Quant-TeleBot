"""Paper orders and the frozen queue/fill model (DESIGN §6).

Our orders are NOT in the real book. Each order records `q_real`, the real contracts ahead of it at its
price. Own orders at the same price that were placed earlier are also ahead of it (time priority).

Trades (from the public feed, exchange time):
  * `taker_side = no`  at yes_price y consumes YES bids at y;
  * `taker_side = yes` at no_price n  consumes NO bids at n.
At our level: the volume first passes the contracts ahead of us (real ones and our own earlier orders),
then fills us: fill = min(size, count - ahead). Real contracts consumed before reaching an order =
count - (own fills ahead of it); q_real decreases by that.
Trade-through: a print strictly worse than our price on our side means every bid at our price was
exhausted first, so our orders fill in priority order (better price, then earlier) up to the print's count.

Between snapshots, a size decrease Delta at our price that trades do not explain,
Delta = max(0, L_prev - traded_at_price - L_now), reduces q_real by: V_T 0 (fewest fills);
V_P Delta*q_real/L_prev (proportional; L_prev is the real level, which never contains our order);
V_C Delta (all cancellations ahead of us; most fills). If the level is absent from the new snapshot,
q_real = 0 in every variant (we are at the front).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D

ZERO = D(0)


@dataclass
class Order:
    oid: int
    side: str          # 'yes' = our YES bid; 'no' = our NO bid
    price: D
    size: D            # remaining
    q_real: D          # real contracts ahead at our price
    placed_ns: int     # decision time (snapshot receive time)
    t_eff_ns: int      # live from (placed + latency)
    episode: str


def consumed_side(trade: dict) -> tuple[str, D, D]:
    """(bid side consumed, price on that side, count) for a public trade record."""
    count = D(trade["count_fp"])
    if trade["taker_side"] == "no":
        return "yes", D(trade["yes_price_dollars"]), count
    return "no", D(trade["no_price_dollars"]), count


def match_trade(orders: list[Order], trade: dict, t_ns: int) -> list[tuple[Order, D, str]]:
    """Apply one trade to the live orders of ONE market. Returns [(order, filled, kind)] and mutates orders.
    Orders not yet live at t_ns are untouched."""
    side, price, count = consumed_side(trade)
    live = [o for o in orders if o.side == side and o.t_eff_ns <= t_ns and o.size > 0]
    out = []
    # trade-through: every live order priced strictly better than the print (higher bid) fills first
    through = sorted((o for o in live if o.price > price), key=lambda o: (-o.price, o.placed_ns, o.oid))
    left = count
    for o in through:
        if left <= 0:
            break
        f = min(o.size, left)
        o.size -= f
        o.q_real = ZERO
        left -= f
        out.append((o, f, "through"))
    # at our level: time priority among own orders at this price
    at = sorted((o for o in live if o.price == price), key=lambda o: (o.placed_ns, o.oid))
    own_filled_ahead = ZERO
    own_size_ahead = ZERO          # remaining size (before this trade) of own earlier orders at this price
    for o in at:
        size_before = o.size
        ahead = o.q_real + own_size_ahead
        f = min(o.size, max(ZERO, count - ahead)) if count > ahead else ZERO
        if f > 0:
            o.size -= f
            out.append((o, f, "queue"))
        o.q_real = max(ZERO, o.q_real - max(ZERO, count - own_filled_ahead))
        own_filled_ahead += f
        own_size_ahead += size_before
    return out


def queue_update(orders: list[Order], side_levels_prev: dict, side_levels_now: dict, traded_at: dict,
                 variant: str) -> None:
    """Apply the cancellation credit between two snapshots. side_levels_*: {side: {price: size}} of the REAL
    book; traded_at: {(side, price): contracts traded between the snapshots}."""
    for o in orders:
        if o.size <= 0:
            continue
        now = side_levels_now.get(o.side, {})
        if o.price not in now:                      # level vanished: we are at the front
            o.q_real = ZERO
            continue
        prev = side_levels_prev.get(o.side, {}).get(o.price)
        if prev is None or variant == "V_T":
            continue
        delta = max(ZERO, prev - traded_at.get((o.side, o.price), ZERO) - now[o.price])
        if delta <= 0:
            continue
        if variant == "V_P":
            o.q_real = max(ZERO, o.q_real - (delta * o.q_real / prev if prev > 0 else ZERO))
        elif variant == "V_C":
            o.q_real = max(ZERO, o.q_real - delta)
        else:
            raise ValueError(variant)
