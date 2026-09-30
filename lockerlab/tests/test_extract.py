"""Screenshot extraction: parsing, missing/ambiguous fields, time zones, the
Claude client wrapper, and URL recognition."""

import json
from types import SimpleNamespace

import pytest

from lockerlab.extract import FIELDS, ClaudeExtractor, media_type_for, normalize, parse_field
from lockerlab.platforms import parse_url

TZ = "America/Denver"
CAP = "2026-10-05T18:00:00.000000Z"  # 12:00 MDT


def tx(**fields):
    t = {f: {"visible": False, "text": "", "confidence": 0, "evidence": ""} for f in FIELDS}
    for k, (text, conf) in fields.items():
        t[k] = {"visible": True, "text": text, "confidence": conf, "evidence": "screenshot 1"}
    return t


class TestParsing:
    @pytest.mark.parametrize("kind,text,value", [
        ("money", "Current Bid: $1,285.50", 128550),
        ("money", "$85", 8500),
        ("money", "85.00", 8500),
        ("int", "12 bids", 12),
        ("int", "Photo 1/8", 8),
        ("pct", "Buyer premium 15%", 0.15),
        ("pct", "18.5 %", 0.185),
        ("size", "Unit Size: 5' x 10'", [5.0, 10.0, None]),
        ("size", "10x15", [10.0, 15.0, None]),
        ("duration", "48 hours", 48),
        ("duration", "3 days to clean out", 72),
    ])
    def test_values(self, kind, text, value):
        assert parse_field(kind, text, TZ, CAP)[0] == value

    @pytest.mark.parametrize("kind,text", [("money", "no bids yet"), ("pct", "premium applies"),
                                           ("size", "large unit"), ("int", "many"), ("duration", "soon")])
    def test_unparseable_raises(self, kind, text):
        with pytest.raises(ValueError):
            parse_field(kind, text, TZ, CAP)


class TestTimes:
    def test_explicit_mdt(self):
        v, status, notes = parse_field("time", "Ends Oct 10, 2026 2:00 PM MDT", TZ, CAP)
        assert (v, status) == ("2026-10-10T20:00:00.000000Z", "found")

    def test_explicit_mst_after_dst_ends(self):
        # DST ends Nov 1 2026: a November time is UTC-7
        v, status, _ = parse_field("time", "11/05/2026 10:00 AM MST", TZ, CAP)
        assert v == "2026-11-05T17:00:00.000000Z" and status == "found"

    def test_no_zone_uses_market_zone_across_dst(self):
        assert parse_field("time", "Oct 30, 2026 10:00 AM", TZ, CAP)[0] == "2026-10-30T16:00:00.000000Z"  # MDT
        v, _, notes = parse_field("time", "Nov 2, 2026 10:00 AM", TZ, CAP)
        assert v == "2026-11-02T17:00:00.000000Z"  # MST
        assert any("no time zone" in n for n in notes)

    def test_missing_year_is_ambiguous_and_flagged(self):
        v, status, notes = parse_field("time", "Oct 10 2:00 PM", TZ, CAP)
        assert status == "ambiguous" and v == "2026-10-10T20:00:00.000000Z"
        assert any("no year" in n for n in notes)

    def test_missing_year_rolls_to_next_year(self):
        # Captured in late December, an end date of Jan 3 means next year.
        v, _, _ = parse_field("time", "Jan 3 2:00 PM", TZ, "2026-12-29T18:00:00.000000Z")
        assert v.startswith("2027-01-03")

    def test_countdown_is_inferred_from_capture_time(self):
        v, status, notes = parse_field("time", "2d 4h left", TZ, CAP)
        assert status == "inferred" and v == "2026-10-07T22:00:00.000000Z"

    def test_date_only_is_ambiguous(self):
        _, status, notes = parse_field("time", "10/10/2026", TZ, CAP)
        assert status == "ambiguous" and any("midnight" in n for n in notes)


class TestNormalize:
    def test_missing_fields_are_marked_not_guessed(self):
        out = normalize(tx(current_bid=("$85", 0.9)), TZ, CAP)
        assert out["current_bid"].value == 8500 and out["current_bid"].status == "found"
        assert out["buyer_premium_pct"].value is None and out["buyer_premium_pct"].status == "not_visible"
        assert out["cleaning_deposit"].confidence == 0.0

    def test_unparseable_text_kept_with_invalid_status(self):
        out = normalize(tx(current_bid=("No bids", 0.9)), TZ, CAP)
        assert out["current_bid"].value is None and out["current_bid"].status == "invalid"
        assert out["current_bid"].text == "No bids"

    def test_assumptions_cap_confidence(self):
        out = normalize(tx(ends_at=("Oct 10 2:00 PM", 0.99)), TZ, CAP)
        assert out["ends_at"].status == "ambiguous" and out["ends_at"].confidence == 0.5

    def test_visible_but_empty_is_not_visible(self):
        t = tx()
        t["unit_size"] = {"visible": True, "text": "  ", "confidence": 0.9, "evidence": "x"}
        assert normalize(t, TZ, CAP)["unit_size"].status == "not_visible"

    def test_garbage_transcription_does_not_crash(self):
        out = normalize({"current_bid": {"visible": True, "text": "$9", "confidence": "high"}}, TZ, CAP)
        assert out["current_bid"].value == 900 and out["current_bid"].confidence == 0.0
        assert normalize(None, TZ, CAP)["unit_size"].status == "not_visible"


class FakeClient:
    def __init__(self, resp):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._resp = resp

    def _create(self, **kw):
        self.calls.append(kw)
        return self._resp


def resp(stop="end_turn", text=None):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(stop_reason=stop, content=content, model="claude-opus-5-5",
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))


class TestClaudeExtractor:
    def test_ok_request_shape(self):
        client = FakeClient(resp(text=json.dumps(tx(current_bid=("$5", 1)))))
        r = ClaudeExtractor(client=client).extract([(b"\x89PNG", "image/png")], "ctx")
        assert r.status == "ok" and r.transcription["current_bid"]["text"] == "$5"
        kw = client.calls[0]
        assert kw["model"] == "claude-opus-5-5"
        assert kw["output_config"]["format"]["type"] == "json_schema"
        assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
        assert kw["messages"][0]["content"][1]["type"] == "image"

    def test_refusal(self):
        r = ClaudeExtractor(client=FakeClient(resp(stop="refusal"))).extract([], "ctx")
        assert r.status == "refused" and r.transcription is None

    def test_truncated_or_invalid_json(self):
        assert ClaudeExtractor(client=FakeClient(resp(stop="max_tokens", text="{"))).extract([], "c").status == "error"
        assert ClaudeExtractor(client=FakeClient(resp(text="not json"))).extract([], "c").status == "error"


def test_media_type_detection():
    assert media_type_for("a.png", b"\x89PNG\r\n\x1a\nxxxx") == "image/png"
    assert media_type_for("a.jpg", b"\xff\xd8\xff\xe0xx") == "image/jpeg"
    assert media_type_for("a.heic", b"\x00\x00\x00\x18ftypheicxxxx") == "image/heic"
    assert media_type_for("a.txt", b"hello") is None


class TestUrls:
    @pytest.mark.parametrize("url,source,ext", [
        ("https://www.storagetreasures.com/auctions/co/colorado-springs/2518843", "storagetreasures", "2518843"),
        ("storagetreasures.com/auction/2518843?utm_source=x", "storagetreasures", "2518843"),
        ("https://www.lockerfox.com/storage-auctions/us/colorado/colorado-springs/?auctionID=48213", "lockerfox", "48213"),
        ("https://bid13.com/auctions/123456-5x10-unit", "bid13", "123456"),
        ("https://www.example.com/lot?id=ABC-9", None, "ABC-9"),
    ])
    def test_recognised(self, url, source, ext):
        u = parse_url(url)
        assert (u.source_key, u.external_id) == (source, ext)

    def test_ambiguous_id_not_guessed(self):
        u = parse_url("https://www.storagetreasures.com/facility/93049/auction/2518843")
        assert u.external_id is None and "several numbers" in u.evidence

    def test_tracking_params_dropped(self):
        a = parse_url("https://www.storagetreasures.com/auctions/2518843?utm_campaign=z&fbclid=1").normalized_url
        b = parse_url("https://storagetreasures.com/auctions/2518843/").normalized_url
        assert a == b

    def test_not_a_url(self):
        assert parse_url("hello").normalized_url is None
