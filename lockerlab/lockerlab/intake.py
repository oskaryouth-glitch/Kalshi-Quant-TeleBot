"""Capture workflow: URL + screenshots -> extraction proposal -> human review ->
immutable observation. Also result capture after an auction closes.

Audit rules this module enforces:
  * Screenshots/photos are stored (and shown to the extractor) only for
    sources whose capture policy is 'allowed'. For manual-only sources the
    files are refused, with the reason shown, and the form is filled by hand.
  * An extraction is a proposal. Only the fields you confirm become an
    observation, and each keeps its label, confidence and evidence:
      EXTRACTED_CONFIRMED  extractor value you accepted unchanged
      USER_ENTERED         you typed or corrected it (from the page you viewed)
      URL_DERIVED          taken from the URL you pasted
    Blank fields are simply absent: platform defaults (e.g. an 18% premium)
    are applied later by underwriting and are never written as observations.
  * The confirmation form itself is stored as raw evidence.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import timedelta

from .capture import register_sources
from .config import Config, canonical_json
from .db import transaction
from .economics import CostPolicy, Scenario, evaluate
from .extract import MAX_IMAGE_BYTES, PROMPT_VERSION, SUPPORTED_MEDIA, Extractor, media_type_for, normalize, \
    parse_field
from .labels import Label
from .money import parse_dollars
from .paper import settle_all
from .pit import TERMINAL_STATUSES, find_auction
from .platforms import capture_policy, parse_url
from .rawstore import RawStore
from .timeutil import from_ts, now_ts, parse_user_time, to_ts
from .units import size_bucket

PARSER_VERSION = "review_form_v1"


class IntakeError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class IntakeResult:
    intake_id: int
    notices: list[str] = field(default_factory=list)


def _store_file(conn, store: RawStore, source_key: str, data: bytes, method: str, ctype: str, now: str,
                url: str | None = None, notes: str | None = None) -> int:
    sha, rel = store.put(data)
    return conn.execute(
        """INSERT INTO raw_captures (source_key, source_url, capture_method, recorded_at, content_sha256,
               content_path, content_type, byte_size, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_key, url, method, now, sha, rel, ctype, len(data), notes),
    ).lastrowid


def start_intake(conn: sqlite3.Connection, store: RawStore, cfg: Config, url: str,
                 files: list[tuple[str, bytes, str]], market_key: str, source_key: str | None = None,
                 now: str | None = None) -> IntakeResult:
    """Record what you supplied. ``files``: (filename, bytes, role) with role
    'screenshot' or 'auction_photo'."""
    now = now or now_ts()
    cfg.market(market_key)
    register_sources(conn, cfg)
    info = parse_url(url)
    src = source_key or info.source_key
    if not src:
        raise IntakeError([f"Couldn't tell the auction site from the URL ({info.evidence}). Pick the platform."])
    if src not in cfg.sources:
        raise IntakeError([f"Unknown platform {src!r}."])
    notices: list[str] = []
    if info.source_key and source_key and info.source_key != source_key:
        notices.append(f"URL looks like {info.source_key} but you chose {source_key}; using your choice.")
    policy = capture_policy(conn, cfg.sources, src)
    auction_id = find_auction(conn, src, info.external_id) if info.external_id else None
    if auction_id:
        notices.append("Already tracking this auction: confirming adds a new snapshot.")

    accepted: list[tuple[str, bytes, str, str]] = []
    if files and policy.screenshot_policy != "allowed":
        notices.append(f"{len(files)} file(s) NOT stored: {src} is manual-only ({policy.reason}). "
                       "Read the listing yourself and fill in the form.")
    elif files:
        for name, data, role in files:
            media = media_type_for(name, data)
            if media not in SUPPORTED_MEDIA:
                notices.append(f"{name}: not a PNG/JPEG/WebP/GIF image ({media or 'unknown type'}); skipped. "
                               "iPhone photos: export as JPEG.")
                continue
            if len(data) > MAX_IMAGE_BYTES:
                notices.append(f"{name}: larger than 5 MB; skipped. Crop or resize it.")
                continue
            sha = hashlib.sha256(data).hexdigest()
            dup = conn.execute(
                """SELECT i.id FROM intake_files f JOIN raw_captures r ON r.id = f.raw_capture_id
                   JOIN intakes i ON i.id = f.intake_id WHERE r.content_sha256 = ? LIMIT 1""", (sha,)).fetchone()
            if dup:
                notices.append(f"{name}: identical file already captured (capture #{dup['id']}); skipped.")
                continue
            accepted.append((name, data, role, media))
    with transaction(conn):
        iid = conn.execute(
            """INSERT INTO intakes (created_at, kind, url, source_key, external_id, url_evidence, market_key,
                   screenshot_policy, auction_id) VALUES (?, 'listing', ?, ?, ?, ?, ?, ?, ?)""",
            (now, info.normalized_url, src, info.external_id, info.evidence, market_key,
             policy.screenshot_policy, auction_id),
        ).lastrowid
        for pos, (name, data, role, media) in enumerate(accepted):
            rid = _store_file(conn, store, src, data, "screenshot" if role == "screenshot" else "manual_photo",
                              media, now, info.normalized_url, notes=f"file={name}")
            conn.execute("INSERT INTO intake_files VALUES (?, ?, ?, ?)", (iid, rid, role, pos))
    return IntakeResult(iid, notices)


def intake(conn: sqlite3.Connection, intake_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM intakes WHERE id = ?", (intake_id,)).fetchone()
    if row is None:
        raise IntakeError([f"no capture #{intake_id}"])
    return row


def intake_files(conn: sqlite3.Connection, intake_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT f.role, f.position, r.* FROM intake_files f JOIN raw_captures r ON r.id = f.raw_capture_id
           WHERE f.intake_id = ? ORDER BY f.position""", (intake_id,)).fetchall()


def run_extraction(conn: sqlite3.Connection, store: RawStore, cfg: Config, intake_id: int,
                   extractor: Extractor, now: str | None = None) -> int | None:
    """Run the extractor over the intake's screenshots. Returns the extraction
    id, or None when policy or missing files mean there is nothing to run."""
    now = now or now_ts()
    it = intake(conn, intake_id)
    if it["screenshot_policy"] != "allowed":
        return None  # enforced again here, not just in the UI
    files = intake_files(conn, intake_id)
    if not files:
        return None
    max_images = cfg.underwriting.get("extraction", "max_images")
    images = [(store.get(f["content_sha256"]), f["content_type"]) for f in files[:max_images]]
    tz = cfg.market(it["market_key"]).get("timezone")
    context = (f"Auction URL: {it['url'] or 'not given'} (platform guess from URL: {it['source_key']}). "
               f"Screenshots supplied at {from_ts(it['created_at']).astimezone().isoformat(timespec='minutes')}. "
               f"Facility local time zone: {tz}.")
    res = extractor.extract(images, context)
    fields = normalize(res.transcription, tz, it["created_at"]) if res.status == "ok" else {}
    with transaction(conn):
        return conn.execute(
            """INSERT INTO extractions (intake_id, created_at, extractor, prompt_version, status, raw_output,
                   fields_json, error, input_tokens, output_tokens) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (intake_id, now, f"{extractor.name} (served by {res.model})" if res.model else extractor.name,
             PROMPT_VERSION, res.status, res.raw_output,
             canonical_json({k: v.to_dict() for k, v in fields.items()}), res.error,
             res.input_tokens, res.output_tokens),
        ).lastrowid


def latest_extraction(conn: sqlite3.Connection, intake_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM extractions WHERE intake_id = ? ORDER BY id DESC LIMIT 1",
                        (intake_id,)).fetchone()


# Form field -> (FIELDS kind, observation column). ends_at etc. use the same parsers.
FORM_FIELDS: dict[str, tuple[str, str]] = {
    "facility_name": ("text", "facility_name"),
    "facility_operator": ("text", "facility_operator"),
    "address": ("text", "address"),
    "city": ("text", "city"),
    "state": ("text", "state"),
    "postal_code": ("text", "postal_code"),
    "unit_label": ("text", "unit_label"),
    "unit_size": ("size", "unit_size"),
    "current_bid": ("money", "current_bid_cents"),
    "opening_bid": ("money", "opening_bid_cents"),
    "bid_count": ("int", "bid_count"),
    "ends_at": ("time", "ends_at"),
    "buyer_premium_pct": ("pct", "buyer_premium_rate"),
    "cleaning_deposit": ("money", "cleaning_deposit_cents"),
    "cleanout_hours": ("duration", "cleanout_hours"),
    "description": ("text", "description"),
    "visible_contents": ("text", ""),  # kept in raw fields + meta; not an observation column
    "photo_count": ("int", "photo_count"),
    "distance_miles": ("number", "distance_miles"),
}


def form_defaults(conn: sqlite3.Connection, cfg: Config, intake_id: int) -> dict[str, dict]:
    """What the review form shows: extracted proposals (with confidence and
    evidence) where available, otherwise blank."""
    ex = latest_extraction(conn, intake_id)
    fields = json.loads(ex["fields_json"]) if ex is not None and ex["status"] == "ok" else {}
    tz = cfg.market(intake(conn, intake_id)["market_key"]).get("timezone")
    out = {}
    for f in FORM_FIELDS:
        fv = fields.get(f)
        out[f] = fv | {"display": display_value(FORM_FIELDS[f][0], fv["value"], tz)} if fv else \
            {"value": None, "text": "", "confidence": 0.0, "evidence": "", "status": "not_visible", "notes": [],
             "display": ""}
    return out


def display_value(kind: str, v, tz: str) -> str:
    """Typed value -> the text a person would type for it (so an untouched field
    round-trips to the same value)."""
    if v is None:
        return ""
    if kind == "money":
        return f"{v / 100:.2f}".rstrip("0").rstrip(".")
    if kind == "pct":
        return f"{v * 100:g}%"
    if kind == "size":
        w, l, h = v
        return f"{w:g}x{l:g}" + (f"x{h:g}" if h else "")
    if kind == "duration":
        return f"{v:g} hours"
    if kind == "time":
        from zoneinfo import ZoneInfo

        return from_ts(v).astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")
    return str(v)


def _parse_form_value(kind: str, text: str, tz: str, now: str):
    if kind == "number":
        v = float(text)
        if v < 0:
            raise ValueError("must be >= 0")
        return v
    if kind == "time":
        # The form's own format is local wall time; anything else goes through
        # the screenshot-time parser (handles '10/04 2:00 PM MDT' etc).
        try:
            return parse_user_time(text, tz)
        except ValueError:
            v, status, notes = parse_field("time", text, tz, now)
            if status != "found":
                raise ValueError("; ".join(notes) + " (type it as YYYY-MM-DD HH:MM)")
            return v
    if kind == "money":
        return parse_dollars(text.replace("$", "").strip() or text)
    v, _, _ = parse_field(kind, text, tz, now)
    return v


def possible_duplicates(conn: sqlite3.Connection, facility: str | None, unit_label: str | None,
                        ends_at: str | None, exclude_auction: int | None) -> list[dict]:
    """Same facility + unit + end time within 3 hours on another auction record:
    probably the same unit listed twice (or on two platforms)."""
    if not (facility and unit_label and ends_at):
        return []
    lo = to_ts(from_ts(ends_at) - timedelta(hours=3))
    hi = to_ts(from_ts(ends_at) + timedelta(hours=3))
    rows = conn.execute(
        """SELECT DISTINCT a.id, a.source_key, a.external_id FROM auction_observations o
           JOIN auctions a ON a.id = o.auction_id
           WHERE lower(trim(o.facility_name)) = lower(trim(?)) AND lower(trim(o.unit_label)) = lower(trim(?))
             AND o.ends_at BETWEEN ? AND ? AND (? IS NULL OR a.id <> ?)""",
        (facility, unit_label, lo, hi, exclude_auction, exclude_auction)).fetchall()
    return [dict(r) for r in rows]


def confirm_intake(conn: sqlite3.Connection, store: RawStore, cfg: Config, intake_id: int,
                   form: dict[str, str], uncertain: set[str] | frozenset = frozenset(),
                   external_id: str | None = None, status: str = "active", confirmed_by: str | None = None,
                   now: str | None = None) -> tuple[int, int, list[str]]:
    """Turn a reviewed capture into an immutable observation.
    Returns (auction_id, observation_id, warnings)."""
    now = now or now_ts()
    it = intake(conn, intake_id)
    if conn.execute("SELECT 1 FROM intake_confirmations WHERE intake_id = ?", (intake_id,)).fetchone():
        raise IntakeError([f"capture #{intake_id} was already confirmed"])
    if status not in ("scheduled", "active"):
        raise IntakeError(["listing captures are for open auctions; record results with the result form"])
    tz = cfg.market(it["market_key"]).get("timezone")
    ex = latest_extraction(conn, intake_id)
    extracted = json.loads(ex["fields_json"]) if ex is not None and ex["status"] == "ok" else {}

    errors, warnings = [], []
    obs: dict = {}
    meta: dict = {}
    raw_fields: dict = {}
    for f, (kind, col) in FORM_FIELDS.items():
        text = (form.get(f) or "").strip()
        if not text:
            continue
        raw_fields[f] = text
        try:
            value = _parse_form_value(kind, text, tz, it["created_at"])
        except ValueError as e:
            errors.append(f"{f}: {e}")
            continue
        prop = extracted.get(f)
        same = prop is not None and prop.get("value") is not None and (
            prop["value"] == value or (kind == "size" and list(prop["value"]) == list(value)))
        if same:
            m = {"label": "EXTRACTED_CONFIRMED", "confidence": prop["confidence"], "evidence": prop["evidence"],
                 "extraction_id": ex["id"], "extraction_status": prop["status"]}
        else:
            m = {"label": "USER_ENTERED", "confidence": 0.95, "evidence": "typed/corrected by you from the listing",
                 **({"extracted_value_was": prop.get("value")} if prop and prop.get("value") is not None else {})}
        if f in uncertain:
            m["confidence"] = min(m["confidence"], 0.5)
            m["marked_unsure"] = True
        meta[f] = m
        if f == "unit_size":
            w, l, h = value
            obs["width_ft"], obs["length_ft"] = w, l
            if h:
                obs["height_ft"] = h
            obs["size_bucket"] = size_bucket(w, l)
            meta["size_bucket"] = {"label": Label.INFERRED.value, "confidence": m["confidence"],
                                   "evidence": "from unit_size"}
        elif f == "visible_contents":
            continue  # kept in raw_fields/meta; not an observation column
        else:
            obs[col] = value
    if errors:
        raise IntakeError(errors)

    typed = (external_id or "").strip()
    ext_id = typed or it["external_id"]
    if ext_id:
        from_url = not typed or typed == it["external_id"]  # an untouched prefill is still URL-derived
        meta["external_id"] = {"label": "URL_DERIVED" if from_url else "USER_ENTERED",
                               "confidence": 0.9 if from_url else 1.0,
                               "evidence": it["url_evidence"] if from_url else "typed by you"}
    elif it["url"]:
        ext_id = "url:" + hashlib.sha256(it["url"].encode()).hexdigest()[:16]
        meta["external_id"] = {"label": "URL_DERIVED", "confidence": 0.8,
                               "evidence": "no ID visible in the URL; derived from a hash of the URL"}
        warnings.append("No auction ID found: this auction is identified by its URL.")
    else:
        raise IntakeError(["Give the auction URL or its ID so later captures and the result match up."])
    if it["url"]:
        obs["url"] = it["url"]
        meta["url"] = {"label": "USER_ENTERED", "confidence": 1.0, "evidence": "pasted URL"}
    if "ends_at" in obs and obs["ends_at"] < it["created_at"]:
        warnings.append("End time is before the capture time: check it (auction already over?).")
    if "unit_size" not in raw_fields:
        warnings.append("No unit size: the quick estimate needs it.")
    if "ends_at" not in raw_fields:
        warnings.append("No end time: it can't appear under Ending soon.")

    src = it["source_key"]
    existing = find_auction(conn, src, ext_id)
    dups = possible_duplicates(conn, obs.get("facility_name"), obs.get("unit_label"), obs.get("ends_at"), existing)
    for d in dups:
        warnings.append(f"Possible duplicate of {d['source_key']}/{d['external_id']} (same facility, unit and "
                        "end time). Recorded anyway; check it.")
    if existing:
        mk = conn.execute("SELECT market_key FROM auctions WHERE id = ?", (existing,)).fetchone()["market_key"]
        if mk != it["market_key"]:
            raise IntakeError([f"auction already recorded in market {mk}"])
        term = conn.execute(f"SELECT status FROM auction_observations WHERE auction_id = ? AND status IN "
                            f"({','.join('?' * len(TERMINAL_STATUSES))}) LIMIT 1",
                            (existing, *TERMINAL_STATUSES)).fetchone()
        if term:
            warnings.append(f"This auction already has a result ({term['status']}); recorded as a relisting snapshot.")

    form_record = {"intake_id": intake_id, "extraction_id": ex["id"] if ex is not None else None,
                   "policy": it["screenshot_policy"], "fields": raw_fields, "uncertain": sorted(uncertain),
                   "external_id": ext_id, "status": status, "confirmed_by": confirmed_by}
    with transaction(conn):
        rid = _store_file(conn, store, src, canonical_json(form_record).encode(), "review_form",
                          "application/json", now, it["url"], notes=f"intake={intake_id}")
        aid = existing or conn.execute(
            "INSERT INTO auctions (source_key, external_id, market_key, first_recorded_at) VALUES (?, ?, ?, ?)",
            (src, ext_id, it["market_key"], now)).lastrowid
        cols = ["auction_id", "raw_capture_id", "observed_at", "recorded_at", "parser_version", "status",
                "raw_fields_json", "field_meta_json", *obs]
        vals = [aid, rid, it["created_at"], now, PARSER_VERSION, status, canonical_json(raw_fields),
                canonical_json(meta), *obs.values()]
        oid = conn.execute(f"INSERT INTO auction_observations ({', '.join(cols)}) VALUES "
                           f"({', '.join('?' * len(cols))})", vals).lastrowid
        conn.execute("INSERT INTO intake_confirmations VALUES (?, ?, ?, ?)",
                     (intake_id, oid, ex["id"] if ex is not None else None, now))
        for f in intake_files(conn, intake_id):
            if f["role"] == "auction_photo":
                if not conn.execute("SELECT 1 FROM images WHERE auction_id = ? AND sha256 = ?",
                                    (aid, f["content_sha256"])).fetchone():
                    conn.execute("""INSERT INTO images (auction_id, raw_capture_id, observed_at, recorded_at,
                                        sha256, original_name, position) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (aid, f["id"], it["created_at"], now, f["content_sha256"], f["notes"],
                                  f["position"]))
    return aid, oid, warnings


RESULT_OUTCOMES = ("sold", "cancelled", "unsold", "unknown")


def record_result(conn: sqlite3.Connection, store: RawStore, cfg: Config, auction_id: int, outcome: str,
                  winning_price: str = "", bid_count: str = "", note: str = "",
                  now: str | None = None) -> dict:
    """Record how an auction ended, then settle its paper decisions."""
    now = now or now_ts()
    if outcome not in RESULT_OUTCOMES:
        raise IntakeError([f"outcome must be one of {RESULT_OUTCOMES}"])
    a = conn.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,)).fetchone()
    if a is None:
        raise IntakeError([f"no auction #{auction_id}"])
    latest = conn.execute("SELECT * FROM auction_observations WHERE auction_id = ? ORDER BY observed_at DESC, "
                          "id DESC LIMIT 1", (auction_id,)).fetchone()
    errors = []
    price = None
    if outcome == "sold":
        try:
            price = parse_dollars(winning_price.replace("$", "").strip())
        except ValueError:
            errors.append("winning price: enter the final price, e.g. 185")
        if latest is not None and latest["ends_at"] and now < latest["ends_at"]:
            errors.append("The recorded end time hasn't passed yet. If it ended early, capture the listing "
                          "again with the right end time first.")
    elif winning_price.strip():
        errors.append("winning price only applies to a sold auction")
    bids = None
    if bid_count.strip():
        try:
            bids = int(bid_count)
            if bids < 0:
                raise ValueError
        except ValueError:
            errors.append("number of bids must be a whole number")
    if errors:
        raise IntakeError(errors)
    status = {"sold": "sold", "cancelled": "cancelled", "unsold": "unsold", "unknown": "closed"}[outcome]
    raw = {"outcome": outcome, "winning_price": winning_price, "bid_count": bid_count, "note": note}
    meta = {k: {"label": "USER_ENTERED", "confidence": 0.95, "evidence": "result form"} for k, v in raw.items() if v}
    with transaction(conn):
        rid = _store_file(conn, store, a["source_key"], canonical_json(raw | {"auction_id": auction_id}).encode(),
                          "result_form", "application/json", now, notes=f"result auction={auction_id}")
        cols = ["auction_id", "raw_capture_id", "observed_at", "recorded_at", "parser_version", "status",
                "raw_fields_json", "field_meta_json", "final_price_cents", "bid_count"]
        conn.execute(f"INSERT INTO auction_observations ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                     (auction_id, rid, now, now, "result_form_v1", status, canonical_json(raw),
                      canonical_json(meta), price, bids))
    settle_all(conn, cfg, now=now)
    return settlement_summary(conn, auction_id)


def settlement_summary(conn: sqlite3.Connection, auction_id: int) -> dict:
    """What the result means for each strategy's operative decision. Paper
    figures are SIMULATED (would we have won) and ESTIMATED (profit from our
    own estimate); nothing here is REALIZED."""
    from .paper import SETTLEMENT_RULE

    rows = conn.execute(
        """WITH ranked AS (SELECT d.*, ROW_NUMBER() OVER (PARTITION BY d.strategy_key
                             ORDER BY d.decided_at DESC, d.id DESC) rn
                           FROM paper_decisions d WHERE d.auction_id = ?)
           SELECT r.*, s.result, s.final_price_cents, s.increment_cents, s.acq_price_conservative_cents,
                  s.acq_price_neutral_cents, s.details_json
           FROM ranked r LEFT JOIN paper_settlements s ON s.decision_id = r.id AND s.rule_version = ?
           WHERE r.rn = 1""", (auction_id, SETTLEMENT_RULE)).fetchall()
    out = []
    for r in rows:
        item = {"strategy": r["strategy_key"], "decision": r["decision"], "max_bid_cents": r["max_bid_cents"],
                "paper_bid_cents": r["paper_bid_cents"], "result": r["result"],
                "final_price_cents": r["final_price_cents"]}
        if r["final_price_cents"] is not None and r["max_bid_cents"] is not None:
            item["max_bid_minus_price_cents"] = r["max_bid_cents"] - r["final_price_cents"]
        inputs = json.loads(r["inputs_json"])
        if r["result"] == "WON" and "scenarios" in inputs:
            policy = CostPolicy(**inputs["policy"])
            for label, price in (("conservative", r["acq_price_conservative_cents"]),
                                 ("neutral", r["acq_price_neutral_cents"])):
                ev = evaluate(price, Scenario(**inputs["scenarios"]["base"]), policy)
                item[f"estimated_cash_profit_{label}_cents"] = ev.cash_profit_cents
                item[f"acquisition_price_{label}_cents"] = price
        out.append(item)
    return {"auction_id": auction_id, "decisions": out}
