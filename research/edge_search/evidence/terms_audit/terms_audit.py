"""Structural terms-verification audit (read-only; nothing in research/structural_arb is modified).

For every URL in the frozen structural_arb terms registry:
  1. the live series bound to it (GET /series, contract_terms_url);
  2. the served PDF's sha256 versus the registered hash (what sarb/terms.lookup checks today);
  3. every filing for that exact template in the public regulatory bucket (initial certification and
     amendments), with S3 LastModified, and whether any filing post-dates the served PDF;
  4. the local structural_arb validation records whose lock-like label depended on the entry.

Public unauthenticated GETs only. Output: outputs/terms_audit.json and outputs/terms_audit.txt.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                         # research/
sys.path.insert(0, str(ROOT / "structural_arb"))
from sarb import terms as T                    # noqa: E402  (read-only import of the frozen registry)

API = "https://api.elections.kalshi.com/trade-api/v2"
S3 = "https://kalshi-public-docs.s3.amazonaws.com/"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


def http(url: str) -> bytes:
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:                      # noqa: BLE001  (retry any transport error)
            time.sleep(2 ** attempt)
    raise RuntimeError("GET failed: " + url)


def all_series() -> list[dict]:
    return json.loads(http(API + "/series"))["series"]


def s3_list(prefix: str) -> list[tuple[str, str, int]]:
    out, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        root = ET.fromstring(http(S3 + "?" + urllib.parse.urlencode(q)))
        for c in root.findall("s3:Contents", NS):
            out.append((c.find("s3:Key", NS).text, c.find("s3:LastModified", NS).text, int(c.find("s3:Size", NS).text)))
        if root.findtext("s3:IsTruncated", namespaces=NS) != "true":
            return out
        token = root.findtext("s3:NextContinuationToken", namespaces=NS)


def filings(template: str) -> list[tuple[str, str, int]]:
    """Every object in the bucket for EXACTLY this template (BTC must not match BTCMINMAX)."""
    exact = re.compile(rf"^{re.escape(template)}(\.pdf$| |_|\()", re.I)
    hits = []
    for pre in ("regulatory/notices/", "regulatory/product-certifications/", "contract_terms/"):
        for k, lm, sz in s3_list(pre + template):
            if exact.match(k[len(pre):]):
                hits.append((k, lm, sz))
    return sorted(hits, key=lambda x: x[1])


def terms_text(pdf: bytes) -> str:
    """Normalised contract terms: from the last 'Official Product Name' (the Appendix A clean copy in a
    filing; the whole document in a served PDF) to the end. Format characters (zero-width, bidi marks
    that the filing PDFs contain), quotes, bullets and whitespace are normalised."""
    import unicodedata
    import pymupdf
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    t = " ".join(p.get_text() for p in doc)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    i = t.rfind("Official Product Name")
    t = t[i:] if i >= 0 else t
    for a, b in (("“", '"'), ("”", '"'), ("’", "'"), ("‘", "'"), ("●", " "), ("•", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def _key(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()      # the filing PDFs drop inter-word spaces; compare without them


def sentence_diff(a: str, b: str) -> dict:
    """Whitespace-insensitive comparison; lists sentences of each text absent from the other."""
    ka, kb = _key(a), _key(b)
    split = lambda t: [s for s in re.split(r"(?<=[.!?])\s+", t) if _key(s)]   # noqa: E731
    return {"equal": ka == kb,
            "only_in_served": [s for s in split(a) if _key(s) not in kb],
            "only_in_latest_filing": [s for s in split(b) if _key(s) not in ka]}


# Phrases that occur only in a later filing (from the served-vs-filing diff). If live market rules carry
# them, the Exchange is already operating under the amendment.
AMENDMENT_MARKERS = {"GLOBALTEMPERATURE": ("The Weather Company", "material error")}


def live_rules_markers(template: str, bound: list[str]) -> dict:
    marks = AMENDMENT_MARKERS.get(template, ())
    if not marks:
        return {}
    seen, n = Counter(), 0
    for s in bound[:5]:
        d = json.loads(http(API + "/markets?" + urllib.parse.urlencode({"series_ticker": s, "status": "open", "limit": 5})))
        for m in d.get("markets", []):
            n += 1
            text = ((m.get("rules_primary") or "") + " " + (m.get("rules_secondary") or "")).lower()
            for k in marks:
                seen[k] += k.lower() in text
    return {"open_markets_checked": n, "markets_containing": dict(seen)}


def validation_records(tickers: set[str]) -> Counter:
    c = Counter()
    for f in sorted((ROOT / "structural_arb" / "data").glob("*/sarb_candidates_*.jsonl.gz")):
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            if r.get("status") not in ("GUARANTEED_STRUCTURAL_NOT_EXECUTABLE", "RULE_DEFINED_LOCK"):
                continue
            series = {e.split("-")[0] for e in r.get("event_tickers", [])}
            if series & tickers:
                c[(f.parent.name, r.get("config_version"), r["status"], r["relationship"])] += 1
    return c


def main():
    series = all_series()
    report, lines = {}, []
    for url, vt in T.REGISTRY.items():
        template = url.rsplit("/", 1)[1][:-4]
        bound = sorted(s["ticker"] for s in series if s.get("contract_terms_url") == url)
        served = http(url)
        served_sha = hashlib.sha256(served).hexdigest()
        status = T.lookup(url, served_sha)[1]
        fl = filings(template)
        served_obj = [f for f in fl if f[0] == f"contract_terms/{template}.pdf"]
        served_lm = served_obj[0][1] if served_obj else None
        newer = [f for f in fl if served_lm and f[1] > served_lm and f[0].startswith("regulatory/")]
        recs = validation_records(set(bound))
        live = live_rules_markers(template, bound)
        latest = [f for f in fl if f[0].startswith("regulatory/")][-1]
        latest_pdf = http(S3 + urllib.parse.quote(latest[0]))
        diff = sentence_diff(terms_text(served), terms_text(latest_pdf))
        report[url] = {"template": template, "bound_series": bound, "served_sha256": served_sha,
                       "registered_sha256": vt.sha256, "current_lookup_status": status,
                       "filings": fl, "served_pdf_s3_last_modified": served_lm,
                       "filings_newer_than_served_pdf": newer,
                       "latest_filing": latest[0], "latest_filing_sha256": hashlib.sha256(latest_pdf).hexdigest(),
                       "served_vs_latest_filing_terms": diff,
                       "live_market_rules_amendment_markers": live,
                       "lock_like_validation_records": {" | ".join(map(str, k)): v for k, v in recs.items()}}
        lines.append(f"{template}: {len(bound)} series; lookup today = {status}; served sha {served_sha[:12]} "
                     f"(registered {vt.sha256[:12]})")
        lines.append(f"   served PDF S3 LastModified {served_lm}")
        for k, lm, _ in fl:
            lines.append(f"   filing {lm}  {k}{'   <-- NEWER THAN SERVED PDF' if (k, lm, _) in newer else ''}")
        lines.append(f"   served terms vs latest filing ({latest[0]}, sha {report[url]['latest_filing_sha256'][:12]}): "
                     f"{'IDENTICAL' if diff['equal'] else 'EVERY SERVED SENTENCE IS IN THE FILING (filing-only lines below)' if not diff['only_in_served'] else 'DIFFERENT'}")
        for s in diff["only_in_served"]:
            lines.append(f"      - served only : {s}")
        for s in diff["only_in_latest_filing"]:
            lines.append(f"      + filing only : {s}")
        if live:
            lines.append(f"   live market rules carrying amendment-only phrases: {live}")
        lines.append(f"   lock-like validation records: {sum(recs.values())}")
        for k, v in sorted(recs.items()):
            lines.append(f"      {k}: {v}")
        lines.append(f"   series: {', '.join(bound)}")
    out = HERE / "outputs"
    out.mkdir(exist_ok=True)
    (out / "terms_audit.json").write_text(json.dumps(report, indent=1))
    (out / "terms_audit.txt").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
