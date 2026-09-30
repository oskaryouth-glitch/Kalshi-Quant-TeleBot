"""Paper-trading tests, focused on look-ahead bias and settlement rules."""

import sqlite3

import pytest

from lockerlab import paper
from lockerlab.capture import import_csv
from lockerlab.pit import snapshot_as_of
from lockerlab.strategies import OperatorEstimate

# Auction A1 ends 2026-10-04 14:00 MDT = 20:00 UTC
ACTIVE = "storagetreasures,A1,2026-10-01 10:00,active,Colorado Springs,5x10,$45,,2026-10-04 14:00,18,100,6,,6"
T_IMPORT = "2026-10-01T17:00:00.000000Z"
T_DECIDE = "2026-10-02T12:00:00.000000Z"
T_AFTER_END = "2026-10-04T20:00:00.000000Z"
T_SETTLE = "2026-10-06T00:00:00.000000Z"


def sold_row(price, observed="2026-10-04 15:00"):
    return f"storagetreasures,A1,{observed},sold,Colorado Springs,5x10,,,2026-10-04 14:00,18,100,6,${price},6"


# Rich enough to clear the margin rules under the repo config (a $900-base
# 5x10 does not: the $253 dump minimum and ~12h labor eat the margin).
EST = OperatorEstimate(
    gross_low_cents=60000, gross_base_cents=200000, gross_high_cents=400000, confidence=0.6,
    fill_fraction=0.5, keep_fraction=0.5, trash_fraction=0.2, n_listings=12, n_orders=10,
    longest_item_in=40, reasons=("visible tools",),
)


@pytest.fixture
def auction(conn, store, cfg, write_csv):
    import_csv(conn, store, cfg, write_csv(ACTIVE), "colorado_springs", now=T_IMPORT)
    return 1


def add_outcome(conn, store, cfg, write_csv, row, now="2026-10-04T22:00:00.000000Z"):
    import_csv(conn, store, cfg, write_csv(row), "colorado_springs", now=now)


class TestPointInTime:
    def test_snapshot_ignores_rows_recorded_later(self, conn, store, cfg, write_csv, auction):
        # A later bid snapshot claims to be observed early, but was only typed in on Oct 3.
        late = ACTIVE.replace("$45", "$300")
        import_csv(conn, store, cfg, write_csv(late), "colorado_springs", now="2026-10-03T00:00:00.000000Z")
        s = snapshot_as_of(conn, auction, T_DECIDE)
        assert s.current_bid_cents == 4500

    def test_snapshot_ignores_rows_observed_later(self, conn, store, cfg, write_csv, auction):
        add_outcome(conn, store, cfg, write_csv, sold_row(250))
        s = snapshot_as_of(conn, auction, T_DECIDE)
        assert s.status == "active"
        assert not hasattr(s, "final_price_cents")  # outcome fields never reach strategies

    def test_nothing_before_first_observation(self, conn, auction):
        assert snapshot_as_of(conn, auction, "2026-10-01T15:00:00.000000Z") is None


class TestDecisionGuards:
    def test_forward_decision_recorded(self, conn, cfg, auction):
        r = paper.decide(conn, cfg, auction, EST, now=T_DECIDE)
        row = conn.execute("SELECT * FROM paper_decisions").fetchone()
        assert row["decided_at"] == row["recorded_at"] == T_DECIDE
        assert row["basis_observation_id"] == 1
        assert row["decision"] == r.underwriting.decision
        assert row["model_version_id"] is not None

    def test_refused_after_known_end(self, conn, cfg, auction):
        with pytest.raises(paper.DecisionRefused, match="ended"):
            paper.decide(conn, cfg, auction, EST, now=T_AFTER_END)

    def test_refused_once_outcome_known(self, conn, store, cfg, write_csv, auction):
        # Cancelled (tenant paid) before the scheduled end: the end-time guard
        # alone would not catch this, the terminal-observation guard must.
        row = sold_row(1, observed="2026-10-02 08:00").replace(",sold,", ",cancelled,").replace("$1,", ",")
        add_outcome(conn, store, cfg, write_csv, row, now="2026-10-02T15:00:00.000000Z")
        with pytest.raises(paper.DecisionRefused, match="already over"):
            paper.decide(conn, cfg, auction, EST, now="2026-10-02T16:00:00.000000Z")

    def test_manual_strategy_cannot_backtest(self, conn, cfg, auction):
        with pytest.raises(paper.DecisionRefused, match="cannot be backtested"):
            paper.decide(conn, cfg, auction, EST, mode="BACKTEST", as_of=T_DECIDE, now=T_AFTER_END)

    def test_forward_rejects_as_of(self, conn, cfg, auction):
        with pytest.raises(paper.DecisionRefused):
            paper.decide(conn, cfg, auction, EST, as_of=T_IMPORT, now=T_DECIDE)

    def test_db_rejects_backdated_forward_decision(self, conn, cfg, auction):
        paper.decide(conn, cfg, auction, EST, now=T_DECIDE)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                """INSERT INTO paper_decisions (auction_id, strategy_key, mode, decided_at, recorded_at,
                   model_version_id, basis_observation_id, decision, inputs_json, inputs_sha256,
                   outputs_json, reasons_json)
                   VALUES (1, 'manual_v1', 'FORWARD', '2026-10-01T18:00:00.000000Z', ?, 1, 1, 'PASS',
                   '{}', 'x', '{}', '[]')""",
                (T_DECIDE,),
            )

    def test_db_rejects_decision_after_end(self, conn, cfg, auction):
        paper.decide(conn, cfg, auction, EST, now=T_DECIDE)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                """INSERT INTO paper_decisions (auction_id, strategy_key, mode, decided_at, recorded_at,
                   model_version_id, basis_observation_id, known_ends_at, decision, inputs_json,
                   inputs_sha256, outputs_json, reasons_json)
                   VALUES (1, 'manual_v1', 'FORWARD', ?, ?, 1, 1, '2026-10-04T20:00:00.000000Z', 'PASS',
                   '{}', 'x', '{}', '[]')""",
                (T_AFTER_END, T_AFTER_END),
            )

    def test_dry_run_records_nothing(self, conn, cfg, auction):
        paper.decide(conn, cfg, auction, EST, record=False, now=T_DECIDE)
        assert conn.execute("SELECT COUNT(*) FROM paper_decisions").fetchone()[0] == 0

    def test_decision_is_reproducible(self, conn, cfg, auction):
        a = paper.decide(conn, cfg, auction, EST, now=T_DECIDE)
        b = paper.decide(conn, cfg, auction, EST, now="2026-10-02T12:05:00.000000Z")
        rows = conn.execute("SELECT inputs_json, max_bid_cents, model_version_id FROM paper_decisions").fetchall()
        assert rows[0]["max_bid_cents"] == rows[1]["max_bid_cents"] == a.underwriting.max_bid_cents
        assert rows[0]["model_version_id"] == rows[1]["model_version_id"]
        re = paper.reevaluate(rows[0]["inputs_json"], a.underwriting.max_bid_cents)
        assert re["base"].net_profit_cents == a.underwriting.outputs["evaluations"]["base"]["net_profit_cents"]
        assert b.underwriting.max_bid_cents == a.underwriting.max_bid_cents

    def test_config_change_creates_new_model_version(self, conn, cfg, auction, home):
        paper.decide(conn, cfg, auction, EST, now=T_DECIDE)
        text = (home / "config" / "underwriting.yaml").read_text()
        (home / "config" / "underwriting.yaml").write_text(text.replace("value: 0.85", "value: 0.80"))
        from lockerlab.config import Config

        paper.decide(conn, Config.load(home / "config"), auction, EST, now="2026-10-02T13:00:00.000000Z")
        assert conn.execute("SELECT COUNT(*) FROM model_versions").fetchone()[0] == 2


class TestSettlement:
    def _decide(self, conn, cfg, est=EST):
        return paper.decide(conn, cfg, 1, est, now=T_DECIDE).underwriting

    def test_awaiting_outcome(self, conn, cfg, auction):
        self._decide(conn, cfg)
        assert paper.settle_all(conn, cfg, now=T_AFTER_END) == {"awaiting_outcome": 1}
        assert conn.execute("SELECT COUNT(*) FROM paper_settlements").fetchone()[0] == 0

    def test_won_prices(self, conn, store, cfg, write_csv, auction):
        uw = self._decide(conn, cfg)
        assert uw.decision == "PAPER_BID"
        price = uw.paper_bid_cents - 2000  # comfortably below our bid
        add_outcome(conn, store, cfg, write_csv, sold_row(price / 100))
        assert paper.settle_all(conn, cfg, now=T_SETTLE) == {"WON": 1}
        s = conn.execute("SELECT * FROM paper_settlements").fetchone()
        assert s["acq_price_conservative_cents"] == uw.paper_bid_cents  # pay our full max
        assert s["acq_price_neutral_cents"] == price + s["increment_cents"]
        assert s["acq_price_neutral_cents"] <= s["acq_price_conservative_cents"]

    def test_lost_when_within_one_increment(self, conn, store, cfg, write_csv, auction):
        uw = self._decide(conn, cfg)
        add_outcome(conn, store, cfg, write_csv, sold_row(uw.paper_bid_cents / 100))  # tie -> we lose
        assert paper.settle_all(conn, cfg, now=T_SETTLE) == {"LOST": 1}

    def test_cancelled_is_void(self, conn, store, cfg, write_csv, auction):
        self._decide(conn, cfg)
        add_outcome(conn, store, cfg, write_csv, sold_row(1).replace(",sold,", ",cancelled,").replace("$1,", ","))
        assert paper.settle_all(conn, cfg, now=T_SETTLE) == {"VOID": 1}

    def test_pass_is_not_bid(self, conn, store, cfg, write_csv, auction):
        poor = OperatorEstimate(0, 1000, 2000, 0.6, 0.5, 0.1, 0.8, 1, 1)
        assert self._decide(conn, cfg, poor).decision == "PASS"
        add_outcome(conn, store, cfg, write_csv, sold_row(75))
        assert paper.settle_all(conn, cfg, now=T_SETTLE) == {"NOT_BID": 1}

    def test_settlement_is_once_per_rule(self, conn, store, cfg, write_csv, auction):
        self._decide(conn, cfg)
        add_outcome(conn, store, cfg, write_csv, sold_row(50))
        paper.settle_all(conn, cfg, now=T_SETTLE)
        assert paper.settle_all(conn, cfg, now=T_SETTLE) == {}

    def test_late_recorded_early_outcome_voids_decision(self, conn, store, cfg, write_csv, auction):
        # The unit was actually cancelled Oct 1 evening, but that was only typed in on Oct 5.
        self._decide(conn, cfg)
        row = sold_row(1, observed="2026-10-01 20:00").replace(",sold,", ",cancelled,").replace("$1,", ",")
        add_outcome(conn, store, cfg, write_csv, row, now="2026-10-05T00:00:00.000000Z")
        assert paper.settle_all(conn, cfg, now=T_SETTLE) == {"VOID": 1}
        assert "invalid decision" in conn.execute("SELECT details_json FROM paper_settlements").fetchone()[0]
