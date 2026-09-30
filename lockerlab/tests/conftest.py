import shutil
from pathlib import Path

import pytest

from lockerlab.capture import register_sources
from lockerlab.config import Config
from lockerlab.db import connect
from lockerlab.rawstore import RawStore

REPO_CONFIG = Path(__file__).resolve().parents[1] / "config"


@pytest.fixture
def home(tmp_path):
    shutil.copytree(REPO_CONFIG, tmp_path / "config")
    (tmp_path / "data").mkdir()
    return tmp_path


@pytest.fixture
def cfg(home):
    return Config.load(home / "config")


@pytest.fixture
def conn(home, cfg):
    c = connect(home / "data" / "test.sqlite3")
    register_sources(c, cfg)
    yield c
    c.close()


@pytest.fixture
def store(home):
    return RawStore(home / "data" / "raw")


HEADER = ("source,external_id,observed_at,status,city,unit_size,current_bid,opening_bid,ends_at,"
          "buyer_premium_pct,cleaning_deposit,photo_count,final_price,distance_miles\n")


@pytest.fixture
def write_csv(tmp_path):
    counter = {"n": 0}

    def _write(*rows: str) -> Path:
        counter["n"] += 1
        p = tmp_path / f"capture_{counter['n']}.csv"
        p.write_text(HEADER + "".join(r + "\n" for r in rows))
        return p

    return _write
