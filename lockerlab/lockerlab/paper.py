"""Paper decisions and settlement. See docs/PAPER_TRADING.md.

Look-ahead protections, in order:
  1. Strategies only see a point-in-time Snapshot (pit.snapshot_as_of).
  2. FORWARD decisions are stamped with the wall clock; the DB rejects any
     FORWARD row whose decided_at != recorded_at (no backdating).
  3. A decision is refused if the auction is already known to be over as of
     the decision time (terminal observation, or past its known end time).
     The DB also rejects decided_at >= known_ends_at.
  4. Strategies that use human judgement cannot run in BACKTEST mode, since
     a human looking at old auctions already knows (or can find) the outcome.
  5. Decisions and settlements are append-only; a changed model gets a new
     model_versions row, and old decisions keep pointing at the old one.
  6. Settlement uses a named, versioned rule. A new rule adds rows; it never
     rewrites old settlements.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import disposal, economics, strategies, transport
from .config import Config, canonical_json
from .db import transaction
from .economics import CostPolicy, Scenario, evaluate, increment_for
from .pit import TERMINAL_STATUSES, snapshot_as_of, terminal_observation_as_of
from .strategies import OperatorEstimate, Underwriting
from .timeutil import now_ts

SETTLEMENT_RULE = "settle_v1"

# Source files whose code determines a decision; hashed into model_versions.
_MODEL_MODULES = (economics, transport, disposal, strategies)


class DecisionRefused(RuntimeError):
    pass


def _code_sha() -> str:
    h = hashlib.sha256()
    for m in _MODEL_MODULES:
        h.update(Path(inspect.getfile(m)).read_bytes())
    return h.hexdigest()


def ensure_model_version(conn: sqlite3.Connection, model_key: str, version: str, config_obj: dict) -> int:
    code = _code_sha()
    cfg_json = canonical_json(config_obj)
    cfg_sha = hashlib.sha256(cfg_json.encode()).hexdigest()
    row = conn.execute(
        """SELECT id FROM model_versions WHERE model_key = ? AND version = ?
           AND code_sha256 = ? AND config_sha256 = ?""",
        (model_key, version, code, cfg_sha),
    ).fetchone()
    if row:
        return row["id"]
    return conn.execute(
        """INSERT INTO model_versions (model_key, version, code_sha256, config_json, config_sha256, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (model_key, version, code, cfg_json, cfg_sha, now_ts()),
    ).lastrowid


@dataclass
class DecisionResult:
    decision_id: int | None
    decided_at: str
    underwriting: Underwriting
    auction_id: int
    strategy_key: str


def decide(
    conn: sqlite3.Connection,
    cfg: Config,
    auction_id: int,
    estimate: OperatorEstimate,
    strategy_key: str = "manual_v1",
    mode: str = "FORWARD",
    as_of: str | None = None,
    record: bool = True,
    now: str | None = None,
) -> DecisionResult:
    """Underwrite an auction using only information available at the decision
    time, and (if ``record``) append the paper decision.

    ``now`` exists for tests; in normal use it is the wall clock.
    """
    if strategy_key not in strategies.STRATEGIES:
        raise DecisionRefused(f"unknown strategy {strategy_key!r}")
    strat = strategies.STRATEGIES[strategy_key]
    wall = now or now_ts()
    if mode == "FORWARD":
        if as_of is not None:
            raise DecisionRefused("FORWARD decisions are made at the current time; as_of is not allowed")
        t = wall
    elif mode == "BACKTEST":
        if not strat["automatic"]:
            raise DecisionRefused(
                f"{strategy_key} uses human judgement and cannot be backtested: the human may know the outcome"
            )
        if as_of is None or as_of > wall:
            raise DecisionRefused("BACKTEST needs an as_of in the past")
        t = as_of
    else:
        raise DecisionRefused(f"unknown mode {mode!r}")

    snap = snapshot_as_of(conn, auction_id, t)
    if snap is None:
        raise DecisionRefused(f"no observation of auction {auction_id} available as of {t}")
    term = terminal_observation_as_of(conn, auction_id, t)
    if term is not None or snap.status in TERMINAL_STATUSES:
        raise DecisionRefused(f"auction {auction_id} is already over as of {t}")
    if snap.ends_at is not None and t >= snap.ends_at:
        raise DecisionRefused(f"auction {auction_id} ended at {snap.ends_at}, before decision time {t}")

    market = cfg.market(snap.market_key)
    uw = strat["fn"](snap, estimate, market, cfg.underwriting)
    unverified = market.unverified(f"markets.{snap.market_key}") + cfg.underwriting.unverified("underwriting")
    uw.inputs["unverified_assumptions"] = unverified
    uw.outputs["unverified_assumption_count"] = len(unverified)

    if not record:
        return DecisionResult(None, t, uw, auction_id, strategy_key)

    inputs_json = canonical_json(uw.inputs)
    with transaction(conn):
        mv = ensure_model_version(
            conn, strategy_key, strat["version"],
            {"market": market.tree, "underwriting": cfg.underwriting.tree},
        )
        did = conn.execute(
            """INSERT INTO paper_decisions (auction_id, strategy_key, mode, decided_at, recorded_at,
                   model_version_id, basis_observation_id, known_ends_at, current_bid_cents, decision,
                   max_bid_cents, paper_bid_cents, confidence, inputs_json, inputs_sha256,
                   outputs_json, reasons_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                auction_id, strategy_key, mode, t, wall, mv, snap.observation_id, snap.ends_at,
                snap.current_bid_cents, uw.decision, uw.max_bid_cents, uw.paper_bid_cents,
                uw.confidence, inputs_json, hashlib.sha256(inputs_json.encode()).hexdigest(),
                canonical_json(uw.outputs), canonical_json(uw.reasons),
            ),
        ).lastrowid
    return DecisionResult(did, t, uw, auction_id, strategy_key)


@dataclass(frozen=True)
class Settlement:
    result: str
    final_price_cents: int | None
    increment_cents: int | None
    acq_price_conservative_cents: int | None
    acq_price_neutral_cents: int | None
    details: dict


def settle_one(decision: sqlite3.Row, outcome: sqlite3.Row, schedule) -> Settlement:
    """settle_v1 (docs/PAPER_TRADING.md):

    cancelled                -> VOID (tenant paid / auction pulled; no capital used)
    decision not PAPER_BID   -> NOT_BID (final price kept for missed-deal analysis)
    unsold (no bids)         -> WON at the opening bid if our bid covered it,
                                else LOST; VOID if the opening bid is unknown
    sold at P                -> WON iff paper_bid >= P + increment(P).
                                conservative price = our full paper bid
                                  (the winner's hidden max may have pushed us there)
                                neutral price = P + increment(P)
                                else LOST
    """
    status = outcome["status"]
    paper_bid = decision["paper_bid_cents"]
    if status == "cancelled":
        return Settlement("VOID", None, None, None, None, {"why": "auction cancelled"})
    if status == "unsold":
        opening = outcome["opening_bid_cents"]
        if decision["decision"] != "PAPER_BID":
            return Settlement("NOT_BID", None, None, None, None, {"why": "unsold; we did not bid"})
        if opening is None:
            return Settlement("VOID", None, None, None, None, {"why": "unsold, opening bid unknown"})
        if paper_bid >= opening:
            return Settlement("WON", opening, 0, opening, opening, {"why": "no competing bids"})
        return Settlement("LOST", None, None, None, None, {"why": "paper bid below opening bid"})
    if status != "sold":
        raise ValueError(f"cannot settle on status {status!r}")
    price = outcome["final_price_cents"]
    inc = increment_for(price, schedule)
    if decision["decision"] != "PAPER_BID":
        return Settlement("NOT_BID", price, inc, None, None,
                          {"max_bid_cents": decision["max_bid_cents"], "decision": decision["decision"]})
    if paper_bid >= price + inc:
        return Settlement("WON", price, inc, paper_bid, price + inc, {})
    return Settlement("LOST", price, inc, None, None, {"shortfall_cents": price + inc - paper_bid})


def settle_all(conn: sqlite3.Connection, cfg: Config, now: str | None = None) -> dict[str, int]:
    """Settle every unsettled decision whose auction has a settleable outcome."""
    t = now or now_ts()
    schedule = cfg.underwriting.get("bid_increments")
    counts: dict[str, int] = {}
    pending = conn.execute(
        """SELECT d.* FROM paper_decisions d
           WHERE NOT EXISTS (SELECT 1 FROM paper_settlements s
                             WHERE s.decision_id = d.id AND s.rule_version = ?)""",
        (SETTLEMENT_RULE,),
    ).fetchall()
    with transaction(conn):
        for d in pending:
            outcome = conn.execute(
                """SELECT * FROM auction_observations
                   WHERE auction_id = ? AND recorded_at <= ?
                     AND status IN ('sold', 'cancelled', 'unsold')
                   ORDER BY observed_at DESC, id DESC LIMIT 1""",
                (d["auction_id"], t),
            ).fetchone()
            if outcome is None:
                counts["awaiting_outcome"] = counts.get("awaiting_outcome", 0) + 1
                continue
            if outcome["observed_at"] <= d["decided_at"]:
                # The outcome was recorded late, but the auction was already over
                # when the decision was made. The decision is invalid, not a win or loss.
                s = Settlement("VOID", None, None, None, None,
                               {"why": "invalid decision: auction already over at decision time"})
            else:
                s = settle_one(d, outcome, schedule)
            conn.execute(
                """INSERT INTO paper_settlements (decision_id, rule_version, settled_at, outcome_observation_id,
                       result, final_price_cents, increment_cents, acq_price_conservative_cents,
                       acq_price_neutral_cents, details_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d["id"], SETTLEMENT_RULE, t, outcome["id"], s.result, s.final_price_cents,
                 s.increment_cents, s.acq_price_conservative_cents, s.acq_price_neutral_cents,
                 canonical_json(s.details)),
            )
            counts[s.result] = counts.get(s.result, 0) + 1
    return counts


def reevaluate(decision_inputs_json: str, bid_cents: int) -> dict[str, economics.Evaluation]:
    """Recompute a stored decision's scenarios at another bid (e.g. the
    settled acquisition price), using exactly the inputs it was made with."""
    inputs = json.loads(decision_inputs_json)
    policy = CostPolicy(**inputs["policy"])
    return {k: evaluate(bid_cents, Scenario(**s), policy) for k, s in inputs["scenarios"].items()}
