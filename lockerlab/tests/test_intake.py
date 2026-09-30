"""Capture workflow: policy gating, field provenance, duplicates, results."""

import json
import sqlite3

import pytest

from lockerlab import intake, paper
from lockerlab.extract import FIELDS, ExtractorResult
from lockerlab.platforms import capture_policy, set_policy
from lockerlab.quick import QuickEstimate

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64
T0 = "2026-10-05T18:00:00.000000Z"


class FakeExtractor:
    name = "fake:v1"

    def __init__(self, **fields):
        self.fields = fields
        self.calls = 0

    def extract(self, images, context):
        self.calls += 1
        t = {f: {"visible": False, "text": "", "confidence": 0, "evidence": ""} for f in FIELDS}
        for k, (text, conf) in self.fields.items():
            t[k] = {"visible": True, "text": text, "confidence": conf, "evidence": "screenshot 1"}
        return ExtractorResult("ok", json.dumps(t), t, model="fake")


EXTRACTED = dict(unit_size=("5x10", 0.95), current_bid=("$85", 0.9), bid_count=("7 bids", 0.8),
                 ends_at=("Oct 10, 2026 2:00 PM MDT", 0.9), facility_name=("Example Storage", 0.8))


def allowed_intake(conn, store, cfg, url="https://example.com/auction/482913", files=((("s.png", PNG, "screenshot"),)),
                   now=T0):
    return intake.start_intake(conn, store, cfg, url, list(files), "colorado_springs", "manual_other", now=now)


class TestPolicy:
    def test_storagetreasures_is_manual_only_by_default(self, conn, cfg):
        assert capture_policy(conn, cfg.sources, "storagetreasures").screenshot_policy == "manual_only"
        assert capture_policy(conn, cfg.sources, "lockerfox").screenshot_policy == "manual_only"
        assert capture_policy(conn, cfg.sources, "nonexistent").screenshot_policy == "manual_only"

    def test_manual_only_refuses_files_and_extraction(self, conn, store, cfg):
        res = intake.start_intake(conn, store, cfg, "https://www.storagetreasures.com/auctions/2518843",
                                  [("s.png", PNG, "screenshot")], "colorado_springs", now=T0)
        assert any("NOT stored" in n for n in res.notices)
        assert conn.execute("SELECT COUNT(*) FROM raw_captures").fetchone()[0] == 0
        ex = FakeExtractor(**EXTRACTED)
        assert intake.run_extraction(conn, store, cfg, res.intake_id, ex, now=T0) is None
        assert ex.calls == 0  # the extractor is never called, even if the UI were bypassed

    def test_policy_event_overrides_config_and_is_permanent(self, conn, cfg):
        with pytest.raises(ValueError, match="record why"):
            set_policy(conn, cfg.sources, "bid13", "allowed", "terms_reviewed_no_restriction", " ", T0)
        set_policy(conn, cfg.sources, "bid13", "allowed", "terms_reviewed_no_restriction", "read ToS 10/5", T0)
        p = capture_policy(conn, cfg.sources, "bid13")
        assert p.screenshot_policy == "allowed" and "read ToS" in p.reason
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM source_policy_events")

    def test_intake_remembers_policy_at_capture_time(self, conn, store, cfg):
        """Revoking permission later doesn't let an old intake be re-extracted."""
        set_policy(conn, cfg.sources, "bid13", "allowed", "written_permission", "email", T0)
        res = intake.start_intake(conn, store, cfg, "https://bid13.com/auctions/123456", [("s.png", PNG, "screenshot")],
                                  "colorado_springs", now=T0)
        assert intake.intake(conn, res.intake_id)["screenshot_policy"] == "allowed"


class TestConfirm:
    def test_provenance_labels(self, conn, store, cfg):
        res = allowed_intake(conn, store, cfg)
        intake.run_extraction(conn, store, cfg, res.intake_id, FakeExtractor(**EXTRACTED), now=T0)
        defaults = intake.form_defaults(conn, cfg, res.intake_id)
        form = {k: v["display"] for k, v in defaults.items()}
        form["current_bid"] = "90"  # corrected by the user
        form["city"] = "Colorado Springs"  # typed by the user
        aid, oid, warnings = intake.confirm_intake(conn, store, cfg, res.intake_id, form, {"bid_count"},
                                                   now="2026-10-05T18:01:00.000000Z")
        o = conn.execute("SELECT * FROM auction_observations WHERE id = ?", (oid,)).fetchone()
        meta = json.loads(o["field_meta_json"])
        assert meta["unit_size"]["label"] == "EXTRACTED_CONFIRMED" and meta["unit_size"]["confidence"] == 0.95
        assert meta["current_bid"]["label"] == "USER_ENTERED" and meta["current_bid"]["extracted_value_was"] == 8500
        assert meta["bid_count"]["confidence"] == 0.5 and meta["bid_count"]["marked_unsure"]
        assert meta["external_id"]["label"] == "URL_DERIVED"
        assert (o["current_bid_cents"], o["width_ft"], o["length_ft"], o["size_bucket"]) == (9000, 5, 10, "5x10")
        assert o["ends_at"] == "2026-10-10T20:00:00.000000Z"
        assert o["observed_at"] == T0 and o["recorded_at"] == "2026-10-05T18:01:00.000000Z"
        # blank fields are absent; platform defaults are never stored as observations
        assert o["buyer_premium_rate"] is None and o["cleaning_deposit_cents"] is None
        # the confirmed form is stored as raw evidence
        form_rc = conn.execute("SELECT * FROM raw_captures WHERE id = ?", (o["raw_capture_id"],)).fetchone()
        assert form_rc["capture_method"] == "review_form"
        assert json.loads(store.get(form_rc["content_sha256"]))["fields"]["current_bid"] == "90"

    def test_manual_entry_on_manual_only_source(self, conn, store, cfg):
        res = intake.start_intake(conn, store, cfg, "https://www.storagetreasures.com/auctions/2518843", [],
                                  "colorado_springs", now=T0)
        aid, oid, w = intake.confirm_intake(conn, store, cfg, res.intake_id,
                                            {"unit_size": "5x5", "current_bid": "$40", "ends_at": "2026-10-09 18:00"},
                                            now=T0)
        o = conn.execute("SELECT * FROM auction_observations WHERE id = ?", (oid,)).fetchone()
        meta = json.loads(o["field_meta_json"])
        assert {m["label"] for k, m in meta.items() if k not in ("size_bucket", "external_id", "url")} == {"USER_ENTERED"}
        assert o["ends_at"] == "2026-10-10T00:00:00.000000Z"  # 18:00 MDT

    def test_bad_values_rejected_without_writing(self, conn, store, cfg):
        res = allowed_intake(conn, store, cfg)
        with pytest.raises(intake.IntakeError) as e:
            intake.confirm_intake(conn, store, cfg, res.intake_id, {"unit_size": "big", "current_bid": "lots"}, now=T0)
        assert len(e.value.errors) == 2
        assert conn.execute("SELECT COUNT(*) FROM auction_observations").fetchone()[0] == 0

    def test_confirm_twice_refused(self, conn, store, cfg):
        res = allowed_intake(conn, store, cfg)
        intake.confirm_intake(conn, store, cfg, res.intake_id, {"unit_size": "5x5"}, now=T0)
        with pytest.raises(intake.IntakeError, match="already confirmed"):
            intake.confirm_intake(conn, store, cfg, res.intake_id, {"unit_size": "5x5"}, now=T0)


class TestDuplicates:
    def test_same_auction_id_becomes_new_snapshot(self, conn, store, cfg):
        r1 = allowed_intake(conn, store, cfg)
        a1, _, _ = intake.confirm_intake(conn, store, cfg, r1.intake_id, {"current_bid": "50"}, now=T0)
        r2 = allowed_intake(conn, store, cfg, url="https://example.com/auction/482913?utm_source=x", files=())
        assert any("Already tracking" in n for n in r2.notices)
        a2, _, _ = intake.confirm_intake(conn, store, cfg, r2.intake_id, {"current_bid": "65"},
                                         now="2026-10-06T18:00:00.000000Z")
        assert a1 == a2
        assert [r[0] for r in conn.execute("SELECT current_bid_cents FROM auction_observations ORDER BY id")] == [5000, 6500]

    def test_identical_screenshot_skipped(self, conn, store, cfg):
        allowed_intake(conn, store, cfg)
        r2 = allowed_intake(conn, store, cfg, url="https://example.com/auction/999999")
        assert any("identical file" in n for n in r2.notices)
        assert intake.intake_files(conn, r2.intake_id) == []

    def test_cross_listing_warning(self, conn, store, cfg):
        f = {"facility_name": "Example Storage", "unit_label": "B12", "ends_at": "2026-10-10 14:00"}
        r1 = allowed_intake(conn, store, cfg, files=())
        intake.confirm_intake(conn, store, cfg, r1.intake_id, f, now=T0)
        r2 = intake.start_intake(conn, store, cfg, "https://www.storagetreasures.com/auctions/2518843", [],
                                 "colorado_springs", now=T0)
        _, _, warnings = intake.confirm_intake(conn, store, cfg, r2.intake_id, f | {"ends_at": "2026-10-10 15:30"},
                                               now=T0)
        assert any("Possible duplicate" in w for w in warnings)

    def test_url_without_id_gets_stable_hash_id(self, conn, store, cfg):
        r1 = allowed_intake(conn, store, cfg, url="https://example.com/listing/abc", files=())
        a1, _, w = intake.confirm_intake(conn, store, cfg, r1.intake_id, {}, now=T0)
        assert any("identified by its URL" in x for x in w)
        r2 = allowed_intake(conn, store, cfg, url="https://example.com/listing/abc/", files=())
        a2, _, _ = intake.confirm_intake(conn, store, cfg, r2.intake_id, {}, now=T0)
        assert a1 == a2


def decided_auction(conn, store, cfg, visible=250000):
    r = allowed_intake(conn, store, cfg, files=())
    aid, _, _ = intake.confirm_intake(conn, store, cfg, r.intake_id,
                                      {"unit_size": "5x5", "current_bid": "40", "ends_at": "2026-10-10 14:00"}, now=T0)
    est = QuickEstimate(visible, 5000, 60000, "light", "car_suv", 0.8, ("TOOLS",))
    res = paper.decide(conn, cfg, aid, est, strategy_key="quick_v1", now="2026-10-06T12:00:00.000000Z",
                       choice="PAPER_BID")
    return aid, res


class TestResults:
    def test_sold_before_end_refused(self, conn, store, cfg):
        aid, _ = decided_auction(conn, store, cfg)
        with pytest.raises(intake.IntakeError, match="hasn't passed"):
            intake.record_result(conn, store, cfg, aid, "sold", "150", now="2026-10-08T12:00:00.000000Z")

    def test_won_result_is_simulated_and_estimated(self, conn, store, cfg):
        aid, res = decided_auction(conn, store, cfg)
        mb = res.underwriting.max_bid_cents
        summary = intake.record_result(conn, store, cfg, aid, "sold", f"{(mb - 5000) // 100}", "11",
                                       now="2026-10-11T12:00:00.000000Z")
        d = summary["decisions"][0]
        assert d["result"] == "WON" and d["max_bid_minus_price_cents"] == 5000
        assert d["acquisition_price_conservative_cents"] == mb
        assert d["estimated_cash_profit_conservative_cents"] <= d["estimated_cash_profit_neutral_cents"]

    def test_lost_and_margin(self, conn, store, cfg):
        aid, res = decided_auction(conn, store, cfg)
        mb = res.underwriting.max_bid_cents
        d = intake.record_result(conn, store, cfg, aid, "sold", f"{(mb + 10000) // 100}",
                                 now="2026-10-11T12:00:00.000000Z")["decisions"][0]
        assert d["result"] == "LOST" and d["max_bid_minus_price_cents"] < 0
        assert "estimated_cash_profit_conservative_cents" not in d

    def test_cancelled_early_is_void(self, conn, store, cfg):
        aid, _ = decided_auction(conn, store, cfg)
        d = intake.record_result(conn, store, cfg, aid, "cancelled", now="2026-10-08T12:00:00.000000Z")["decisions"][0]
        assert d["result"] == "VOID"

    def test_unknown_result_stays_unsettled(self, conn, store, cfg):
        aid, _ = decided_auction(conn, store, cfg)
        d = intake.record_result(conn, store, cfg, aid, "unknown", now="2026-10-11T12:00:00.000000Z")["decisions"][0]
        assert d["result"] is None
        assert conn.execute("SELECT status FROM auction_observations ORDER BY id DESC").fetchone()[0] == "closed"

    def test_price_only_for_sold(self, conn, store, cfg):
        aid, _ = decided_auction(conn, store, cfg)
        with pytest.raises(intake.IntakeError, match="only applies"):
            intake.record_result(conn, store, cfg, aid, "cancelled", "100", now="2026-10-11T12:00:00.000000Z")
