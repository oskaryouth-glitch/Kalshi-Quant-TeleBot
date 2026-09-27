"""One-off live smoke evaluation (read-only, public endpoints). Usage: python scripts/smoke_live.py EVENT [EVENT...]
Fetches each family back-to-back, evaluates all templates once (no persistence re-fetch), prints outcome counts.
NOT the production collector (see DESIGN.md §E.2)."""
import sys, json, time, hashlib, collections as C, datetime as dt
from decimal import Decimal
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarb.client import PublicClient
from sarb import semantics as SEM, relationships as R, fees as FEES
from sarb.evaluator import BookObs, MarketMeta, evaluate
from sarb.orderbook import parse_orderbook, OrderBookFormatError
import requests
c = PublicClient(per_second=8)
def iso(ns): return dt.datetime.fromtimestamp(ns/1e9, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def ts_ns(s): return int(dt.datetime.fromisoformat(s.replace("Z","+00:00")).timestamp()*1e9) if s else None
ex = c.exchange_status().body
_r = c.fee_changes(show_historical="true"); assert _r.status == 200, (_r.status, str(_r.body)[:200]); series_ch = _r.body["series_fee_change_arr"]
targets = sys.argv[1:]  # event tickers
events = [c.get(f"/events/{e}", {"with_nested_markets": "true"}).body for e in targets]
series, terms_sha, specs, metas = {}, {}, [], {}
fetch_mono = time.monotonic_ns()
for eb in events:
    ev = eb["event"]; ms = ev.get("markets") or eb.get("markets") or []
    st = ev["series_ticker"]
    if st not in series:
        series[st] = c.series(st).body
        url = series[st]["series"].get("contract_terms_url")
        if url and url not in terms_sha:
            terms_sha[url] = hashlib.sha256(requests.get(url, timeout=30).content).hexdigest()
    for m in ms:
        if m.get("status") != "active": continue
        specs.append(SEM.build_market_spec(ev, m, series[st], terms_sha))
        lp = Decimal(m["last_price_dollars"]) if m.get("last_price_dollars") else None
        metas[m["ticker"]] = MarketMeta(m["ticker"], st, ev["event_ticker"], m["status"], ts_ns(m.get("close_time")), lp,
                                        ts_ns(m.get("latest_expiration_time")), fetch_mono)
print("terms:", {u.rsplit('/',1)[-1]: h[:12] for u, h in terms_sha.items()})
print("spec rejects:", C.Counter(s.reject for s in specs), "terms status:", C.Counter(s.terms_status for s in specs))
fams = SEM.group_families(specs)
ev_ch = []
for e in targets:
    ev_ch += c.get("/events/fee_changes", {"event_ticker": e}).body.get("event_fee_changes", [])
tot = C.Counter(); logged = []
for key, fs in fams.items():
    fam = R.Family(fs)
    structs = R.numeric_family_templates(fam)
    books = {}
    for s in sorted(fs, key=lambda s: s.ticker):          # family fetched back-to-back
        r = c.orderbook(s.ticker)
        try: ob = parse_orderbook(s.ticker, r.body)
        except OrderBookFormatError as e: ob = None
        xc = dict(r.headers).get("x-cache")
        books[s.ticker] = BookObs(ob, r.status, r.sent_mono_ns, r.recv_mono_ns, r.sent_utc_ns, r.recv_utc_ns, xc)
    now_mono, now_utc = time.monotonic_ns(), time.time_ns()
    fees = {}
    for s in fs:
        try: fees[s.ticker] = FEES.resolve_fee(s.series_ticker, s.event_ticker, iso(now_utc), series[s.series_ticker], series_ch, ev_ch)
        except FEES.UnsupportedFee as e: fees[s.ticker] = e
    skew = max(b.recv_mono_ns for b in books.values()) - min(b.sent_mono_ns for b in books.values())
    print(f"family {key} markets={len(fs)} events={sorted({s.event_ticker for s in fs})} templates={len(structs)} "
          f"guaranteed={sum(s.relationship_class=='GUARANTEED' for s in structs)} book_skew_s={skew/1e9:.2f} "
          f"fees={C.Counter((f.fee_type, str(f.multiplier)) if isinstance(f, FEES.ResolvedFee) else repr(f) for f in fees.values())}")
    for stc in structs:
        out, rec = evaluate(stc, books, metas, fees, ex.get("trading_active", False), now_mono, now_utc, None)
        tot[(stc.relationship, out if out != "LOGGED" else rec.status)] += 1
        if rec: logged.append(rec)
print("\nOUTCOMES (relationship, outcome) -> count")
for k, v in sorted(tot.items()): print("  ", k, v)
for rec in sorted(logged, key=lambda r: -Decimal(r.raw_inconsistency or "-9"))[:6]:
    print("\nTOP", rec.relationship, rec.status, "raw", rec.raw_inconsistency, "locked", rec.locked_payoff, "maxC", rec.max_executable_size)
    print("   legs", [(l.ticker[-18:], l.side, l.best_ask, l.displayed_depth) for l in rec.legs])
    print("   reasons", rec.reasons[:8]); print("   edges@1", rec.extra.get("edges_by_size", {}).get("1"))
