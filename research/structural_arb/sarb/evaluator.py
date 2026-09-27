"""Price a structural candidate against executable books and apply every gate.

Pure function of its inputs (no I/O), so any snapshot can be re-evaluated offline.

Label semantics (DESIGN.md §C):
  ARBITRAGE  = GUARANTEED lock (checker L >= 1 in every determinate state, incl. ALL_NO where
               applicable) AND verified contract terms (or MECNET for categorical R1) AND every
               gate passes AND edge > 0 under ALL fee scenarios (the binding one is non-direct
               cent rounding with worst-case fill fragmentation) AND persistence confirmed on
               an independent re-fetch.
               Residual risks that NO Kalshi candidate can remove are always listed:
               discretionary settlement (6.3(c)/7.1), contract modification (7.2), trade
               cancellation (5.11), and non-atomic multi-leg execution.
  GUARANTEED_STRUCTURAL_NOT_EXECUTABLE = lock holds but some execution gate fails.
  CANDIDATE_TERMS_UNVERIFIED = lock holds under the conservative model, but the series terms
               are not in the verified registry (sarb/terms.py).
  STATISTICAL = displayed prices violate the naive relationship, but the checker finds no lock
               (coverage gap, ALL_NO state, semantic uncertainty, ...).
  REJECTED   = data / timing / metadata failure; the prices cannot be trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Mapping, Sequence

from . import config, fees as FEES
from .orderbook import Fill, Level, OrderBook, walk
from .relationships import Structural
from .research_log import CandidateRecord, LegRecord

RESIDUAL_RISKS = (
    "RULEBOOK_6.3c_DISCRETIONARY_SETTLEMENT(last traded / fair price; result='scalar')",
    "RULEBOOK_7.1_MARKET_OUTCOME_REVIEW",
    "RULEBOOK_7.2_CONTRACT_MODIFICATION(source/underlying/expiration)",
    "RULEBOOK_5.11_TRADE_CANCELLATION_OR_ADJUSTMENT",
    "NON_ATOMIC_MULTI_LEG_EXECUTION(no multi-leg orders; displayed depth may vanish)",
    "REST_BOOKS_NOT_SIMULTANEOUS(no server timestamps/sequence numbers without auth)",
)
RULE_5_11_NO_CANCEL_RANGE = Decimal("0.20")     # Rulebook 5.11(c)(ii)
MAX_METADATA_AGE_NS = 120_000_000_000           # market status/close_time freshness
MAX_SIZE_SCAN = 5000


@dataclass(frozen=True)
class BookObs:
    book: OrderBook | None
    status_code: int
    sent_mono_ns: int
    recv_mono_ns: int
    sent_utc_ns: int
    recv_utc_ns: int
    x_cache: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class MarketMeta:
    ticker: str
    series_ticker: str
    event_ticker: str
    status: str
    close_time_utc_ns: int | None
    last_price: Decimal | None
    latest_expiration_utc_ns: int | None
    fetched_mono_ns: int


def _D(x: Fraction) -> Decimal:
    return Decimal(x.numerator) / Decimal(x.denominator)


def _levels(fill: Fill) -> tuple[Level, ...]:
    return fill.fills


def price_portfolio(struct: Structural, books: Mapping[str, BookObs], fees: Mapping[str, FEES.ResolvedFee],
                    meta: Mapping[str, MarketMeta], size: Decimal) -> dict:
    """Edges under every fee scenario at a given size. Returns {} if any leg lacks depth."""
    legs, fills = [], {}
    for p in struct.positions:
        f = walk(books[p.ticker].book.asks(p.side), size)
        if not f.complete:
            return {}
        fills[p.ticker] = f
    payoff = _D(struct.locked) * size
    out = {"size": size, "gross_cost": sum((f.cost for f in fills.values()), Decimal(0)), "edges": {}}
    for sc in FEES.SCENARIOS:
        cash = Decimal(0)
        for p in struct.positions:
            cash += FEES.leg_cash_out(_levels(fills[p.ticker]), meta[p.ticker].series_ticker, fees[p.ticker], sc)
        out["edges"][sc.name] = payoff - cash
    out["fills"] = fills
    return out


def evaluate(struct: Structural, books: Mapping[str, BookObs], meta: Mapping[str, MarketMeta],
             fees_or_err: Mapping[str, object], exchange_trading_active: bool, now_mono_ns: int,
             now_utc_ns: int, persistence_confirmed: bool | None, snapshot_id: str | None = None,
             size_grid: Sequence[Decimal] = config.SIZE_GRID) -> tuple[str, CandidateRecord | None]:
    """Returns (outcome, record). outcome:
       CONSISTENT -- top-of-book prices do not violate the NOMINAL relationship (counted, not logged)
       NO_ASK     -- some leg has no displayed ask (counted, not logged)
       LOGGED     -- a displayed inconsistency; the record carries the full evaluation"""
    tick = [p.ticker for p in struct.positions]
    reasons: list[str] = []
    # ---------- book integrity (needed before any price is used)
    for t in tick:
        b = books.get(t)
        if b is None or b.book is None or b.status_code != 200 or b.error:
            reasons.append(f"BOOK_UNAVAILABLE:{t}")
        elif b.x_cache and "hit" in b.x_cache.lower():
            reasons.append(f"CDN_CACHE_HIT:{t}")
        elif b.book.is_crossed():
            reasons.append(f"BOOK_CROSSED_OR_LOCKED:{t}")
    if reasons:
        return "LOGGED", _rejected(struct, reasons, snapshot_id)
    best = {p.ticker: books[p.ticker].book.best_ask(p.side) for p in struct.positions}
    if any(v is None for v in best.values()):
        return "NO_ASK", None
    # Screen against max(nominal, locked): overlapping sets can lock MORE than the template's
    # nominal payoff, and such a portfolio must not be skipped.
    raw_nominal = _D(max(struct.nominal_locked, struct.locked)) - sum((l.price for l in best.values()), Decimal(0))
    if raw_nominal <= 0:
        return "CONSISTENT", None
    raw_locked = _D(struct.locked) - sum((l.price for l in best.values()), Decimal(0))

    # ---------- metadata / exchange / timing gates
    gates: dict[str, bool] = {}
    gates["exchange_trading_active"] = bool(exchange_trading_active)
    for t in tick:
        m = meta.get(t)
        ok = (m is not None and m.status == "active" and m.close_time_utc_ns is not None
              and m.close_time_utc_ns > now_utc_ns and now_mono_ns - m.fetched_mono_ns <= MAX_METADATA_AGE_NS)
        gates[f"market_active_fresh:{t}"] = ok
    sent = [books[t].sent_mono_ns for t in tick]
    recv = [books[t].recv_mono_ns for t in tick]
    skew = max(recv) - min(sent)
    age = now_mono_ns - min(recv)
    gates["skew_ok"] = skew <= config.MAX_LEG_SKEW_NS
    gates["age_ok"] = 0 <= age <= config.MAX_SNAPSHOT_AGE_NS
    # ---------- structural gates
    gates["locked_guaranteed"] = struct.relationship_class == "GUARANTEED" and struct.locked >= 1
    gates["no_checker_bug"] = not any(n.startswith("BUG") for n in struct.notes)
    # ---------- fees
    fee_ok = all(isinstance(fees_or_err.get(t), FEES.ResolvedFee) for t in tick)
    gates["fees_resolved"] = fee_ok
    fees = {t: fees_or_err[t] for t in tick} if fee_ok else {}

    # ---------- depth / edges / sizes
    grid_results, max_pos_size, n_pos_sizes = {}, None, 0
    depth = {p.ticker: sum((l.qty for l in books[p.ticker].book.asks(p.side)), Decimal(0)) for p in struct.positions}
    fractional_levels = {p.ticker: any(l.qty != l.qty.to_integral_value() for l in books[p.ticker].book.asks(p.side))
                         for p in struct.positions}
    if fee_ok:
        for c in size_grid:
            r = price_portfolio(struct, books, fees, meta, c)
            grid_results[str(c)] = ({k: str(v) for k, v in r["edges"].items()} if r else "INSUFFICIENT_DEPTH")
        max_c = int(min(min(depth.values()), MAX_SIZE_SCAN))
        for c in range(1, max_c + 1):
            r = price_portfolio(struct, books, fees, meta, Decimal(c))
            if r and all(v > 0 for v in r["edges"].values()):
                max_pos_size, n_pos_sizes = c, n_pos_sizes + 1
    gates["depth_ge_1"] = min(depth.values()) >= 1
    gates["edge_positive_all_scenarios_some_size"] = max_pos_size is not None
    # ---------- Rulebook 5.11 cancellation-range exposure (fair-value proxy = last traded price)
    rng_detail = {}
    for p in struct.positions:
        m = meta.get(p.ticker)
        lp = m.last_price if m else None
        ask = best[p.ticker].price
        if lp is None or lp <= 0:
            rng_detail[p.ticker] = "NO_LAST_PRICE"
            continue
        fair_side = lp if p.side == "yes" else 1 - lp
        rng_detail[p.ticker] = str(abs(ask - fair_side))
    gates["rule_5_11_within_no_cancel_range"] = all(v not in ("NO_LAST_PRICE",) and Decimal(v) <= RULE_5_11_NO_CANCEL_RANGE
                                                    for v in rng_detail.values())
    gates["persistence_confirmed"] = bool(persistence_confirmed)

    # ---------- status
    failing = [k for k, v in gates.items() if not v]
    reasons = [f"FAIL:{k}" for k in failing]
    data_fail = [k for k in failing if k.startswith(("market_active_fresh", "exchange_trading_active", "skew_ok",
                                                      "age_ok", "no_checker_bug", "fees_resolved"))]
    if data_fail:
        status = "REJECTED"
    elif struct.relationship_class != "GUARANTEED" or struct.locked < 1:
        status = "STATISTICAL"
        reasons.append(f"NOT_LOCKED:min_payoff={struct.locked}@{struct.argmin_state}")
    elif not _terms_ok(struct):
        status = "CANDIDATE_TERMS_UNVERIFIED"
    elif failing:
        status = "GUARANTEED_STRUCTURAL_NOT_EXECUTABLE"
    else:
        status = "ARBITRAGE"
    if not failing:
        reasons.append("ALL_GATES_PASSED")

    legs = []
    for p in struct.positions:
        b = books[p.ticker]
        f1 = walk(b.book.asks(p.side), Decimal(1))
        legs.append(LegRecord(p.ticker, "buy", p.side, "1", str(best[p.ticker].price), str(f1.vwap) if f1.filled else None,
                              str(f1.worst_price) if f1.filled else None, str(depth[p.ticker]), str(f1.filled),
                              None, None, b.sent_utc_ns, b.recv_utc_ns, b.book.source_format))
    rec = CandidateRecord(
        relationship=struct.relationship, relationship_class=struct.relationship_class, status=status,
        reasons=reasons, event_tickers=list(struct.events), size="grid", legs=legs,
        locked_payoff=str(struct.locked), raw_inconsistency=str(raw_nominal),
        max_executable_size=str(max_pos_size) if max_pos_size else None,
        skew_ns=skew, age_ns=age, persistence_confirmed=persistence_confirmed, snapshot_id=snapshot_id,
        settlement_evidence={"family_key": struct.family_key, "argmin_state": struct.argmin_state,
                             "nominal_locked": str(struct.nominal_locked), "notes": struct.notes},
    )
    rec.extra = {
        "raw_locked_top_of_book": str(raw_locked),
        "edges_by_size": grid_results,
        "n_positive_integer_sizes": n_pos_sizes,
        "gates": gates,
        "rule_5_11_distance": rng_detail,
        "fractional_depth_levels": fractional_levels,
        "one_leg_discretionary_worst_payoff": str(struct.one_leg_discretionary_worst),
        "residual_risks": list(RESIDUAL_RISKS),
        "fee_provenance": {t: (f.source, str(f.multiplier), f.fee_type) for t, f in fees.items()},
    }
    return "LOGGED", rec


def _terms_ok(struct: Structural) -> bool:
    # Categorical R1_SHORT / exclusive pairs rely only on MECNET "at most one market can resolve
    # to 'yes'" (API definition of mutually_exclusive), not on series-specific terms.
    if struct.family_key.startswith("MECNET:"):
        return struct.relationship in ("R1_SHORT", "R1_EXCLUSIVE_PAIR")
    return struct.terms_verified


def _rejected(struct: Structural, reasons: list[str], snapshot_id: str | None) -> CandidateRecord:
    rec = CandidateRecord(struct.relationship, struct.relationship_class, "REJECTED", reasons,
                          list(struct.events), "n/a", [], locked_payoff=str(struct.locked), snapshot_id=snapshot_id,
                          settlement_evidence={"family_key": struct.family_key})
    rec.extra = {"residual_risks": list(RESIDUAL_RISKS)}
    return rec
