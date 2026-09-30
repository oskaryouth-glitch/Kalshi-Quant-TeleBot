"""SQLite connection and migrations.

SQLite is deliberate: one file, zero cost, trivially backed up, and it enforces
the integrity rules we care about (CHECK constraints, append-only triggers,
STRICT typing). Move to Postgres only if concurrency ever demands it.

Connections run in autocommit mode; multi-statement writes use
``transaction()`` so they are all-or-nothing.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator

from .timeutil import now_ts

# Every table here rejects UPDATE and DELETE. Corrections are new rows.
APPEND_ONLY_TABLES = (
    "sources",
    "raw_captures",
    "auctions",
    "auction_observations",
    "bid_events",
    "images",
    "model_versions",
    "paper_decisions",
    "paper_settlements",
)


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    if conn.in_transaction:  # nested: let the outer transaction own commit
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _migration_files() -> list[tuple[int, str, str]]:
    out = []
    for entry in resources.files("lockerlab.migrations").iterdir():
        if entry.name.endswith(".sql"):
            out.append((int(entry.name.split("_", 1)[0]), entry.name, entry.read_text()))
    return sorted(out)


def _append_only_triggers(table: str) -> list[str]:
    return [
        f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} BEGIN "
        f"SELECT RAISE(ABORT, 'append-only table {table}: UPDATE forbidden'); END;",
        f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} BEGIN "
        f"SELECT RAISE(ABORT, 'append-only table {table}: DELETE forbidden'); END;",
    ]


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               version INTEGER PRIMARY KEY, name TEXT NOT NULL,
               sha256 TEXT NOT NULL, applied_at TEXT NOT NULL) STRICT"""
    )
    applied = {
        r["version"]: r["sha256"]
        for r in conn.execute("SELECT version, sha256 FROM schema_migrations")
    }
    for version, name, sql in _migration_files():
        digest = hashlib.sha256(sql.encode()).hexdigest()
        if version in applied:
            if applied[version] != digest:
                raise RuntimeError(
                    f"migration {name} was edited after being applied; "
                    "add a new migration instead of changing an old one"
                )
            continue
        stmts = _split_sql(sql)
        if version == 1:
            for t in APPEND_ONLY_TABLES:
                stmts.extend(_append_only_triggers(t))
        with transaction(conn):
            for stmt in stmts:
                conn.execute(stmt)
            conn.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                (version, name, digest, now_ts()),
            )


def _split_sql(script: str) -> list[str]:
    """Split a migration into statements. Strips ``--`` comments, so migration
    files must not contain ``--`` inside string literals."""
    stmts, buf = [], []
    for line in script.splitlines():
        code = line.split("--", 1)[0].rstrip()
        if not code.strip():
            continue
        buf.append(code)
        joined = "\n".join(buf)
        if sqlite3.complete_statement(joined):
            stmts.append(joined)
            buf = []
    if buf:
        raise ValueError("unterminated SQL statement in migration")
    return stmts
