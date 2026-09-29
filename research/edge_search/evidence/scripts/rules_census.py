import json, re, collections as C
from decimal import Decimal as D
evs=json.load(open("events_0929.json"))
ser={s["ticker"]:s for s in json.load(open("series_0929.json"))}
ms=[(e,m) for e in evs for m in e.get("markets") or [] if m.get("status")=="active"]
def txt(m): return (m.get("rules_primary") or "")+" || "+(m.get("rules_secondary") or "")
pats={
 "M2_average": r"\baverage\b",
 "M2_total_cumulative": r"\b(cumulative|in total|total number|combined total|total of)\b",
 "M2_high_low_of_day": r"\b(maximum|highest|high temperature|low temperature|minimum)\b",
 "M2_ever_at_any_point": r"\b(at any (point|time)|ever (reach|trade|close|be)|is ever)\b",
 "M5_ties": r"\b(ties?|tied|dead[- ]heat)\b",
 "M5_dnp": r"(does not play|did not play|doesn't play|not play in|inactive|does not start|DNP|scratched|withdraw)",
 "M8_postpone_cancel": r"(postpone|cancel|abandon|suspend|called off|rescheduled)",
 "M8_not_released": r"(not (been )?(released|published|available|reported)|is delayed|delay in|no data|unavailable)",
 "M8_fair_value": r"(fair (market )?value|fair price|last traded price|settle.{0,20}at \$?0?\.5|50 ?cents)",
 "M3_first_release": r"(initial (release|report|estimate)|first (release|report|print)|advance estimate|preliminary|revis)",
 "M3_lst": r"(local standard time|\bLST\b|standard time)",
 "M3_rounded": r"(round(ed|ing)?|decimal place|nearest)",
}
cnt=C.Counter(); ex=C.defaultdict(C.Counter); samples={}
for e,m in ms:
    t=txt(m)
    for k,p in pats.items():
        if re.search(p,t,re.I):
            cnt[k]+=1; ex[k][e["series_ticker"]]+=1
            samples.setdefault((k,e["series_ticker"]), t[:700])
print("active markets", len(ms))
for k in pats:
    print(f"\n== {k}: {cnt[k]} markets in {len(ex[k])} series; top: {ex[k].most_common(12)}")
json.dump({f"{k}|{s}":v for (k,s),v in samples.items()}, open("rules_samples.json","w"))
# M4 tail quotes
tail=C.Counter()
for e,m in ms:
    pls=m.get("price_level_structure")
    try:
        ya=D(m.get("yes_ask_dollars") or "0"); yb=D(m.get("yes_bid_dollars") or "0")
        na=D(m.get("no_ask_dollars") or "0"); nb=D(m.get("no_bid_dollars") or "0")
    except Exception: continue
    tail[(pls,"yes_ask<=0.01")]+= (0<ya<=D("0.01"))
    tail[(pls,"yes_ask<0.01")]+= (0<ya<D("0.01"))
    tail[(pls,"yes_bid>=0.99")]+= (D("0.99")<=yb<1)
    tail[(pls,"yes_bid>0.99")]+= (D("0.99")<yb<1)
    tail[(pls,"yes_ask 0.01-0.03")]+= (D("0.01")<=ya<=D("0.03"))
    tail[(pls,"yes_bid=0.01 (longshot bid)")]+= (yb==D("0.01"))
    tail[(pls,"n")]+=1
print("\nM4 tail quotes (summary fields):")
for k,v in sorted(tail.items(), key=lambda kv: (str(kv[0][0]),kv[0][1])): print(k,v)
