"""Review pass 1 (rules/mechanics only): reproduction script for evidence/review1/outputs.

Read-only public sources only:
  * https://kalshi-public-docs.s3.amazonaws.com  (Kalshi's public regulatory bucket: filed Part 40
    certifications, amendments, notices, rulebooks, and the served contract_terms PDFs)
  * https://api.elections.kalshi.com/trade-api/v2 (unauthenticated GETs)
No prices, order books or trades are used anywhere in this script: only rules text, filing dates,
and settlement STATE fields (result, settlement_value_dollars, close_time).

    python review1_mechanics.py stale-terms           # served terms PDF older than latest filed amendment
    python review1_mechanics.py early-close SERIES... # close-time pattern of settled markets
    python review1_mechanics.py contingency SERIES... # frequency of scalar/fixed-value settlement states
    python review1_mechanics.py field-sum SERIES:N... # per-event sum of settlement values over listed markets
"""
import collections as C, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo

S3 = "https://kalshi-public-docs.s3.amazonaws.com/"
API = "https://api.elections.kalshi.com/trade-api/v2"


def _get(url):
    for a in range(7):
        try:
            return urllib.request.urlopen(url, timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** a); continue
            raise
    raise RuntimeError("rate limited: " + url)


def s3_keys():
    keys, tok = [], None
    while True:
        q = {"list-type": "2", "max-keys": "1000", **({"continuation-token": tok} if tok else {})}
        x = _get(S3 + "?" + urllib.parse.urlencode(q)).decode()
        keys += [(m[1], m[2]) for m in re.finditer(r"<Contents><Key>(.*?)</Key><LastModified>(.*?)</LastModified>", x)]
        t = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", x)
        if not t:
            return keys
        tok = t.group(1)


def stale_terms():
    """Heuristic screen only: a served PDF older than the latest amendment notice. Confirm each hit by
    diffing texts (BTC/ETH are false positives: their served PDF already equals Amendment 2)."""
    keys = s3_keys()
    terms = {k.split("/", 1)[1][:-4].upper(): d for k, d in keys
             if k.startswith("contract_terms/") and k.lower().endswith(".pdf") and k.count("/") == 1}
    amend = C.defaultdict(list)
    for k, d in keys:
        m = re.match(r"regulatory/notices/([A-Z0-9]+)[ _]+Amendment", k)
        if m:
            amend[m.group(1)].append(d)
    stale = sorted((n, terms[n][:10], max(v)[:10]) for n, v in amend.items() if n in terms and terms[n] < max(v))
    print(f"served terms PDFs {len(terms)}; templates with amendment notices {len(amend)}; served PDF older than latest amendment {len(stale)}")
    for r in stale:
        print("  ", *r)


def settled(series):
    out = {}
    for path, extra in (("/markets", {"status": "settled"}), ("/historical/markets", {})):
        cur = None
        for _ in range(10):
            q = {"series_ticker": series, "limit": 1000, **extra, **({"cursor": cur} if cur else {})}
            d = json.loads(_get(API + path + "?" + urllib.parse.urlencode(q)))
            for m in d.get("markets", []):
                out[m["ticker"]] = m
            cur = d.get("cursor"); time.sleep(0.8)
            if not cur or not d.get("markets"):
                break
    return list(out.values())


def _events(ms):
    ev = C.defaultdict(list)
    for m in ms:
        ev[m["event_ticker"]].append(m)
    return {e: l for e, l in ev.items() if all(x.get("result") in ("yes", "no", "scalar") for x in l)}


def early_close(series):
    et, t = ZoneInfo("America/New_York"), (lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")))
    for st in series:
        ev = _events(settled(st)); early = C.Counter(); n = 0
        for l in ev.values():
            last = max(t(m["close_time"]) for m in l)
            for m in l:
                if (last - t(m["close_time"])).total_seconds() > 3600:
                    n += 1; early[t(m["close_time"]).astimezone(et).strftime("%H:%M")] += 1
        print(f"{st:14s} events={len(ev):4d} closed >1h before the event's final close={n:4d} times(ET)={early.most_common(5)}")


def contingency(series):
    for st in series:
        ev = _events(settled(st))
        sc = [e for e, l in ev.items() if any(x["result"] == "scalar" for x in l)]
        half = [e for e in sc if all(x.get("settlement_value_dollars") == "0.5000" for x in ev[e])]
        sums = C.Counter(str(sum(D(x.get("settlement_value_dollars") or "0") for x in ev[e])) for e in sc)
        print(f"{st:13s} events={len(ev):5d} with_scalar={len(sc):4d} all_0.50={len(half):4d} scalar-event payout sums={sums.most_common(4)}")


def field_sum(specs):
    for spec in specs:
        st, n = spec.split(":"); n = int(n)
        ev = _events(settled(st))
        s = sorted(sum(D(x.get("settlement_value_dollars") or "0") for x in l) for l in ev.values())
        if s:
            print(f"{st:13s} N={n} events={len(s)} sum min={s[0]} median={s[len(s)//2]} max={s[-1]} mean-N={float(sum(s))/len(s)-n:.2f} below_N={sum(1 for v in s if v < n)}")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"stale-terms": lambda a: stale_terms(), "early-close": early_close, "contingency": contingency, "field-sum": field_sum}[cmd](args)
