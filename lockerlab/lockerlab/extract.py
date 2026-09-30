"""Screenshot field extraction.

Two stages, kept separate on purpose:

1. A vision model TRANSCRIBES what is visible, per field: the exact text,
   whether it is visible at all, a confidence, and where it saw it. It is told
   never to infer or fill gaps.
2. ``normalize`` PARSES those transcriptions into typed values with
   deterministic, tested code (money, sizes, times in the market's time zone).
   Anything it cannot parse unambiguously is marked, never guessed.

Every field ends up as {value, text, confidence, evidence, status} where
status is one of:
  found        parsed cleanly from visible text
  not_visible  the extractor saw nothing for it
  invalid      text was visible but could not be parsed
  ambiguous    parseable only with an assumption (shown in evidence)
  inferred     derived rather than read (e.g. a relative "2d 4h left" end time)

Extraction only runs for sources whose capture policy allows it
(platforms.capture_policy); the caller enforces that.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from dateutil import parser as dateparser

from .money import parse_dollars
from .timeutil import from_ts, to_ts
from .units import parse_size

PROMPT_VERSION = "extract_v1"

# field -> (kind, what to look for)
FIELDS: dict[str, tuple[str, str]] = {
    "platform": ("text", "Auction website or app name, as shown (logo or header)."),
    "auction_id": ("text", "Auction or lot ID/number exactly as shown."),
    "facility_name": ("text", "Storage facility name."),
    "facility_operator": ("text", "Storage company/brand if shown separately (e.g. CubeSmart)."),
    "address": ("text", "Facility street address."),
    "city": ("text", "City."),
    "state": ("text", "State."),
    "postal_code": ("text", "ZIP code."),
    "unit_label": ("text", "Unit number/label (e.g. B112)."),
    "unit_size": ("size", "Unit dimensions, e.g. 5x10 or 10' x 15'."),
    "current_bid": ("money", "Current/high bid amount."),
    "opening_bid": ("money", "Starting/opening/minimum bid if shown separately."),
    "bid_count": ("int", "Number of bids."),
    "ends_at": ("time", "Auction end date and time exactly as displayed, including any time zone, or a countdown such as '2d 4h left'."),
    "buyer_premium_pct": ("pct", "Buyer's premium percentage."),
    "cleaning_deposit": ("money", "Cleaning/cleanout deposit amount."),
    "cleanout_hours": ("duration", "Time allowed to empty the unit after winning (e.g. 48 hours, 3 days)."),
    "description": ("text", "The listing's description text. Replace any person's name with [name]."),
    "visible_contents": ("text", "Short comma-separated list of items visible in the unit photos. Say 'possible' where unsure."),
    "photo_count": ("int", "Number of photos in the listing if a count is shown (e.g. '1/8' means 8)."),
}

SYSTEM = (
    "You transcribe storage-auction listing screenshots into fields. Rules:\n"
    "- Copy text exactly as it appears. Do not reformat, convert or compute anything.\n"
    "- If a field is not visible in any screenshot, set visible=false and text to an empty string. "
    "Never guess, infer, or use typical values.\n"
    "- confidence: 0-1, how sure you are the transcription is exactly right (legibility, cropping).\n"
    "- evidence: which screenshot (1-based) and where, e.g. 'screenshot 1, header under the title'.\n"
    "- Never transcribe a private person's name (tenant/occupant); write [name] instead.\n"
    "- For visible_contents, describe items in the unit photos briefly and conservatively."
)

SCHEMA: dict = {
    "type": "object",
    "properties": {
        f: {
            "type": "object",
            "properties": {
                "visible": {"type": "boolean"},
                "text": {"type": "string"},
                "confidence": {"type": "number"},
                "evidence": {"type": "string"},
            },
            "required": ["visible", "text", "confidence", "evidence"],
            "additionalProperties": False,
        }
        for f in FIELDS
    },
    "required": list(FIELDS),
    "additionalProperties": False,
}

SUPPORTED_MEDIA = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


@dataclass
class ExtractorResult:
    status: str  # ok | error | refused
    raw_output: str | None
    transcription: dict | None
    error: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class Extractor(Protocol):
    name: str

    def extract(self, images: list[tuple[bytes, str]], context: str) -> ExtractorResult: ...


class ClaudeExtractor:
    """Claude vision transcription with JSON-schema structured output."""

    def __init__(self, model: str = "claude-opus-5-5", effort: str = "medium", client: Any = None):
        self.model = model
        self.effort = effort
        self._client = client
        self.name = f"claude:{model}"

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def extract(self, images: list[tuple[bytes, str]], context: str) -> ExtractorResult:
        import anthropic

        content: list[dict] = []
        for i, (data, media) in enumerate(images, start=1):
            content.append({"type": "text", "text": f"Screenshot {i}:"})
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": media, "data": base64.standard_b64encode(data).decode()}})
        content.append({"type": "text", "text": context + "\n\nFields:\n" + "\n".join(
            f"- {f}: {desc}" for f, (_, desc) in FIELDS.items())})
        try:
            resp = self._get_client().beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM,
                messages=[{"role": "user", "content": content}],
                output_config={"effort": self.effort,
                               "format": {"type": "json_schema", "schema": SCHEMA}},
                # Server-side fallback on a policy decline: the API re-runs the
                # request on a fallback model within the same call.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError:
            return ExtractorResult("error", None, None, "No valid Anthropic credentials. Set ANTHROPIC_API_KEY "
                                   "(or run `ant auth login`), or fill the fields by hand.")
        except anthropic.RateLimitError as e:
            return ExtractorResult("error", None, None, f"Rate limited: {e.message}")
        except anthropic.APIStatusError as e:
            return ExtractorResult("error", None, None, f"API error {e.status_code}: {e.message}")
        except anthropic.APIConnectionError:
            return ExtractorResult("error", None, None, "Could not reach the Anthropic API (network).")
        except anthropic.AnthropicError as e:  # e.g. missing credentials raised client-side
            return ExtractorResult("error", None, None, f"{type(e).__name__}: {e}")
        usage = getattr(resp, "usage", None)
        common = dict(model=getattr(resp, "model", self.model),
                      input_tokens=getattr(usage, "input_tokens", None),
                      output_tokens=getattr(usage, "output_tokens", None))
        if resp.stop_reason == "refusal":
            return ExtractorResult("refused", None, None, "The model declined this request.", **common)
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if resp.stop_reason == "max_tokens" or text is None:
            return ExtractorResult("error", text, None, f"Incomplete response ({resp.stop_reason}).", **common)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return ExtractorResult("error", text, None, f"Unparseable output: {e}", **common)
        return ExtractorResult("ok", text, data, **common)


# ---------------------------------------------------------------------------
# Normalization: transcription text -> typed values. Pure and deterministic.
# ---------------------------------------------------------------------------

TZ_ABBREV = {
    "MDT": -6, "MST": -7, "MT": None, "PDT": -7, "PST": -8, "PT": None, "CDT": -5, "CST": -6,
    "EDT": -4, "EST": -5, "UTC": 0, "GMT": 0,
}
_RELATIVE = re.compile(r"(?:(\d+)\s*d(?:ays?)?)?\s*(?:(\d+)\s*h(?:(?:ou)?rs?)?)?\s*(?:(\d+)\s*m(?:in(?:ute)?s?)?)?\s*(?:left|remaining)?$",
                       re.I)


@dataclass
class FieldValue:
    value: Any
    text: str
    confidence: float
    evidence: str
    status: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"value": self.value, "text": self.text, "confidence": self.confidence,
                "evidence": self.evidence, "status": self.status, "notes": self.notes}


def _parse_time(text: str, tz: str, captured_at: str) -> tuple[str, str, list[str]]:
    """Returns (utc timestamp, status, notes)."""
    t = text.strip()
    rel = _RELATIVE.match(t)
    if rel and any(rel.groups()):
        d, h, m = (int(x) if x else 0 for x in rel.groups())
        end = from_ts(captured_at) + timedelta(days=d, hours=h, minutes=m)
        return to_ts(end), "inferred", [f"countdown '{t}' added to capture time {captured_at}; "
                                        "check the actual end time"]
    notes: list[str] = []
    abbrev = next((a for a in TZ_ABBREV if re.search(rf"\b{a}\b", t)), None)
    cleaned = re.sub(r"\b(?:Ends?|Closes?|on|at)\b[:]?", " ", t, flags=re.I)
    if abbrev:
        cleaned = re.sub(rf"\b{abbrev}\b", " ", cleaned)
    default = datetime(1900, 1, 1)
    try:
        dt = dateparser.parse(cleaned, default=default, fuzzy=False)
    except (ValueError, OverflowError) as e:
        raise ValueError(f"unrecognised date/time {t!r}") from e
    status = "found"
    if dt.year == 1900:
        # No year shown: take the next occurrence after the capture time.
        cap_local = from_ts(captured_at).astimezone(ZoneInfo(tz))
        dt = dt.replace(year=cap_local.year)
        if dt.replace(tzinfo=ZoneInfo(tz)) < cap_local - timedelta(days=1):
            dt = dt.replace(year=cap_local.year + 1)
        status = "ambiguous"
        notes.append(f"no year shown; assumed {dt.year}")
    if dt.hour == 0 and dt.minute == 0 and not re.search(r"\d:\d|am|pm|noon|midnight", t, re.I):
        status = "ambiguous"
        notes.append("no time of day shown; midnight assumed")
    if dt.tzinfo is None:
        if abbrev and TZ_ABBREV[abbrev] is not None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=TZ_ABBREV[abbrev])))
        else:
            dt = dt.replace(tzinfo=ZoneInfo(tz))
            if not abbrev:
                notes.append(f"no time zone shown; interpreted as {tz}")
    return to_ts(dt), status, notes


def _parse_duration_hours(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|days?|d)\b", text, re.I)
    if not m:
        raise ValueError(f"unrecognised duration {text!r}")
    n = float(m.group(1))
    return n * 24 if m.group(2).lower().startswith("d") else n


def _parse_int(text: str) -> int:
    m = re.search(r"/\s*(\d+)\b", text) or re.search(r"\b(\d+)\b", text)
    if not m:
        raise ValueError(f"no number in {text!r}")
    return int(m.group(1))


def _parse_pct(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not m:
        raise ValueError(f"no percentage in {text!r}")
    v = float(m.group(1))
    if not 0 <= v <= 100:
        raise ValueError("percentage out of range")
    return v / 100


def _parse_money(text: str) -> int:
    m = re.search(r"\$\s*[0-9][0-9,]*(?:\.[0-9]{1,2})?", text) or re.search(r"\b[0-9][0-9,]*(?:\.[0-9]{2})?\b", text)
    if not m:
        raise ValueError(f"no dollar amount in {text!r}")
    return parse_dollars(m.group(0))


def parse_field(kind: str, text: str, tz: str, captured_at: str) -> tuple[Any, str, list[str]]:
    """(value, status, notes). Raises ValueError when the text can't be parsed."""
    if kind == "text":
        return text.strip(), "found", []
    if kind == "money":
        return _parse_money(text), "found", []
    if kind == "int":
        return _parse_int(text), "found", []
    if kind == "pct":
        return _parse_pct(text), "found", []
    if kind == "size":
        w, l, h = parse_size(re.sub(r"(?i)\b(unit|size|ft|feet)\b[:]?", " ", text).strip() or text)
        return [w, l, h], "found", []
    if kind == "duration":
        return _parse_duration_hours(text), "found", []
    if kind == "time":
        return _parse_time(text, tz, captured_at)
    raise AssertionError(kind)


def normalize(transcription: dict | None, tz: str, captured_at: str) -> dict[str, FieldValue]:
    out: dict[str, FieldValue] = {}
    transcription = transcription or {}
    for f, (kind, _) in FIELDS.items():
        t = transcription.get(f) or {}
        text = str(t.get("text") or "").strip()
        conf = t.get("confidence")
        conf = min(1.0, max(0.0, float(conf))) if isinstance(conf, (int, float)) else 0.0
        ev = str(t.get("evidence") or "")
        if not t.get("visible") or not text:
            out[f] = FieldValue(None, "", 0.0, ev or "not visible in the screenshots", "not_visible")
            continue
        try:
            value, status, notes = parse_field(kind, text, tz, captured_at)
        except ValueError as e:
            out[f] = FieldValue(None, text, conf, ev, "invalid", [str(e)])
            continue
        if status != "found":
            conf = min(conf, 0.5)  # an assumption was needed: never present as certain
        out[f] = FieldValue(value, text, conf, ev, status, notes)
    return out


def media_type_for(name: str, data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1"):
        return "image/heic"
    return None
