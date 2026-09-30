"""Evidence reports. Every figure is labelled OBSERVED / INFERRED / ESTIMATED /
SIMULATED; nothing here is REALIZED until real acquisitions exist."""

from __future__ import annotations

import json
import sqlite3
import statistics
from collections import defaultdict

from .config import Config
from .money import fmt
from .paper import SETTLEMENT_RULE, reevaluate
from .units import SIZE_BUCKETS

BUCKET_ORDER = [b for b, _ in SIZE_BUCKETS] + [None]


def _pct(xs: list[int], q: float) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def market_rows(conn: sqlite3.Connection, market: str | None = None) -> list[dict]:
    """Per size bucket: how many auctions we have seen, how they ended, and
    what they cleared at (OBSERVED final prices; all-in cost INFERRED)."""
    q = """
    WITH latest AS (
        SELECT o.*, a.market_key,
               ROW_NUMBER() OVER (PARTITION BY o.auction_id ORDER BY o.observed_at DESC, o.id DESC) AS rn
        FROM auction_observations o JOIN auctions a ON a.id = o.auction_id
        WHERE (? IS NULL OR a.market_key = ?)
    ), sized AS (
        SELECT auction_id, size_bucket, width_ft, length_ft,
               ROW_NUMBER() OVER (PARTITION BY auction_id ORDER BY observed_at DESC, id DESC) AS rn
        FROM auction_observations WHERE size_bucket IS NOT NULL
    )
    SELECT l.auction_id, l.status, l.final_price_cents, l.buyer_premium_rate, l.sales_tax_rate,
           s.size_bucket, s.width_ft, s.length_ft
    FROM latest l LEFT JOIN sized s ON s.auction_id = l.auction_id AND s.rn = 1
    WHERE l.rn = 1
    """
    by: dict = defaultdict(list)
    for r in conn.execute(q, (market, market)):
        by[r["size_bucket"]].append(r)
    out = []
    for b in BUCKET_ORDER:
        rows = by.get(b, [])
        if not rows:
            continue
        sold = [r for r in rows if r["status"] == "sold"]
        prices = [r["final_price_cents"] for r in sold]
        psf = [r["final_price_cents"] / (r["width_ft"] * r["length_ft"]) for r in sold if r["width_ft"]]
        allin = [
            r["final_price_cents"] * (1 + (r["buyer_premium_rate"] or 0)) * (1 + (r["sales_tax_rate"] or 0))
            for r in sold
        ]
        closed = [r for r in rows if r["status"] in ("sold", "cancelled", "unsold")]
        out.append({
            "size_bucket": b or "unknown",
            "auctions": len(rows),
            "open_or_unknown": len(rows) - len(closed),
            "sold": len(sold),
            "cancelled": sum(r["status"] == "cancelled" for r in rows),
            "unsold": sum(r["status"] == "unsold" for r in rows),
            "cancel_rate": (sum(r["status"] == "cancelled" for r in closed) / len(closed)) if closed else None,
            "median_final_cents": statistics.median(prices) if prices else None,
            "p25_final_cents": _pct(prices, 0.25) if prices else None,
            "p75_final_cents": _pct(prices, 0.75) if prices else None,
            "median_final_per_sqft_cents": statistics.median(psf) if psf else None,
            "median_all_in_acquisition_cents": statistics.median(allin) if allin else None,
        })
    return out


def paper_rows(conn: sqlite3.Connection, strategy: str | None = None) -> list[dict]:
    """Per strategy, using each auction's operative decision (the latest one
    made before the auction ended)."""
    q = """
    WITH ranked AS (
        SELECT d.*, ROW_NUMBER() OVER (
            PARTITION BY d.auction_id, d.strategy_key, d.mode ORDER BY d.decided_at DESC, d.id DESC) AS rn
        FROM paper_decisions d WHERE (? IS NULL OR d.strategy_key = ?)
    )
    SELECT r.*, s.result, s.acq_price_conservative_cents, s.acq_price_neutral_cents, s.final_price_cents
    FROM ranked r LEFT JOIN paper_settlements s ON s.decision_id = r.id AND s.rule_version = ?
    WHERE r.rn = 1
    """
    groups: dict = defaultdict(list)
    for r in conn.execute(q, (strategy, strategy, SETTLEMENT_RULE)):
        groups[(r["strategy_key"], r["mode"])].append(r)
    out = []
    for (strat, mode), rows in sorted(groups.items()):
        won = [r for r in rows if r["result"] == "WON"]
        lost = [r for r in rows if r["result"] == "LOST"]
        profits_c, profits_n, capital = [], [], 0
        for r in won:
            ec = reevaluate(r["inputs_json"], r["acq_price_conservative_cents"])["base"]
            en = reevaluate(r["inputs_json"], r["acq_price_neutral_cents"])["base"]
            profits_c.append(ec.net_profit_cents)
            profits_n.append(en.net_profit_cents)
            capital += ec.cash_invested_cents
        out.append({
            "strategy": strat,
            "mode": mode,
            "auctions_decided": len(rows),
            "paper_bids": sum(r["decision"] == "PAPER_BID" for r in rows),
            "watch": sum(r["decision"] == "WATCH" for r in rows),
            "pass": sum(r["decision"] == "PASS" for r in rows),
            "awaiting_outcome": sum(r["result"] is None for r in rows),
            "won": len(won),
            "lost": len(lost),
            "void": sum(r["result"] == "VOID" for r in rows),
            "win_rate_SIMULATED": len(won) / (len(won) + len(lost)) if (won or lost) else None,
            "capital_committed_SIMULATED_cents": capital,
            "est_net_profit_conservative_ESTIMATED_cents": sum(profits_c),
            "est_net_profit_neutral_ESTIMATED_cents": sum(profits_n),
            "median_est_profit_ESTIMATED_cents": statistics.median(profits_c) if profits_c else None,
            "est_loss_rate_ESTIMATED": (sum(p < 0 for p in profits_c) / len(profits_c)) if profits_c else None,
        })
    return out


def coverage(conn: sqlite3.Connection) -> dict:
    one = lambda q: conn.execute(q).fetchone()[0]  # noqa: E731
    return {
        "auctions": one("SELECT COUNT(*) FROM auctions"),
        "observations": one("SELECT COUNT(*) FROM auction_observations"),
        "auctions_with_outcome": one(
            "SELECT COUNT(DISTINCT auction_id) FROM auction_observations "
            "WHERE status IN ('sold','cancelled','unsold')"),
        "auctions_closed_price_unknown": one(
            "SELECT COUNT(DISTINCT auction_id) FROM auction_observations o WHERE status = 'closed' "
            "AND NOT EXISTS (SELECT 1 FROM auction_observations x WHERE x.auction_id = o.auction_id "
            "AND x.status IN ('sold','cancelled','unsold'))"),
        "auctions_single_observation": one(
            "SELECT COUNT(*) FROM (SELECT auction_id FROM auction_observations "
            "GROUP BY auction_id HAVING COUNT(*) = 1)"),
        "images": one("SELECT COUNT(*) FROM images"),
        "paper_decisions": one("SELECT COUNT(*) FROM paper_decisions"),
        "decisions_awaiting_outcome": one(
            f"SELECT COUNT(*) FROM paper_decisions d WHERE NOT EXISTS (SELECT 1 FROM paper_settlements s "
            f"WHERE s.decision_id = d.id AND s.rule_version = '{SETTLEMENT_RULE}')"),
    }


def assumption_rows(cfg: Config) -> list[dict]:
    rows = []
    for k, m in cfg.markets.items():
        rows += m.unverified(f"markets.{k}")
    rows += cfg.underwriting.unverified("underwriting")
    return rows


def format_table(rows: list[dict], money_suffix: str = "_cents") -> str:
    if not rows:
        return "(no data)"
    cols = list(rows[0])

    def cell(c, v):
        if v is None:
            return "-"
        if c.endswith(money_suffix):
            return fmt(round(v))
        if isinstance(v, float):
            return f"{v:.0%}" if ("rate" in c) else f"{v:.2f}"
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        return str(v)

    header = [c.replace(money_suffix, "") for c in cols]
    body = [[cell(c, r[c]) for c in cols] for r in rows]
    widths = [max(len(h), *(len(b[i]) for b in body)) for i, h in enumerate(header)]
    line = lambda xs: "  ".join(x.ljust(w) for x, w in zip(xs, widths))  # noqa: E731
    return "\n".join([line(header), line(["-" * w for w in widths]), *(line(b) for b in body)])
