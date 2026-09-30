"""End-to-end CLI flow and the automated-collection gate."""

import pytest

from lockerlab.cli import ESTIMATE_TEMPLATE, main
from lockerlab.collectors.base import CollectionNotAuthorized, PoliteClient, assert_collection_authorized


def run(home, *args):
    return main(["--home", str(home), *args])


def test_end_to_end(home, tmp_path, capsys):
    assert run(home, "init") == 0
    cap = tmp_path / "cap.csv"
    assert run(home, "template", "capture", "--out", str(cap)) == 0
    # The template's example auction ends 2026-10-04; move it far into the
    # future so a FORWARD decision made "now" (wall clock) is still valid.
    cap.write_text(cap.read_text().replace("2026-10-04 14:00", "2099-01-01 12:00")
                   .replace("2026-10-01 19:30", "2026-01-01 12:00"))
    assert run(home, "import", str(cap), "--market", "colorado_springs") == 0
    assert run(home, "import", str(cap), "--market", "colorado_springs") == 0  # idempotent
    assert "already imported" in capsys.readouterr().out

    est = tmp_path / "est.yaml"
    est.write_text(ESTIMATE_TEMPLATE)
    assert run(home, "underwrite", str(est)) == 0
    out = capsys.readouterr().out
    assert "MAXIMUM RECOMMENDED PAPER BID" in out and "DRY RUN" in out

    assert run(home, "decide", str(est)) == 0
    assert "RECORDED: paper decision #1" in capsys.readouterr().out
    assert run(home, "settle") == 0
    assert "awaiting_outcome" in capsys.readouterr().out
    for which in ("market", "paper", "coverage", "assumptions"):
        assert run(home, "report", which) == 0
    assert run(home, "auctions", "--open") == 0
    assert "EXAMPLE-123456" in capsys.readouterr().out


def test_bad_import_exit_code(home, tmp_path, capsys):
    p = tmp_path / "bad.csv"
    p.write_text("source,external_id,status\nstoragetreasures,X,flying\n")
    assert run(home, "import", str(p), "--market", "colorado_springs") == 2
    assert "IMPORT REJECTED" in capsys.readouterr().err


def test_decide_unknown_auction_refused(home, tmp_path, capsys):
    run(home, "init")
    est = tmp_path / "est.yaml"
    est.write_text(ESTIMATE_TEMPLATE)
    assert run(home, "decide", str(est)) == 2
    assert "REFUSED" in capsys.readouterr().err


class TestCollectionGate:
    SOURCES = {
        "st": {"automated_collection": "prohibited"},
        "b13": {"automated_collection": "unknown"},
        "ok": {"automated_collection": "authorized"},
    }

    @pytest.mark.parametrize("key", ["st", "b13", "missing"])
    def test_refuses_unauthorized(self, key):
        with pytest.raises(CollectionNotAuthorized):
            assert_collection_authorized(self.SOURCES, key)
        with pytest.raises(CollectionNotAuthorized):
            PoliteClient(self.SOURCES, key, "lockerlab-research/0.1")

    def test_authorized_allowed_but_must_not_impersonate_browser(self):
        PoliteClient(self.SOURCES, "ok", "lockerlab-research/0.1 (+contact)")
        with pytest.raises(ValueError):
            PoliteClient(self.SOURCES, "ok", "Mozilla/5.0 Chrome")

    def test_repo_config_authorizes_nothing(self, cfg):
        for key in cfg.sources:
            with pytest.raises(CollectionNotAuthorized):
                assert_collection_authorized(cfg.sources, key)
