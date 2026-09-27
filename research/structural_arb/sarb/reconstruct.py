"""Independent after-the-fact reconstruction of a logged candidate (e.g. every RULE_DEFINED_LOCK).

Uses ONLY the recorded streams (books: raw order books, market, event, series and exchange bodies
with timings; the fee-ledger file; the record's provenance block). It then re-derives, from
scratch:
  semantics (sarb.semantics.build_market_spec) -> readings / envelopes / template
  -> the independent payoff checker on the legs (sarb.payoff)
  -> fees in force (a fresh FeeLedger: changes first seen <= evaluation time, plus the recorded
     observations)
  -> every evaluator gate (sarb.evaluator.evaluate)
and compares everything with the logged record. Nothing is fetched from the network. The one
exception is the fresh terms re-hash at P3, which cannot be redone later: its recorded outcome
(metadata_consistency) is used, alongside the stored terms hashes.

    python -m sarb.reconstruct <data_dir> [--status RULE_DEFINED_LOCK]
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
from decimal import Decimal
from fractions import Fraction

from . import fees as FEES
from . import payoff as P
from . import relationships as R
from . import semantics as SEM
from .evaluator import BookObs, MarketMeta, evaluate
from .fee_ledger import FeeLedger, FeeUnresolved
from .orderbook import OrderBookFormatError, parse_orderbook
from .universe import parse_iso_ns


def _read(data_dir, kind):
    for f in sorted(glob.glob(os.path.join(data_dir, f"sarb_{kind}_*.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def reconstruct(data_dir: str, rec: dict, books_index: dict | None = None) -> dict:
    grp, phase = rec["extra"]["group"], rec["extra"]["phase"]
    prov, ev_info = rec["extra"]["provenance"], rec["extra"]["eval"]
    entries = books_index[grp] if books_index is not None else [b for b in _read(data_dir, "books") if b.get("group") == grp]

    def pick(kind, ticker):
        same = [b for b in entries if b["kind"] == kind and b["ticker"] == ticker and b["phase"] == phase]
        earlier = [b for b in entries if b["kind"] == kind and b["ticker"] == ticker and b["phase"] == "P2"]
        cand = same or earlier
        return cand[-1] if cand else None

    diffs = []
    legs = [t for t, _, _ in prov["positions"]]
    specs, books, metas, markets, events = {}, {}, {}, {}, {}
    ledger = FeeLedger(os.path.join(data_dir, prov["fee_ledger_file"]), known_as_of_ns=ev_info["utc_ns"])
    for t in legs:
        mb = pick("market", t)
        ob = pick("orderbook", t)
        m = (mb or {}).get("body", {}).get("market") if mb else None
        if not m or not ob:
            diffs.append(f"MISSING_SNAPSHOT:{t}")
            continue
        markets[t] = m
        eb = pick("event", m["event_ticker"])
        ev = (eb or {}).get("body", {}).get("event") if eb else None
        sb = pick("series", (ev or {}).get("series_ticker", "")) if ev else None
        ser = (sb or {}).get("body") if sb else None
        if not ev or not ser:
            diffs.append(f"MISSING_EVENT_OR_SERIES:{t}")
            continue
        events[t] = ev
        ledger.observe_event(ev, eb["recv_utc_ns"])
        ledger.observe_series(ser, sb["recv_utc_ns"])
        pl = prov["legs"][t]
        terms_sha = {pl["terms_url"]: pl["terms_sha_at_build"]} if pl["terms_url"] and pl["terms_sha_at_build"] else {}
        sp = SEM.build_market_spec(ev, m, ser, terms_sha)
        specs[t] = sp
        for k_rec, v_now in (("readings", sp.readings), ("terms_status", sp.terms_status),
                             ("strike_type", sp.strike_type),
                             ("inner", [repr(i) for i in sp.envelope.inner] if sp.envelope else None),
                             ("outer", [repr(i) for i in sp.envelope.outer] if sp.envelope else None)):
            if pl[k_rec] != v_now:
                diffs.append(f"SEMANTICS_DIFFER:{t}:{k_rec}")
        try:
            book = parse_orderbook(t, ob["body"]) if ob["status"] == 200 else None
        except OrderBookFormatError:
            book = None
        books[t] = BookObs(book, ob["status"], ob["sent_mono_ns"], ob["recv_mono_ns"], ob["sent_utc_ns"],
                           ob["recv_utc_ns"], (ob.get("headers") or {}).get("x-cache"))
        lp = m.get("last_price_dollars")
        lpd = Decimal(lp) if lp else None
        metas[t] = MarketMeta(t, ev.get("series_ticker", ""), ev["event_ticker"], m.get("status", ""),
                              parse_iso_ns(m.get("close_time")), lpd if lpd and lpd > 0 else None,
                              parse_iso_ns(m.get("latest_expiration_time")), mb["recv_mono_ns"])
    if diffs:
        return {"match": False, "diffs": diffs}
    # ---- independent checker on the legs only (atoms of the legs' breakpoints suffice for their payoff)
    positions = tuple(P.Position(t, side, Fraction(q)) for t, side, q in prov["positions"])
    fkey = rec["settlement_evidence"]["family_key"]
    if fkey.startswith("MECNET:"):
        # categorical: at most one YES (MECNET) + NONE; requires the recorded events to be mutually exclusive
        if not all(events[t].get("mutually_exclusive") for t in legs):
            diffs.append("MECNET_NOT_CONFIRMED_IN_RECORDED_EVENT")
        states = P.categorical_states(legs)
        fast = P.verify(positions, states).min_payoff
    elif fkey.startswith("COMBO:"):
        return {"match": False, "diffs": ["COMBO_RECONSTRUCTION_UNSUPPORTED"]}
    else:
        fam = R.Family(list(specs.values()))
        states, fast = R._LazyStates(fam), fam.locked_fast(positions)
    st = R.Structural(rec["relationship"], "UNCHECKED", positions, Fraction(prov["checker"]["nominal"]),
                      fast, "UNCHECKED", Fraction(-1), fkey,
                      tuple(rec["event_tickers"]), [], all(s.terms_status == "TERMS_VERIFIED" for s in specs.values()),
                      False, states)
    R.check(st)
    if str(st.locked) != prov["checker"]["locked"]:
        diffs.append(f"CHECKER_LOCKED_DIFFERS:{st.locked}!={prov['checker']['locked']}")
    # ---- fees
    fees = {}
    for t in legs:
        try:
            fees[t] = ledger.resolve(metas[t].series_ticker, metas[t].event_ticker, ev_info["utc_ns"])
        except FeeUnresolved as e:
            fees[t] = e
    # ---- metadata consistency (recomputed, except the P3 live terms re-hash, which is taken as recorded)
    cons = {}
    for t in legs:
        pl, sp = prov["legs"][t], specs[t]
        recorded = rec["extra"].get("metadata_consistency", {}).get(t, [])
        mecnet_ok = (not rec["settlement_evidence"]["family_key"].startswith("MECNET:")
                     or bool(events[t].get("mutually_exclusive")))
        cons[t] = (SEM.market_fingerprint(markets[t]) == pl["market_fp_at_build"] and sp.terms_url == pl["terms_url"]
                   and "TERMS_HASH_CHANGED_OR_UNAVAILABLE" not in recorded and mecnet_ok)
    active, ex_mono, _ = ev_info["exchange"]
    out, rec2 = evaluate(st, books, metas, fees, active, ev_info["mono_ns"], ev_info["utc_ns"], ev_info["persistence_in"],
                         exchange_fetched_mono_ns=ex_mono, metadata_consistent=cons)
    if rec2 is None:
        return {"match": False, "diffs": diffs + [f"RECONSTRUCTED_OUTCOME:{out}"]}
    for k_rec, a, b in (("status", rec["status"], rec2.status),
                        ("edges_by_size", rec["extra"].get("edges_by_size"), rec2.extra.get("edges_by_size")),
                        ("max_executable_size", rec.get("max_executable_size"), rec2.max_executable_size),
                        ("max_size_positive_and_rule_5_11", rec["extra"].get("max_size_positive_and_rule_5_11"),
                         rec2.extra.get("max_size_positive_and_rule_5_11")),
                        ("gates", rec["extra"].get("gates"), rec2.extra.get("gates"))):
        if json.dumps(a, sort_keys=True, default=str) != json.dumps(b, sort_keys=True, default=str):
            diffs.append(f"DIFFERS:{k_rec}")
    return {"match": not diffs, "diffs": diffs, "status": rec2.status}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--status", default="RULE_DEFINED_LOCK")
    a = ap.parse_args(argv)
    idx: dict = {}
    for b in _read(a.data_dir, "books"):
        idx.setdefault(b.get("group"), []).append(b)
    n = ok = 0
    for r in _read(a.data_dir, "candidates"):
        if r["status"] != a.status or "provenance" not in r["extra"]:
            continue
        n += 1
        res = reconstruct(a.data_dir, r, idx)
        ok += res["match"]
        if not res["match"]:
            print("MISMATCH", r["candidate_id"], res["diffs"])
    print(f"reconstructed {n} records with status {a.status}: {ok} match, {n - ok} mismatch")


if __name__ == "__main__":
    main()
