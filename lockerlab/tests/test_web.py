"""The desk web app, end to end through HTTP (FastAPI TestClient)."""

import json
import re

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lockerlab.db import connect  # noqa: E402
from lockerlab.web.app import create_app  # noqa: E402

from test_intake import EXTRACTED, PNG, FakeExtractor  # noqa: E402


@pytest.fixture
def app(home):
    clock = {"now": "2026-10-05T18:00:00.000000Z"}
    ex = FakeExtractor(**EXTRACTED)
    client = TestClient(create_app(home, extractor_factory=lambda cfg: ex, clock=lambda: clock["now"]))
    client.clock, client.extractor, client.db = clock, ex, home / "data" / "lockerlab.sqlite3"
    return client


def q(client, sql, *args):
    c = connect(client.db)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


EST = {"visible": "2500", "hidden_low": "50", "hidden_high": "600", "disposal": "light", "transport": "car_suv",
       "confidence": "80", "tags": ["TOOLS"]}


def capture_allowed(c, url="https://example.com/auction/482913"):
    r = c.post("/capture", data={"url": url, "source_key": "manual_other"},
               files=[("screenshots", ("s.png", PNG, "image/png"))], follow_redirects=False)
    assert r.status_code == 303
    iid = int(re.search(r"/capture/(\d+)", r.headers["location"]).group(1))
    return iid


def test_pages_render_empty(app):
    for path in ("/", "/capture", "/calibration", "/readiness", "/assumptions", "/sources"):
        r = app.get(path)
        assert r.status_code == 200, path
    assert "0</div>need an estimate" in app.get("/").text.replace("\n", "")


def test_full_daily_flow(app):
    iid = capture_allowed(app)
    assert app.extractor.calls == 1
    page = app.get(f"/capture/{iid}").text
    assert 'value="5x10"' in page and "read · 95%" in page and "not visible" in page
    assert 'value="482913"' in page  # auction ID prefilled from the URL
    form = {"unit_size": "5x10", "current_bid": "85", "bid_count": "7", "ends_at": "2026-10-10 14:00",
            "facility_name": "Example Storage", "city": "Colorado Springs", "external_id": "482913"}
    r = app.post(f"/capture/{iid}/confirm", data=form, follow_redirects=False)
    aid = int(re.search(r"/auction/(\d+)", r.headers["location"]).group(1))
    # calculate: shows numbers, records nothing
    r = app.post(f"/auction/{aid}/estimate", data=EST | {"action": "calculate"})
    assert "Model says" in r.text and "Economic profit" in r.text
    assert q(app, "SELECT COUNT(*) FROM paper_decisions")[0][0] == 0
    max_bid = int(re.search(r'name="paper_bid" value="(\d+)"', r.text).group(1))
    # decide
    r = app.post(f"/auction/{aid}/estimate", data=EST | {"action": "PAPER_BID", "paper_bid": str(max_bid)},
                 follow_redirects=False)
    assert r.status_code == 303
    d = q(app, "SELECT * FROM paper_decisions")[0]
    assert (d["decision"], d["paper_bid_cents"], d["strategy_key"]) == ("PAPER_BID", max_bid * 100, "quick_v1")
    desk = app.get("/").text
    assert "Most interesting" in desk and re.search(r'class="score">(\d+)', desk)
    # result after close
    app.clock["now"] = "2026-10-11T01:00:00.000000Z"
    # well below our max: at this price the increment is up to $25, and a win needs price + increment
    r = app.post(f"/auction/{aid}/result", data={"outcome": "sold", "winning_price": str(max_bid - 100),
                                                 "bid_count": "12"})
    assert 'banner bad' not in r.text, re.findall(r'banner bad">([^<]*)', r.text)
    assert "WON" in r.text and "SIMULATED win, ESTIMATED profit" in r.text
    assert q(app, "SELECT result FROM paper_settlements")[0][0] == "WON"
    meta = json.loads(q(app, "SELECT field_meta_json FROM auction_observations ORDER BY id")[0][0])
    assert meta["external_id"]["label"] == "URL_DERIVED"  # untouched prefill is not "user entered"


def test_paper_bid_above_max_refused_via_ui(app):
    iid = capture_allowed(app)
    r = app.post(f"/capture/{iid}/confirm", data={"unit_size": "5x5", "current_bid": "40",
                                                  "ends_at": "2026-10-10 14:00"}, follow_redirects=False)
    aid = int(re.search(r"/auction/(\d+)", r.headers["location"]).group(1))
    r = app.post(f"/auction/{aid}/estimate", data=EST | {"action": "PAPER_BID", "paper_bid": "99999"})
    assert "can&#39;t exceed" in r.text or "can't exceed" in r.text
    assert q(app, "SELECT COUNT(*) FROM paper_decisions")[0][0] == 0


def test_manual_only_source_through_ui(app):
    r = app.post("/capture", data={"url": "https://www.storagetreasures.com/auctions/2518843"},
                 files=[("screenshots", ("s.png", PNG, "image/png"))], follow_redirects=False)
    loc = r.headers["location"]
    page = app.get(loc).text
    assert "NOT stored" in page and "Manual only for storagetreasures" in page
    assert app.extractor.calls == 0
    assert q(app, "SELECT COUNT(*) FROM raw_captures")[0][0] == 0
    iid = int(re.search(r"/capture/(\d+)", loc).group(1))
    assert app.post(f"/capture/{iid}/extract", follow_redirects=False).status_code == 303
    assert app.extractor.calls == 0 and q(app, "SELECT COUNT(*) FROM extractions")[0][0] == 0


def test_triage_pass_and_calibration_reasons(app):
    iid = capture_allowed(app)
    r = app.post(f"/capture/{iid}/confirm", data={"unit_size": "10x20", "ends_at": "2026-10-10 14:00"},
                 follow_redirects=False)
    aid = int(re.search(r"/auction/(\d+)", r.headers["location"]).group(1))
    r = app.post(f"/auction/{aid}/triage", data={"action": "PASS"})
    assert "pick at least one reason" in r.text
    app.post(f"/auction/{aid}/triage", data={"action": "PASS", "pass_tags": ["TOO_LARGE"]})
    assert "Too Large" in app.get("/calibration").text


def test_assumption_panel_creates_set_and_keeps_old_decisions(app):
    iid = capture_allowed(app)
    r = app.post(f"/capture/{iid}/confirm", data={"unit_size": "5x5", "current_bid": "40",
                                                  "ends_at": "2026-10-10 14:00"}, follow_redirects=False)
    aid = int(re.search(r"/auction/(\d+)", r.headers["location"]).group(1))
    app.post(f"/auction/{aid}/estimate", data=EST | {"action": "WATCH"})
    before = [tuple(x) for x in q(app, "SELECT * FROM paper_decisions")]
    page = app.get("/assumptions").text
    form = {}
    for name, value in re.findall(r'name="(v::[^"]+)" value="([^"]*)"', page):
        form[name] = value
    for name in re.findall(r'<select name="(s::[^"]+)"', page):
        sel = re.search(rf'<select name="{re.escape(name)}">(.*?)</select>', page, re.S).group(1)
        form[name] = re.search(r'<option value="(\w+)" selected', sel).group(1)
    form["v::underwriting.labor.minutes_per_sale"] = "40"
    form["s::underwriting.labor.minutes_per_sale"] = "USER"
    r = app.post("/assumptions", data=form | {"note": "slower"}, follow_redirects=False)
    assert "saved=1" in r.headers["location"]
    assert [tuple(x) for x in q(app, "SELECT * FROM paper_decisions")] == before
    overrides = json.loads(q(app, "SELECT overrides_json FROM assumption_sets")[0][0])
    assert list(overrides) == ["underwriting.labor.minutes_per_sale"]
    assert "Retrospective" in app.get("/calibration").text


def test_source_policy_change_needs_note(app):
    r = app.post("/sources/bid13/policy", data={"policy": "allowed", "basis": "other", "note": " "},
                 follow_redirects=False)
    assert "error" in r.headers["location"]
    app.post("/sources/bid13/policy", data={"policy": "allowed", "basis": "written_permission", "note": "email 10/7"})
    assert q(app, "SELECT screenshot_policy FROM source_policy_events")[0][0] == "allowed"


def test_evidence_only_serves_images(app):
    iid = capture_allowed(app)
    img = q(app, "SELECT raw_capture_id FROM intake_files")[0][0]
    assert app.get(f"/evidence/{img}").content == PNG
    app.post(f"/capture/{iid}/confirm", data={"unit_size": "5x5"})
    form_id = q(app, "SELECT id FROM raw_captures WHERE capture_method = 'review_form'")[0][0]
    assert app.get(f"/evidence/{form_id}").status_code == 404


def test_readiness_logging(app):
    r = app.post("/readiness/check", data={"check_key": "disposal_called", "status": "done", "note": ""},
                 follow_redirects=False)
    assert "error" in r.headers["location"]
    app.post("/readiness/check", data={"check_key": "disposal_called", "status": "done",
                                       "note": "Woodmen: 250 lb = $54"})
    app.post("/readiness/selling", data={"item": "lamp", "platform": "FB", "listing_minutes": "12",
                                         "selling_minutes": "30", "sold": "1", "price": "25"})
    page = app.get("/readiness").text
    assert "Woodmen: 250 lb = $54" in page and "lamp" in page
    main = page.split('<footer')[0].lower().replace("never recommends buying", "")
    assert "buy" not in main
