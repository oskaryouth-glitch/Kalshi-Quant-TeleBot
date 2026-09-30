"""The daily desk: what needs attention, ranked, plus dataset health,
calibration and readiness. Read-only: nothing here writes to the database.

Every number is labelled by kind in the UI: OBSERVED (from captures),
ESTIMATED (from your estimate + the model), SIMULATED (paper wins/losses).
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from dataclasses import dataclass, field

from .config import Config
from .economics import CostPolicy, Scenario, evaluate
from .paper import SETTLEMENT_RULE
from .pit import Snapshot
from .quick import QuickEstimate, opportunity_score, quick_v1
from .strategies import UnderwritingError
from .timeutil import from_ts, now_ts

SMALL = ("5x5", "5x10")
ENDING_SOON_HOURS = 24
LISTING_STATUSES = ("scheduled", "active")
RESULT_STATUSES = ("sold", "cancelled", "unsold", "closed")


@dataclass
class AuctionRow:
    id: int
    source_key: str
    external_id: str
    market_key: str
    url: str | None = None
    facility: str | None = None
    city: str | None = None
    unit_label: str | None = None
    size_bucket: str | None = None
    size_text: str | None = None
    current_bid_cents: int | None = None
    bid_count: int | None = None
    ends_at: str | None = None
    hours_left: float | None = None
    photo_count: int | None = None
    images: int = 0
    snapshots: int = 0
    result_status: str | None = None
    final_price_cents: int | None = None
    decision: dict | None = None
    settlement: dict | None = None
    state: str = "NEEDS_ESTIMATE"
    score: dict | None = None
    metrics: dict = field(default_factory=dict)
    first_observed_at: str | None = None


def _hours_left(ends_at: str | None, now: str) -> float | None:
    if not ends_at:
        return None
    return (from_ts(ends_at) - from_ts(now)).total_seconds() / 3600


def load_auctions(conn: sqlite3.Connection, cfg: Config, market: str | None = None,
                  now: str | None = None) -> list[AuctionRow]:
    now = now or now_ts()
    rows: dict[int, AuctionRow] = {}
    for a in conn.execute("SELECT * FROM auctions WHERE (? IS NULL OR market_key = ?)", (market, market)):
        rows[a["id"]] = AuctionRow(a["id"], a["source_key"], a["external_id"], a["market_key"])
    if not rows:
        return []
    for o in conn.execute("SELECT * FROM auction_observations ORDER BY observed_at, id"):
        r = rows.get(o["auction_id"])
        if r is None:
            continue
        r.snapshots += 1
        r.first_observed_at = r.first_observed_at or o["observed_at"]
        if o["status"] in LISTING_STATUSES:
            for attr, col in (("url", "url"), ("facility", "facility_name"), ("city", "city"),
                              ("unit_label", "unit_label"), ("size_bucket", "size_bucket"),
                              ("current_bid_cents", "current_bid_cents"), ("bid_count", "bid_count"),
                              ("ends_at", "ends_at"), ("photo_count", "photo_count")):
                if o[col] is not None:
                    setattr(r, attr, o[col])
            if o["width_ft"]:
                r.size_text = f"{o['width_ft']:g}x{o['length_ft']:g}"
        elif o["status"] in RESULT_STATUSES:
            r.result_status = o["status"]
            r.final_price_cents = o["final_price_cents"]
            if o["bid_count"] is not None:
                r.bid_count = o["bid_count"]
    for i in conn.execute("SELECT auction_id, COUNT(*) n FROM images GROUP BY auction_id"):
        if i["auction_id"] in rows:
            rows[i["auction_id"]].images = i["n"]
    decisions = conn.execute(
        """WITH ranked AS (SELECT d.*, ROW_NUMBER() OVER (PARTITION BY d.auction_id
                             ORDER BY d.decided_at DESC, d.id DESC) rn FROM paper_decisions d
                           WHERE d.mode = 'FORWARD')
           SELECT r.*, s.result, s.acq_price_conservative_cents, s.acq_price_neutral_cents,
                  s.final_price_cents AS settled_price
           FROM ranked r LEFT JOIN paper_settlements s ON s.decision_id = r.id AND s.rule_version = ?
           WHERE r.rn = 1""", (SETTLEMENT_RULE,)).fetchall()
    uw = cfg.underwriting
    lv = str(uw.get("labor_value_cents_per_hour"))
    for d in decisions:
        r = rows.get(d["auction_id"])
        if r is None:
            continue
        outputs = json.loads(d["outputs_json"])
        inputs = json.loads(d["inputs_json"])
        reasons = json.loads(d["reasons_json"])
        est = inputs.get("quick_estimate")
        r.decision = {"id": d["id"], "choice": d["decision"], "strategy": d["strategy_key"],
                      "decided_at": d["decided_at"], "max_bid_cents": d["max_bid_cents"],
                      "paper_bid_cents": d["paper_bid_cents"], "confidence": d["confidence"],
                      "model_recommendation": outputs.get("model_recommendation"),
                      "pass_tags": reasons.get("pass_tags", []) if isinstance(reasons, dict) else [],
                      "note": reasons.get("note", "") if isinstance(reasons, dict) else "",
                      "estimate": est}
        if d["result"]:
            r.settlement = {"result": d["result"], "conservative": d["acq_price_conservative_cents"],
                            "neutral": d["acq_price_neutral_cents"], "price": d["settled_price"]}
        if est and "evaluations" in outputs:
            base = outputs["evaluations"]["base"]
            econ = outputs["economic_profit_cents_by_labor_value"]["base"].get(lv)
            # Recomputed at the LATEST observed bid from the decision's stored
            # inputs (display only; the recorded decision is unchanged).
            cur_bid = r.current_bid_cents or 0
            at_cur = evaluate(cur_bid, Scenario(**inputs["scenarios"]["base"]), CostPolicy(**inputs["policy"]))
            r.metrics = {
                "cash_at_current_cents": at_cur.cash_profit_cents,
                "economic_at_current_cents": at_cur.economic_profit_cents(int(lv)),
                "bid_for_current_cents": cur_bid,
                "max_bid_cents": d["max_bid_cents"],
                "cash_profit_cents": base["cash_profit_cents"],
                "economic_profit_cents": econ,
                "labor_value_cents": int(lv),
                "cash_roi": base.get("cash_roi"),
                "cash_per_hour_cents": base.get("cash_profit_per_hour_cents"),
                "labor_hours": base["labor_hours"],
                "cash_per_kept_cuft_cents": (base["cash_profit_cents"] / base["retained_cuft"]
                                             if base["retained_cuft"] else None),
                "low_cash_cents": outputs["evaluations"]["low"]["cash_profit_cents"],
                "high_cash_cents": outputs["evaluations"]["high"]["cash_profit_cents"],
                "all_in_acquisition_cents": base["acquisition"]["total_cents"],
                "cash_costs_cents": base["cash_expenses_cents"],
                "disposal_level": est["disposal"],
                "vehicle": outputs["transport"]["choice"]["vehicle"],
                "fits_suv": outputs["transport"]["choice"]["vehicle"].startswith("friend_"),
                "confidence": est["confidence"],
                "tags": est.get("tags", []),
            }
            r.score = opportunity_score(outputs, est, r.size_bucket, r.current_bid_cents, uw)
    for r in rows.values():
        r.hours_left = _hours_left(r.ends_at, now)
        if r.result_status:
            r.state = "CLOSED"
        elif r.hours_left is not None and r.hours_left <= 0:
            r.state = "AWAITING_RESULT"
        elif r.decision is None:
            r.state = "NEEDS_ESTIMATE"
        else:
            r.state = {"WATCH": "WATCHING", "PAPER_BID": "PAPER_BID", "PASS": "PASS"}[r.decision["choice"]]
    return list(rows.values())


@dataclass
class Filters:
    sizes: tuple[str, ...] = SMALL
    max_current_bid_cents: int | None = None
    ending_within_hours: float | None = None
    low_disposal: bool = False
    fits_suv: bool = False
    category: str | None = None
    min_cash_profit_cents: int | None = None
    min_roi: float | None = None
    min_confidence: float | None = None

    def estimate_filters_active(self) -> bool:
        return any([self.low_disposal, self.fits_suv, self.category, self.min_cash_profit_cents is not None,
                    self.min_roi is not None, self.min_confidence is not None])


def passes(r: AuctionRow, f: Filters) -> bool:
    """Size / bid / time filters apply to everything. Estimate-based filters
    apply only to estimated auctions: an unestimated one still needs you."""
    if f.sizes and (r.size_bucket or "unknown") not in f.sizes and not (r.size_bucket is None and "unknown" in f.sizes):
        return False
    if f.max_current_bid_cents is not None and (r.current_bid_cents or 0) > f.max_current_bid_cents:
        return False
    if f.ending_within_hours is not None and (r.hours_left is None or r.hours_left > f.ending_within_hours):
        return False
    m = r.metrics
    if not m:
        return True
    if f.low_disposal and m["disposal_level"] not in ("negligible", "light"):
        return False
    if f.fits_suv and not m["fits_suv"]:
        return False
    if f.category and f.category not in m["tags"]:
        return False
    if f.min_cash_profit_cents is not None and m["cash_profit_cents"] < f.min_cash_profit_cents:
        return False
    if f.min_roi is not None and (m["cash_roi"] is None or m["cash_roi"] < f.min_roi):
        return False
    if f.min_confidence is not None and m["confidence"] < f.min_confidence:
        return False
    return True


def sections(rows: list[AuctionRow], f: Filters) -> dict[str, list[AuctionRow]]:
    shown = [r for r in rows if passes(r, f)]
    open_rows = [r for r in shown if r.state in ("NEEDS_ESTIMATE", "WATCHING", "PAPER_BID", "PASS")]
    by_score = lambda r: (-(r.score["score"] if r.score else -1), r.hours_left if r.hours_left is not None else 1e9)  # noqa: E731
    by_end = lambda r: r.hours_left if r.hours_left is not None else 1e9  # noqa: E731
    return {
        "TOP": sorted([r for r in open_rows if r.score and r.state in ("WATCHING", "PAPER_BID")], key=by_score)[:5],
        "ENDING_SOON": sorted([r for r in open_rows if r.state != "PASS" and r.hours_left is not None
                               and r.hours_left <= ENDING_SOON_HOURS], key=by_end),
        "NEEDS_ESTIMATE": sorted([r for r in open_rows if r.state == "NEEDS_ESTIMATE"],
                                 key=lambda r: (r.size_bucket not in SMALL, by_end(r))),
        "WATCHING": sorted([r for r in open_rows if r.state == "WATCHING"], key=by_score),
        "PAPER_BID": sorted([r for r in open_rows if r.state == "PAPER_BID"], key=by_end),
        "PASS": sorted([r for r in open_rows if r.state == "PASS"], key=by_end),
        "AWAITING_RESULT": sorted([r for r in shown if r.state == "AWAITING_RESULT"], key=lambda r: r.ends_at or ""),
        "CLOSED": sorted([r for r in shown if r.state == "CLOSED"], key=lambda r: r.ends_at or "", reverse=True)[:25],
    }


def health(rows: list[AuctionRow], now: str | None = None) -> dict:
    now = now or now_ts()
    closed = [r for r in rows if r.state == "CLOSED"]
    forward = [r for r in rows if r.first_observed_at and (r.ends_at is None or r.first_observed_at < r.ends_at)]
    firsts = [r.first_observed_at for r in rows if r.first_observed_at]
    days = (from_ts(now) - from_ts(min(firsts))).days + 1 if firsts else 0
    settled = [r for r in rows if r.settlement]
    closed_small = [r for r in closed if r.size_bucket in SMALL and r.result_status != "closed"]
    return {
        "forward_captured": len(forward),
        "closed": len(closed),
        "closed_5x5": sum(r.size_bucket == "5x5" for r in closed),
        "closed_5x10": sum(r.size_bucket == "5x10" for r in closed),
        "closed_other": sum(r.size_bucket not in SMALL for r in closed),
        "closed_small_known": len(closed_small),
        "paper_bids": sum(1 for r in rows if r.decision and r.decision["choice"] == "PAPER_BID"),
        "paper_wins": sum(1 for r in settled if r.settlement["result"] == "WON"),
        "passes": sum(1 for r in rows if r.decision and r.decision["choice"] == "PASS"),
        "unknown_results": sum(r.result_status == "closed" for r in rows),
        "awaiting_result": sum(r.state == "AWAITING_RESULT" for r in rows),
        "days_collecting": days,
        "target_closed_small": 100,
    }


# ---------------------------------------------------------------------------
# Calibration: our max bid and estimate vs what the market actually paid.
# ---------------------------------------------------------------------------

MIN_N = 10
SOLID_N = 30


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if vx == 0 or vy == 0 else cov / (vx * vy)


def _group_stats(items: list[dict]) -> dict:
    n = len(items)
    out = {"n": n, "reading": "too few to read" if n < MIN_N else "early signal only" if n < SOLID_N
           else "readable (market prices only, not realized value)"}
    if n:
        ratios = [i["max_over_price"] for i in items]
        out["median_max_over_price"] = statistics.median(ratios)
        out["share_we_would_win"] = sum(i["would_win"] for i in items) / n
        out["median_estimate_over_price"] = statistics.median(i["estimate_over_price"] for i in items)
    return out


def calibration(conn: sqlite3.Connection, rows: list[AuctionRow]) -> dict:
    items = []
    for r in rows:
        d = r.decision
        if not d or not d["estimate"] or r.result_status != "sold" or not r.final_price_cents:
            continue
        est = d["estimate"]
        price = r.final_price_cents
        max_bid = d["max_bid_cents"] or 0
        base_est = est["visible_value_cents"] + (est["hidden_low_cents"] + est["hidden_high_cents"]) / 2
        items.append({
            "auction": r, "tags": est.get("tags") or ["UNKNOWN"], "disposal": est["disposal"],
            "small": r.size_bucket in SMALL, "visible": est["visible_value_cents"],
            "confidence": est["confidence"], "max_over_price": max_bid / price,
            "would_win": max_bid >= price, "estimate_over_price": base_est / price, "base_est": base_est,
            "price": price, "choice": d["choice"],
        })
    groups: dict[str, dict] = {}

    def add(name, pred):
        groups[name] = _group_stats([i for i in items if pred(i)])

    add("All estimated, sold", lambda i: True)
    for t in sorted({t for i in items for t in i["tags"]}):
        add(f"Tag: {t.replace('_', '/').title()}", lambda i, t=t: t in i["tags"])
    add("Messy (medium/heavy disposal)", lambda i: i["disposal"] in ("medium", "heavy"))
    add("Organized (negligible/light)", lambda i: i["disposal"] in ("negligible", "light"))
    add("Small (5x5, 5x10)", lambda i: i["small"])
    add("Larger", lambda i: not i["small"])
    add("Expensive-looking (visible ≥ $1,000)", lambda i: i["visible"] >= 100000)
    add("Visible < $1,000", lambda i: i["visible"] < 100000)
    add("Confidence ≥ 60%", lambda i: i["confidence"] >= 0.6)
    add("Confidence < 60%", lambda i: i["confidence"] < 0.6)
    rho = _spearman([i["base_est"] for i in items], [i["price"] for i in items]) if len(items) >= MIN_N else None
    pass_reasons: dict[str, int] = {}
    for r in rows:
        if r.decision and r.decision["choice"] == "PASS":
            for t in r.decision["pass_tags"]:
                pass_reasons[t] = pass_reasons.get(t, 0) + 1
    missed = [i for i in items if i["choice"] != "PAPER_BID" and i["would_win"]]
    return {"groups": groups, "n": len(items), "rank_correlation": rho, "pass_reasons": pass_reasons,
            "missed_deals": len(missed)}


# ---------------------------------------------------------------------------
# Readiness: evidence still missing before a first real experiment could even
# be considered. Never recommends buying.
# ---------------------------------------------------------------------------

TOP_ASSUMPTIONS = (
    ("underwriting.labor.minutes_per_sale", "Selling minutes per sale"),
    ("underwriting.labor.minutes_per_listing", "Listing minutes per item"),
    ("underwriting.quick.avg_sale_by_category_cents", "Average sale price by category"),
    ("markets.colorado_springs.disposal.weight_schedule", "Dump pricing by weight"),
    ("underwriting.quick.disposal_profiles", "Trash share by disposal level"),
    ("markets.colorado_springs.vehicles.friend_suv.available", "Borrowed SUV availability"),
    ("underwriting.tax_regime", "Tax regime"),
    ("underwriting.valuation_haircut", "Valuation haircut"),
    ("underwriting.returns_rate", "Returns and no-shows"),
)


def _latest_checks(conn) -> dict[str, sqlite3.Row]:
    out = {}
    for r in conn.execute("SELECT * FROM readiness_checks ORDER BY id"):
        out[r["check_key"]] = r
    return out


def readiness(conn: sqlite3.Connection, cfg: Config, rows: list[AuctionRow], now: str | None = None) -> dict:
    from .assumptions import leaf
    from .platforms import capture_policy

    h = health(rows, now)
    checks = _latest_checks(conn)
    decided_before_close = sum(1 for r in rows if r.decision and r.state == "CLOSED")
    won = h["paper_wins"]
    lost = sum(1 for r in rows if r.settlement and r.settlement["result"] == "LOST")
    margins = [r.decision["max_bid_cents"] - r.final_price_cents for r in rows
               if r.decision and r.decision["choice"] == "PAPER_BID" and r.final_price_cents is not None
               and r.decision["max_bid_cents"] is not None]
    small_prices = [r.final_price_cents for r in rows if r.result_status == "sold" and r.size_bucket in SMALL]
    sells = conn.execute("SELECT * FROM selling_time_log").fetchall()
    items = []

    def item(name, done, have, need, missing):
        items.append({"name": name, "done": bool(done), "have": have, "need": need, "missing": missing})

    item("Closed small-unit auctions observed", h["closed_small_known"] >= 100, h["closed_small_known"], 100,
         f"{max(0, 100 - h['closed_small_known'])} more with a known result")
    item("Days observing", h["days_collecting"] >= 56, h["days_collecting"], 56, "at least 8 weeks of forward capture")
    item("Decisions recorded before close", decided_before_close >= 40, decided_before_close, 40,
         "estimate and decide before auctions end")
    decided = sum(1 for r in rows if r.decision)
    bid_rate = h["paper_bids"] / decided if decided else None
    item("Paper bid rate", decided > 0, f"{bid_rate:.0%}" if bid_rate is not None else "n/a", "reported",
         "context only: how selective the rules are")
    win_rate = won / (won + lost) if won + lost else None
    item("Paper win rate (conservative rule)", won >= 5 and (win_rate or 0) >= 0.10,
         f"{won} won of {won + lost}" if won + lost else "none settled", "≥ 5 wins and ≥ 10%",
         "settled paper bids")
    item("Margin: median max bid minus winning price", len(margins) >= 10,
         f"${statistics.median(margins) / 100:,.0f} (n={len(margins)})" if margins else "n/a", "n ≥ 10",
         "paper bids with a sold result")
    item("Small-unit clearing price", len(small_prices) >= 30,
         f"median ${statistics.median(small_prices) / 100:,.0f} (n={len(small_prices)})" if small_prices else "n/a",
         "n ≥ 30", "sold small units")
    age = leaf(cfg, "underwriting.operator_age")
    item("Transport confirmed first-hand",
         checks.get("transport_confirmed") is not None and checks["transport_confirmed"]["status"] == "done",
         checks["transport_confirmed"]["note"] if "transport_confirmed" in checks else "not recorded",
         "a named friend's vehicle on 48 h notice, or a U-Haul plan",
         f"age {age['value']} ({age['status']}); record a transport check")
    ws = leaf(cfg, "markets.colorado_springs.disposal.weight_schedule")
    item("Disposal pricing verified", ws["status"] == "VERIFIED" or (
        "disposal_called" in checks and checks["disposal_called"]["status"] == "done"),
         ws["status"], "VERIFIED", "call Woodmen Dump / Peak Disposal and record it")
    sold_sells = [s for s in sells if s["sold"]]
    item("Timed selling experiment", len(sold_sells) >= 10, f"{len(sold_sells)} timed sales", 10,
         "sell your own items and log listing + selling minutes")
    item("Dry, secure storage identified",
         "storage_space" in checks and checks["storage_space"]["status"] == "done",
         checks["storage_space"]["note"] if "storage_space" in checks else "not recorded", "recorded", "")
    sources = [{"source": k, "policy": capture_policy(conn, cfg.sources, k).screenshot_policy,
                "automated": v.get("automated_collection"), "next": v.get("next_step", "")}
               for k, v in cfg.sources.items()]
    unresolved = []
    for path, label in TOP_ASSUMPTIONS:
        lf = leaf(cfg, path)
        if lf["status"] != "VERIFIED":
            unresolved.append({"label": label, "status": lf["status"], "path": path})
    timed = {}
    if sold_sells:
        timed = {"median_listing_minutes": statistics.median(s["listing_minutes"] for s in sold_sells),
                 "median_selling_minutes": statistics.median(s["selling_minutes"] for s in sold_sells),
                 "assumed_listing": cfg.underwriting.get("labor", "minutes_per_listing"),
                 "assumed_selling": cfg.underwriting.get("labor", "minutes_per_sale")}
    return {"items": items, "sources": sources, "unresolved": unresolved, "timed": timed,
            "met": sum(i["done"] for i in items), "total": len(items)}


def retro(conn: sqlite3.Connection, cfg: Config) -> list[dict]:
    """RETROSPECTIVE, not stored: re-run past quick estimates under the CURRENT
    assumptions to see how much an assumption change would have moved max bids.
    Recorded decisions are untouched."""
    out = []
    for d in conn.execute("SELECT * FROM paper_decisions WHERE strategy_key = 'quick_v1' ORDER BY decided_at"):
        inputs = json.loads(d["inputs_json"])
        snap = Snapshot(**inputs["snapshot"])
        est = QuickEstimate(**{k: (tuple(v) if k == "tags" else v) for k, v in inputs["quick_estimate"].items()})
        try:
            uw = quick_v1(snap, est, cfg.market(snap.market_key), cfg.underwriting)
            now_max = uw.max_bid_cents
        except UnderwritingError as e:
            now_max = f"error: {e}"
        out.append({"decision_id": d["id"], "auction_id": d["auction_id"], "decided_at": d["decided_at"],
                    "recorded_max_bid_cents": d["max_bid_cents"], "max_bid_under_current_assumptions_cents": now_max})
    return out
