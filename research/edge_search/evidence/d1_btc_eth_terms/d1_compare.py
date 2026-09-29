"""D1: rules-only comparison of the BTC/ETH contract-terms PDFs replaced in the public regulatory bucket
on 2026-09-29, against the reviewed copies, the controlling filings and the Rulebook.

Uses no price, order-book, opportunity or collection data. It reads documents only:
  * reviewed copies:     research/structural_arb/sources/contract_terms/contract_terms_{BTC,ETH}.pdf
  * replaced copies:     bucket contract_terms/{BTC,ETH}.pdf (saved here as new_contract_terms_*.pdf)
  * controlling filings: bucket regulatory/notices/{BTC,ETH} Amendment 2 for posting.pdf
  * all filings for BTC/ETH in the bucket, plus the Rulebook (Rules 5.18/5.19)

Nothing in research/structural_arb is modified.

usage: python d1_compare.py [--offline]   (--offline: reuse the PDFs already saved in this directory)
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                                       # research/
sys.path.insert(0, str(ROOT / "structural_arb"))
from sarb import filings as FL                               # noqa: E402  (read-only)
from sarb import terms as T                                  # noqa: E402  (read-only)

BUCKET = "https://kalshi-public-docs.s3.amazonaws.com/"
CDN = "https://assets.kalshi.com/contract_terms/"
OUT = HERE / "outputs"
RULEBOOK_KEY = "regulatory/rulebook/Kalshi DCM Rulebook v.1.29.pdf"
# Outcome-relevant clauses. Each must be textually identical between the reviewed and the replaced copy.
CLAUSES = ("Underlying", "Source Agency", "Type", "Issuance", "Payout Criterion", "Minimum Tick",
           "Last Trading Date", "Settlement Date", "Expiration Date", "Expiration time", "Expiration Value",
           "Settlement Value", "Contingencies", "Position Limit", "Position Accountability Level")


def get(url: str) -> bytes:
    import requests
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


def pdf_text(pdf: bytes, from_official: bool = True) -> str:
    """Same normalisation as evidence/terms_audit/terms_audit.py (format characters stripped, quotes and
    bullets normalised, whitespace collapsed); optionally from the last 'Official Product Name' onwards,
    which is the Appendix A clean copy in a filing and the whole document in a served PDF."""
    import pymupdf
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    t = " ".join(p.get_text() for p in doc)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    if from_official:
        i = t.rfind("Official Product Name")
        t = t[i:] if i >= 0 else t
    for a, b in (("“", '"'), ("”", '"'), ("’", "'"), ("‘", "'"), ("●", " "), ("•", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def key(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()       # filing PDFs drop inter-word spaces: compare without them


def sentences(t: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", t) if key(s)]


def char_diff(a: str, b: str) -> list[tuple[str, str, str]]:
    ka, kb = re.sub(r"\s+", "", a), re.sub(r"\s+", "", b)
    sm = difflib.SequenceMatcher(None, ka, kb, autojunk=False)
    return [(op, ka[i1:i2], kb[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]


def clause_text(t: str, name: str) -> str | None:
    """The text of one 'Name: ...' clause, up to the next known clause label."""
    k = key(t)
    i = k.find(key(name) + ":")
    if i < 0:
        return None
    rest = k[i + len(key(name)) + 1:]
    ends = [rest.find(key(c) + ":") for c in CLAUSES if c != name and rest.find(key(c) + ":") > 0]
    return rest[:min(ends)] if ends else rest


def main(offline: bool = False) -> dict:
    OUT.mkdir(exist_ok=True)
    listing = [f for pre in FL.PREFIXES for f in FL.http_list(pre)] if not offline else None
    report: dict = {"documents": {}, "templates": {}}

    def load(name: str, url: str | None, local: Path | None = None) -> bytes:
        p = local or (HERE / name)
        if offline or url is None:
            b = p.read_bytes()
        else:
            b = get(url)
            if local is None:
                p.write_bytes(b)
        report["documents"][name] = {"source": url or str(p.relative_to(ROOT)), "bytes": len(b),
                                     "sha256": hashlib.sha256(b).hexdigest()}
        return b

    rb = load("rulebook_v1.29.pdf", BUCKET + urllib.parse.quote(RULEBOOK_KEY), HERE / ".rulebook.tmp")
    rbt = pdf_text(rb, from_official=False)
    for rule, nxt in (("RULE 5.18 POSITION ACCOUNTABILITY (a)", "RULE 5.19 POSITION LIMITS (a)"),
                      ("RULE 5.19 POSITION LIMITS (a)", "(c) In addition to the restrictions")):
        i = rbt.find(rule)
        report.setdefault("rulebook_excerpts", {})[rule[:9]] = rbt[i:rbt.find(nxt, i + 10)].strip() if i >= 0 else None
    (HERE / ".rulebook.tmp").unlink(missing_ok=True)

    for tpl, url in (("BTC", CDN + "BTC.pdf"), ("ETH", CDN + "ETH.pdf")):
        entry = T.REGISTRY[url]
        reviewed = load(f"reviewed_{tpl}", None, ROOT / "structural_arb/sources/contract_terms" / f"contract_terms_{tpl}.pdf")
        new = load(f"new_contract_terms_{tpl}.pdf", BUCKET + f"contract_terms/{tpl}.pdf")
        cdn = get(url) if not offline else None
        a2 = load(f"controlling_{tpl}", BUCKET + urllib.parse.quote(entry.controlling_filing), HERE / f".{tpl}_a2.tmp")
        (HERE / f".{tpl}_a2.tmp").unlink(missing_ok=True)
        t_old, t_new, t_a2 = pdf_text(reviewed), pdf_text(new), pdf_text(a2)
        for n, t in (("reviewed", t_old), ("new", t_new), ("controlling_A2_appendixA", t_a2)):
            (OUT / f"{tpl}_{n}.txt").write_text(t + "\n")
        k_new, k_a2, k_old = key(t_new), key(t_a2), key(t_old)
        rec = {
            "registry": {"served_sha256_reviewed": entry.sha256, "controlling_filing": entry.controlling_filing,
                         "controlling_filing_sha256": entry.controlling_filing_sha256},
            "reviewed_sha256": hashlib.sha256(reviewed).hexdigest(),
            "new_sha256": hashlib.sha256(new).hexdigest(),
            "cdn_now_sha256": hashlib.sha256(cdn).hexdigest() if cdn else None,
            "controlling_sha256_now": hashlib.sha256(a2).hexdigest(),
            "char_diff_reviewed_to_new": char_diff(t_old, t_new),
            "sentences_only_in_reviewed": [s for s in sentences(t_old) if key(s) not in k_new],
            "sentences_only_in_new": [s for s in sentences(t_new) if key(s) not in k_old],
            "new_sentences_absent_from_controlling_filing": [s for s in sentences(t_new) if key(s) not in k_a2],
            "reviewed_sentences_absent_from_controlling_filing": [s for s in sentences(t_old) if key(s) not in k_a2],
            "clauses": {c: {"identical_reviewed_vs_new": clause_text(t_old, c) == clause_text(t_new, c),
                            "in_reviewed": clause_text(t_old, c) is not None, "in_new": clause_text(t_new, c) is not None}
                        for c in CLAUSES},
            "rules_required_present_in_new": {p: key(p) in k_new for p in entry.rules_required},
        }
        if listing is not None:
            rec["bucket_objects_now"] = [(f.key, f.last_modified, f.size) for f in listing if FL.belongs(tpl, f.key)]
            now = time.time_ns()
            objs = tuple(f for f in listing if FL.belongs(tpl, f.key))
            rec["filing_status_now"] = FL.status(entry, FL.Listing(tpl, now, objs, rec["controlling_sha256_now"]), now)
        report["templates"][tpl] = rec
    (OUT / "d1_compare.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps(report, indent=1, sort_keys=True))
    return report


if __name__ == "__main__":
    main(offline="--offline" in sys.argv)
