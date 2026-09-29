"""Liquidity Incentive Program scoring and the frozen quote configuration (DESIGN §5, §7).

Same algorithm as the PT1-frozen `m6_rewards.configure` / `side_share` (tests assert equality), extended
to several own orders per side (a partially filled order plus a replenishment order).

Filed formula (LIP filed 2026-07-15, modified 2026-07-30): per side, walk bid levels from the best down,
accumulating size; Reference Price = first level where cumulative >= Target/5; stop once cumulative >=
Target; if never, the side has no qualifying bids and the snapshot is EXCLUDED. Weight of a bid =
DF^(ticks below the Reference) (1 at/above it) x size; a user's side score is its weighted size over
the side total. Snapshot score = YES share + NO share. All other resting size is treated as eligible.
"""
from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal as D

from . import spec as S

DEFAULT_RANGES = [{"start": "0", "end": "1", "step": "0.01"}]


def grid_ticks(ranges: list[dict], lo: D, hi: D) -> int:
    n = D(0)
    for r in ranges:
        s, e, st = D(r["start"]), D(r["end"]), D(r["step"])
        a, b = max(lo, s), min(hi, e)
        if b > a:
            n += (b - a) / st
    return int(n.to_integral_value())


def snap_down(p: D, ranges: list[dict]) -> D:
    for r in ranges:
        s, e, st = D(r["start"]), D(r["end"]), D(r["step"])
        if s <= p <= e:
            return s + ((p - s) / st).to_integral_value(rounding=ROUND_FLOOR) * st
    return p.quantize(D("0.01"), rounding=ROUND_FLOOR)


def levels(book: dict, side: str) -> list[tuple[D, D]]:
    """Bids of one side, best first: side 'yes' -> yes_dollars, 'no' -> no_dollars."""
    raw = book.get("yes_dollars" if side == "yes" else "no_dollars") or []
    return sorted(((D(p), D(q)) for p, q in raw), reverse=True)


def configure(book: dict, ranges: list[dict] | None) -> tuple[D, D, str]:
    """Target (YES bid, NO bid, mode) from the REAL book (PT1 configure; clamped to [0.01, 0.99])."""
    ranges = ranges or DEFAULT_RANGES
    yb, nb = levels(book, "yes"), levels(book, "no")
    by, bn = (yb[0][0] if yb else None), (nb[0][0] if nb else None)
    if by is not None and bn is not None and by + bn >= S.JOIN_IF_BID_SUM_GE:
        py, pn, mode = by, bn, "join_best"
    else:
        if by is not None and bn is not None:
            mid = (by + (1 - bn)) / 2
        elif by is not None:
            mid = min(by + D("0.05"), D("0.94"))
        elif bn is not None:
            mid = max(1 - bn - D("0.05"), D("0.06"))
        else:
            mid = D("0.50")
        py = snap_down(max(mid - S.IMPROVE_HALF_WIDTH, S.PRICE_MIN), ranges)
        pn = snap_down(max((1 - mid) - S.IMPROVE_HALF_WIDTH, S.PRICE_MIN), ranges)
        mode = "improve_to_10c"
    return min(max(py, S.PRICE_MIN), S.PRICE_MAX), min(max(pn, S.PRICE_MIN), S.PRICE_MAX), mode


def side_share(others: list[tuple[D, D]], mine: list[tuple[D, D]], T: D, d: D, ranges: list[dict] | None) -> D | None:
    """others: real bids [(price, size)]; mine: own bids [(price, size)]. Returns own normalised share of
    the side, or None if the side does not reach Target (snapshot excluded)."""
    ranges = ranges or DEFAULT_RANGES
    book: dict[D, D] = {}
    for p, s in others:
        book[p] = book.get(p, D(0)) + s
    own: dict[D, D] = {}
    for p, s in mine:
        if s > 0:
            book[p] = book.get(p, D(0)) + s
            own[p] = own.get(p, D(0)) + s
    cum, ref, visited = D(0), None, []
    for p in sorted(book, reverse=True):
        cum += book[p]
        visited.append(p)
        if ref is None and cum >= T / 5:
            ref = p
        if cum >= T:
            break
    if cum < T:
        return None
    w = lambda p: D(1) if p >= ref else d ** grid_ticks(ranges, p, ref)      # noqa: E731
    total = sum(book[p] * w(p) for p in visited)
    if total <= 0:
        return None
    return sum(own[p] * w(p) for p in visited if p in own) / total


def snapshot_score(book: dict, mine_yes, mine_no, T: D, d: D, ranges) -> D:
    """(YES share + NO share); 0 if the snapshot is excluded on either side."""
    sy = side_share(levels(book, "yes"), mine_yes, T, d, ranges)
    sn = side_share(levels(book, "no"), mine_no, T, d, ranges)
    if sy is None or sn is None:
        return D(0)
    return sy + sn
