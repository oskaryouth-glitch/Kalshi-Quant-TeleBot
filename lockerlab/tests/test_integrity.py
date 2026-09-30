"""Data-integrity tests: append-only storage, raw evidence, capture validation."""

import sqlite3

import pytest

from lockerlab.capture import CaptureError, import_csv, import_photos, template_csv
from lockerlab.db import APPEND_ONLY_TABLES, connect
from lockerlab.rawstore import CorruptEvidence, RawStore

NOW = "2026-10-02T00:00:00.000000Z"
ROW = "storagetreasures,A1,2026-10-01 10:00,active,Colorado Springs,5x10,$45,,2026-10-04 14:00,18,100,6,,6"


class TestAppendOnly:
    def test_every_table_rejects_update_and_delete(self, conn, store, cfg, write_csv):
        import_csv(conn, store, cfg, write_csv(ROW), "colorado_springs", now=NOW)
        for table in ("sources", "raw_captures", "auctions", "auction_observations"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                conn.execute(f"UPDATE {table} SET rowid = rowid")
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                conn.execute(f"DELETE FROM {table}")

    def test_triggers_exist_for_all_tables(self, conn):
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        for t in APPEND_ONLY_TABLES:
            assert f"{t}_no_update" in names and f"{t}_no_delete" in names

    def test_cannot_record_observation_before_it_was_seen(self, conn, store, cfg, write_csv):
        import_csv(conn, store, cfg, write_csv(ROW), "colorado_springs", now=NOW)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO auction_observations (auction_id, raw_capture_id, observed_at, recorded_at, "
                "parser_version, status, raw_fields_json, field_meta_json) "
                "VALUES (1, 1, '2026-10-03T00:00:00.000000Z', '2026-10-02T00:00:00.000000Z', 'x', 'active', '{}', '{}')"
            )

    def test_edited_migration_is_detected(self, home):
        path = home / "data" / "m.sqlite3"
        c = connect(path)
        c.execute("DELETE FROM schema_migrations")  # not append-only-protected
        c.execute("INSERT INTO schema_migrations VALUES (1, '001_init.sql', 'bogus', 'x')")
        c.close()
        with pytest.raises(RuntimeError, match="edited after being applied"):
            connect(path)


class TestRawStore:
    def test_roundtrip_and_idempotent(self, tmp_path):
        s = RawStore(tmp_path)
        sha, rel = s.put(b"hello")
        assert s.put(b"hello") == (sha, rel)
        assert s.get(sha) == b"hello"

    def test_tamper_detected(self, tmp_path):
        s = RawStore(tmp_path)
        sha, rel = s.put(b"hello")
        p = tmp_path / rel
        p.chmod(0o644)
        p.write_bytes(b"HELLO")
        with pytest.raises(CorruptEvidence):
            s.get(sha)


class TestCapture:
    def test_import_creates_observation_with_provenance(self, conn, store, cfg, write_csv):
        res = import_csv(conn, store, cfg, write_csv(ROW), "colorado_springs", now=NOW)
        assert (res.observations, res.new_auctions) == (1, 1)
        o = conn.execute("SELECT * FROM auction_observations").fetchone()
        assert o["current_bid_cents"] == 4500
        assert o["buyer_premium_rate"] == pytest.approx(0.18)
        assert (o["width_ft"], o["length_ft"], o["size_bucket"]) == (5, 10, "5x10")
        # 10:00 Mountain Daylight Time = 16:00 UTC
        assert o["observed_at"] == "2026-10-01T16:00:00.000000Z"
        assert o["ends_at"] == "2026-10-04T20:00:00.000000Z"
        assert '"current_bid":"$45"' in o["raw_fields_json"]
        assert '"size_bucket":{"confidence":1.0,"label":"INFERRED"}' in o["field_meta_json"]
        raw = conn.execute("SELECT * FROM raw_captures").fetchone()
        assert store.get(raw["content_sha256"]).startswith(b"source,")

    def test_reimport_is_noop(self, conn, store, cfg, write_csv):
        p = write_csv(ROW)
        import_csv(conn, store, cfg, p, "colorado_springs", now=NOW)
        assert import_csv(conn, store, cfg, p, "colorado_springs", now=NOW).already_imported
        assert conn.execute("SELECT COUNT(*) FROM auction_observations").fetchone()[0] == 1

    def test_second_snapshot_appends(self, conn, store, cfg, write_csv):
        import_csv(conn, store, cfg, write_csv(ROW), "colorado_springs", now=NOW)
        later = ROW.replace("2026-10-01 10:00", "2026-10-01 18:00").replace("$45", "$80")
        import_csv(conn, store, cfg, write_csv(later), "colorado_springs", now=NOW)
        bids = [r[0] for r in conn.execute("SELECT current_bid_cents FROM auction_observations ORDER BY id")]
        assert bids == [4500, 8000]

    def test_bad_file_writes_nothing(self, conn, store, cfg, write_csv):
        bad = ROW.replace("$45", "forty")
        with pytest.raises(CaptureError) as e:
            import_csv(conn, store, cfg, write_csv(ROW, bad), "colorado_springs", now=NOW)
        assert "line 3" in str(e.value)
        assert conn.execute("SELECT COUNT(*) FROM auction_observations").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM raw_captures").fetchone()[0] == 0

    @pytest.mark.parametrize("mutate,msg", [
        (lambda r: r.replace("active", "sold"), "requires final_price"),
        (lambda r: r.replace(",6,,6", ",6,$100,6"), "final_price given"),
        (lambda r: r.replace("storagetreasures", "nosuchsite"), "unknown source"),
        (lambda r: r.replace("2026-10-01 10:00", "2027-01-01 10:00"), "in the future"),
        (lambda r: r.replace(",18,", ",0.18,"), "ambiguous percent"),
        (lambda r: r.replace("5x10", "big"), "unrecognised unit size"),
        (lambda r: r.replace("active", "won"), "status must be"),
    ])
    def test_validation(self, conn, store, cfg, write_csv, mutate, msg):
        with pytest.raises(CaptureError, match=msg):
            import_csv(conn, store, cfg, write_csv(mutate(ROW)), "colorado_springs", now=NOW)

    def test_extra_values_rejected(self, conn, store, cfg, write_csv):
        with pytest.raises(CaptureError, match="more values than columns"):
            import_csv(conn, store, cfg, write_csv(ROW + ",totes, bike"), "colorado_springs", now=NOW)

    def test_refuses_occupant_names(self, conn, store, cfg, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text("source,external_id,status,tenant_name\nstoragetreasures,A1,active,Jane Doe\n")
        with pytest.raises(CaptureError, match="personal names"):
            import_csv(conn, store, cfg, p, "colorado_springs", now=NOW)

    def test_unknown_column_rejected(self, conn, store, cfg, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text("source,external_id,status,curent_bid\nstoragetreasures,A1,active,5\n")
        with pytest.raises(CaptureError, match="unknown columns"):
            import_csv(conn, store, cfg, p, "colorado_springs", now=NOW)

    def test_blank_observed_at_defaults_to_import_time(self, conn, store, cfg, write_csv):
        res = import_csv(conn, store, cfg, write_csv(ROW.replace("2026-10-01 10:00", "")),
                         "colorado_springs", now=NOW)
        assert conn.execute("SELECT observed_at FROM auction_observations").fetchone()[0] == NOW
        assert any("defaulted" in w for w in res.warnings)

    def test_template_imports_cleanly(self, conn, store, cfg, tmp_path):
        p = tmp_path / "t.csv"
        p.write_text(template_csv())
        assert import_csv(conn, store, cfg, p, "colorado_springs",
                          now="2026-10-03T00:00:00.000000Z").observations == 1

    def test_photos(self, conn, store, cfg, write_csv, tmp_path):
        import_csv(conn, store, cfg, write_csv(ROW), "colorado_springs", now=NOW)
        img = tmp_path / "p1.jpg"
        img.write_bytes(b"\xff\xd8fakejpeg")
        assert import_photos(conn, store, "storagetreasures", "A1", "2026-10-01T16:00:00.000000Z",
                             [img], now=NOW) == (1, 0)
        assert import_photos(conn, store, "storagetreasures", "A1", "2026-10-01T16:00:00.000000Z",
                             [img], now=NOW) == (0, 1)
