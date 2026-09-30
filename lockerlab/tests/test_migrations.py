"""Upgrading a real v1 database must preserve every row and the audit guarantees."""

import sqlite3

import pytest

from lockerlab.capture import import_csv, register_sources
from lockerlab.db import APPEND_ONLY_TABLES, connect
from lockerlab.rawstore import RawStore

ROW = "storagetreasures,A1,2026-10-01 10:00,active,Colorado Springs,5x10,$45,,2026-10-04 14:00,18,100,6,,6"


def test_v1_database_upgrades_without_losing_rows(home, cfg, write_csv):
    path = home / "data" / "v1.sqlite3"
    c = connect(path, migrate_upto=1)
    register_sources(c, cfg)
    import_csv(c, RawStore(home / "data" / "raw"), cfg, write_csv(ROW), "colorado_springs",
               now="2026-10-02T00:00:00.000000Z")
    before = [tuple(r) for r in c.execute("SELECT * FROM raw_captures ORDER BY id")]
    obs_before = [tuple(r) for r in c.execute("SELECT * FROM auction_observations ORDER BY id")]
    c.close()

    c = connect(path)  # applies 002 (raw_captures rebuild) and 003
    assert [tuple(r) for r in c.execute("SELECT * FROM raw_captures ORDER BY id")] == before
    assert [tuple(r) for r in c.execute("SELECT * FROM auction_observations ORDER BY id")] == obs_before
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    # the rebuilt table is append-only again, and accepts the new capture methods
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        c.execute("DELETE FROM raw_captures")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        c.execute("UPDATE raw_captures SET notes = 'x'")
    c.execute("INSERT INTO raw_captures (source_key, capture_method, recorded_at, content_sha256, content_path,"
              " content_type, byte_size) VALUES ('storagetreasures', 'screenshot', 'x', 'y', 'z', 'image/png', 1)")
    # observations still reference raw_captures correctly
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO auction_observations (auction_id, raw_capture_id, observed_at, recorded_at,"
                  " parser_version, status, raw_fields_json, field_meta_json) VALUES (1, 999, 'a', 'b', 'p',"
                  " 'active', '{}', '{}')")


def test_every_table_is_append_only(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    missing = names - set(APPEND_ONLY_TABLES) - {"schema_migrations"}
    assert not missing, f"tables without append-only triggers: {missing}"
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    for t in APPEND_ONLY_TABLES:
        assert {f"{t}_no_update", f"{t}_no_delete"} <= triggers
