"""Quick underwriter, opportunity score, decision guards, assumption changes,
desk sections, calibration and readiness."""

import dataclasses
import json
import sqlite3

import pytest

from lockerlab import analysis, assumptions, desk, intake, paper
from lockerlab.assumptions import effective_config
from lockerlab.quick import QuickEstimate, gross_cases, opportunity_score, physical, quick_v1
from lockerlab.strategies import UnderwritingError

T0 = "2026-10-05T18:00:00.000000Z"
T_DEC = "2026-10-06T12:00:00.000000Z"
RICH = QuickEstimate(250000, 5000, 60000, "light", "car_suv", 0.8, ("TOOLS",))


def snap(w=5, l=5, bid=4000):
    return dataclasses.replace(analysis.synthetic_snapshot(w, l, "colorado_springs"), current_bid_cents=bid)


def new_auction(conn, store, cfg, n=1, size="5x5", bid="40", ends="2026-10-10 14:00", source="manual_other"):
    url = f"https://example.com/auction/{100000 + n}"
    r = intake.start_intake(conn, store, cfg, url, [], "colorado_springs", source, now=T0)
    aid, _, _ = intake.confirm_intake(conn, store, cfg, r.intake_id,
                                      {"unit_size": size, "current_bid": bid, "ends_at": ends}, now=T0)
    return aid


class TestQuickModel:
    def test_gross_cases(self, cfg):
        q = cfg.underwriting.section("quick")
        g = gross_cases(QuickEstimate(60000, 5000, 40000, "light", "car_suv", 0.6), q)
        # low = 0.6*600 + 50; base = 600 + 50 + 0.5*350; high = 1.25*600 + 400
        assert g == {"low": 41000, "base": 82500, "high": 115000}

    def test_physical_scales_with_size(self, cfg):
        q = cfg.underwriting.section("quick")
        heavy = QuickEstimate(0, 0, 0, "heavy", "pickup_van", 0.5)
        p5, p10 = physical(snap(5, 5), heavy, q), physical(snap(5, 10), heavy, q)
        assert (p5.mattresses, p10.mattresses, p5.bulky_items, p10.bulky_items) == (1, 2, 1, 2)
        assert p10.trash_cuft == pytest.approx(2 * p5.trash_cuft)
        assert p5.longest_item_in == 90

    def test_estimate_validation(self):
        with pytest.raises(UnderwritingError):
            QuickEstimate(100, 500, 100, "light", "car_suv", 0.5)
        with pytest.raises(UnderwritingError):
            QuickEstimate(100, 0, 0, "tidy", "car_suv", 0.5)
        with pytest.raises(UnderwritingError):
            QuickEstimate(100, 0, 0, "light", "car_suv", 0.5, ("GOLD",))

    def test_labor_value_never_changes_max_bid(self, cfg):
        a = quick_v1(snap(), RICH, cfg.market("colorado_springs"), cfg.underwriting)
        changed = assumptions.apply_overrides(cfg, {"underwriting.labor_value_cents_per_hour":
                                                    {"value": 9900, "status": "USER", "source": "t"}})
        b = quick_v1(snap(), RICH, changed.market("colorado_springs"), changed.underwriting)
        assert a.max_bid_cents == b.max_bid_cents
        assert a.outputs["evaluations"]["base"]["cash_profit_cents"] == b.outputs["evaluations"]["base"]["cash_profit_cents"]

    def test_age_19_rules_out_home_depot(self, cfg):
        uw = quick_v1(snap(5, 10), dataclasses.replace(RICH, transport="pickup_van"),
                      cfg.market("colorado_springs"), cfg.underwriting)
        hd = next(o for o in uw.outputs["transport"]["options"] if o["vehicle"] == "homedepot_cargo_van")
        assert not hd["feasible"] and "21+" in hd["reason"]


class TestScore:
    def test_transparent_and_bounded(self, cfg):
        uw = quick_v1(snap(), RICH, cfg.market("colorado_springs"), cfg.underwriting)
        s = opportunity_score(uw.outputs, dataclasses.asdict(RICH), "5x5", 4000, cfg.underwriting)
        assert 0 <= s["score"] <= 100
        assert s["score"] == max(0, min(100, round(sum(c["points"] for c in s["components"]))))
        assert all(c["why"] for c in s["components"])
        assert any("Tools" in c["why"] for c in s["components"])

    def test_score_never_changes_underwriting(self, cfg):
        base = quick_v1(snap(), RICH, cfg.market("colorado_springs"), cfg.underwriting)
        tweaked = assumptions.apply_overrides(cfg, {})
        tree = json.loads(json.dumps(tweaked.underwriting.tree))
        tree["score"]["category_points"]["value"]["TOOLS"] = -5
        from lockerlab.config import Assumptions
        uw2 = Assumptions(tree)
        other = quick_v1(snap(), RICH, cfg.market("colorado_springs"), uw2)
        assert other.max_bid_cents == base.max_bid_cents
        s1 = opportunity_score(base.outputs, dataclasses.asdict(RICH), "5x5", 4000, cfg.underwriting)
        s2 = opportunity_score(base.outputs, dataclasses.asdict(RICH), "5x5", 4000, uw2)
        assert s1["score"] > s2["score"]

    def test_zero_max_bid_is_not_treated_as_missing(self, cfg):
        uw = quick_v1(snap(bid=None), RICH, cfg.market("colorado_springs"), cfg.underwriting)
        out = dict(uw.outputs, max_bid_cents=0)
        s = opportunity_score(out, dataclasses.asdict(RICH), "5x5", None, cfg.underwriting)
        assert s["components"][0]["points"] == 12


class TestDecisionGuards:
    def test_paper_bid_cannot_exceed_max(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg)
        uw = paper.decide(conn, cfg, aid, RICH, "quick_v1", record=False, now=T_DEC).underwriting
        with pytest.raises(paper.DecisionRefused, match="exceed"):
            paper.decide(conn, cfg, aid, RICH, "quick_v1", now=T_DEC, choice="PAPER_BID",
                         paper_bid_cents=uw.max_bid_cents + 100)
        paper.decide(conn, cfg, aid, RICH, "quick_v1", now=T_DEC, choice="PAPER_BID",
                     paper_bid_cents=uw.max_bid_cents - 1000)
        row = conn.execute("SELECT * FROM paper_decisions").fetchone()
        assert (row["decision"], row["paper_bid_cents"], row["max_bid_cents"]) == (
            "PAPER_BID", uw.max_bid_cents - 1000, uw.max_bid_cents)
        assert json.loads(row["outputs_json"])["model_recommendation"] == "PAPER_BID"

    def test_paper_bid_below_current_refused(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg, bid="400")
        with pytest.raises(paper.DecisionRefused):
            paper.decide(conn, cfg, aid, RICH, "quick_v1", now=T_DEC, choice="PAPER_BID", paper_bid_cents=40000)

    def test_no_bid_allowed_when_rules_say_none(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg)
        poor = QuickEstimate(3000, 0, 1000, "heavy", "pickup_van", 0.9, ("HOUSEHOLD",))
        with pytest.raises(paper.DecisionRefused, match="WATCH or PASS"):
            paper.decide(conn, cfg, aid, poor, "quick_v1", now=T_DEC, choice="PAPER_BID")

    def test_pass_needs_a_reason_and_records_it(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg)
        with pytest.raises(paper.DecisionRefused, match="reason"):
            paper.decide(conn, cfg, aid, RICH, "quick_v1", now=T_DEC, choice="PASS")
        paper.decide(conn, cfg, aid, RICH, "quick_v1", now=T_DEC, choice="PASS",
                     pass_tags=("TOO_MUCH_TRASH", "TRANSPORT"), note="couch in back")
        rs = json.loads(conn.execute("SELECT reasons_json FROM paper_decisions").fetchone()[0])
        assert rs["pass_tags"] == ["TOO_MUCH_TRASH", "TRANSPORT"] and rs["note"] == "couch in back"

    def test_triage_pass_without_estimate(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg, size="10x20")
        paper.decide(conn, cfg, aid, None, "triage_v1", now=T_DEC, choice="PASS", pass_tags=("TOO_LARGE",))
        with pytest.raises(paper.DecisionRefused):
            paper.decide(conn, cfg, aid, None, "triage_v1", now=T_DEC, choice="PAPER_BID")
        row = conn.execute("SELECT * FROM paper_decisions").fetchone()
        assert row["strategy_key"] == "triage_v1" and row["max_bid_cents"] is None

    def test_no_decision_after_end(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg)
        with pytest.raises(paper.DecisionRefused, match="ended"):
            paper.decide(conn, cfg, aid, RICH, "quick_v1", now="2026-10-11T00:00:00.000000Z", choice="WATCH")

    def test_decision_sees_only_what_was_recorded_by_then(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg, bid="40")
        # a later capture showing a higher bid, recorded after the decision time
        r = intake.start_intake(conn, store, cfg, "https://example.com/auction/100001", [], "colorado_springs",
                                "manual_other", now="2026-10-07T12:00:00.000000Z")
        intake.confirm_intake(conn, store, cfg, r.intake_id, {"current_bid": "300"}, now="2026-10-07T12:00:00.000000Z")
        res = paper.decide(conn, cfg, aid, RICH, "quick_v1", record=False, now=T_DEC)
        assert res.underwriting.outputs["current_bid_cents"] == 4000


class TestAssumptionChanges:
    def test_old_decisions_unchanged_new_ones_differ(self, conn, store, cfg):
        aid = new_auction(conn, store, cfg)
        paper.decide(conn, cfg, aid, RICH, "quick_v1", now=T_DEC, choice="WATCH")
        before = [tuple(r) for r in conn.execute("SELECT * FROM paper_decisions")]
        sid = assumptions.save(conn, cfg, {"underwriting.labor.minutes_per_sale": ("45", "USER", "")},
                               note="slower selling", now="2026-10-06T13:00:00.000000Z")
        assert sid is not None
        cfg2 = effective_config(conn, cfg)
        assert cfg2.underwriting.get("labor", "minutes_per_sale") == 45
        paper.decide(conn, cfg2, aid, RICH, "quick_v1", now="2026-10-06T14:00:00.000000Z", choice="WATCH")
        rows = conn.execute("SELECT * FROM paper_decisions ORDER BY id").fetchall()
        assert tuple(rows[0]) == before[0]  # untouched
        assert rows[0]["model_version_id"] != rows[1]["model_version_id"]
        assert rows[1]["max_bid_cents"] < rows[0]["max_bid_cents"]
        retro = desk.retro(conn, cfg2)
        assert retro[0]["recorded_max_bid_cents"] == rows[0]["max_bid_cents"]
        assert retro[0]["max_bid_under_current_assumptions_cents"] == rows[1]["max_bid_cents"]
        assert conn.execute("SELECT COUNT(*) FROM paper_decisions").fetchone()[0] == 2  # retro wrote nothing

    def test_invalid_input_rejected(self, conn, cfg):
        with pytest.raises(ValueError):
            assumptions.save(conn, cfg, {"underwriting.target_cash_roi": ("150", "USER", "")})
        with pytest.raises(ValueError):
            assumptions.save(conn, cfg, {"markets.colorado_springs.disposal.weight_schedule": ("100:25, 50:30", "USER", "")})
        with pytest.raises(KeyError):
            assumptions.save(conn, cfg, {"underwriting.bid_increments": ("1", "USER", "")})

    def test_no_change_no_row_and_sets_are_append_only(self, conn, cfg):
        assert assumptions.save(conn, cfg, {"underwriting.labor.minutes_per_sale": ("25", "GUESS", "")}) is None
        assumptions.save(conn, cfg, {"underwriting.labor.minutes_per_sale": ("30", "VERIFIED", "timed 10 sales")})
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE assumption_sets SET note = 'x'")
        lf = assumptions.leaf(effective_config(conn, cfg), "underwriting.labor.minutes_per_sale")
        assert (lf["value"], lf["status"], lf["source"]) == (30.0, "VERIFIED", "timed 10 sales")


class TestDesk:
    def test_sections_and_health(self, conn, store, cfg):
        a_need = new_auction(conn, store, cfg, 1)
        a_bid = new_auction(conn, store, cfg, 2)
        a_pass = new_auction(conn, store, cfg, 3)
        a_big = new_auction(conn, store, cfg, 4, size="10x20")
        a_done = new_auction(conn, store, cfg, 5, ends="2026-10-06 10:00")
        paper.decide(conn, cfg, a_bid, RICH, "quick_v1", now=T_DEC, choice="PAPER_BID")
        paper.decide(conn, cfg, a_pass, None, "triage_v1", now=T_DEC, choice="PASS", pass_tags=("LOW_VALUE",))
        now = "2026-10-09T21:00:00.000000Z"  # 23h before the 10/10 14:00 MDT close
        intake.record_result(conn, store, cfg, a_done, "sold", "120", now=now)
        rows = desk.load_auctions(conn, cfg, "colorado_springs", now)
        s = desk.sections(rows, desk.Filters())
        ids = lambda k: [r.id for r in s[k]]  # noqa: E731
        assert ids("NEEDS_ESTIMATE") == [a_need]  # 10x20 filtered out by the small-unit default
        assert ids("PAPER_BID") == [a_bid] and ids("PASS") == [a_pass] and ids("CLOSED") == [a_done]
        assert a_bid in ids("ENDING_SOON") and a_pass not in ids("ENDING_SOON")
        assert ids("TOP") == [a_bid] and s["TOP"][0].score["score"] > 0
        assert a_big in [r.id for r in desk.sections(rows, desk.Filters(sizes=()))["NEEDS_ESTIMATE"]]
        h = desk.health(rows, now)
        assert (h["closed"], h["closed_5x5"], h["paper_bids"], h["passes"], h["days_collecting"]) == (1, 1, 1, 1, 5)

    def test_awaiting_result(self, conn, store, cfg):
        new_auction(conn, store, cfg)
        rows = desk.load_auctions(conn, cfg, "colorado_springs", "2026-10-11T00:00:00.000000Z")
        assert rows[0].state == "AWAITING_RESULT"

    def test_estimate_filters_keep_unestimated(self, conn, store, cfg):
        a_need = new_auction(conn, store, cfg, 1)
        a_bid = new_auction(conn, store, cfg, 2)
        paper.decide(conn, cfg, a_bid, RICH, "quick_v1", now=T_DEC, choice="WATCH")
        rows = desk.load_auctions(conn, cfg, "colorado_springs", T_DEC)
        s = desk.sections(rows, desk.Filters(min_cash_profit_cents=10**9))
        assert [r.id for r in s["NEEDS_ESTIMATE"]] == [a_need] and s["WATCHING"] == []

    def test_calibration_needs_sample(self, conn, store, cfg):
        a = new_auction(conn, store, cfg)
        paper.decide(conn, cfg, a, RICH, "quick_v1", now=T_DEC, choice="PAPER_BID")
        intake.record_result(conn, store, cfg, a, "sold", "100", now="2026-10-11T00:00:00.000000Z")
        rows = desk.load_auctions(conn, cfg, "colorado_springs", "2026-10-11T00:00:00.000000Z")
        c = desk.calibration(conn, rows)
        assert c["groups"]["All estimated, sold"]["n"] == 1
        assert c["groups"]["All estimated, sold"]["reading"] == "too few to read"
        assert c["rank_correlation"] is None

    def test_spearman(self):
        assert desk._spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
        assert desk._spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)

    def test_readiness_never_says_buy(self, conn, store, cfg):
        rows = desk.load_auctions(conn, cfg, "colorado_springs", T_DEC)
        r = desk.readiness(conn, cfg, rows, T_DEC)
        text = json.dumps(r).lower()
        assert "buy" not in text and "recommend" not in text
        assert r["met"] < r["total"]
        assert any(u["label"] == "Selling minutes per sale" for u in r["unresolved"])
