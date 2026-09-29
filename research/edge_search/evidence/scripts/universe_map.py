import json, sys, collections as C
from decimal import Decimal as D
SP=sys.argv[1]
ser={s["ticker"]:s for s in json.load(open(SP+"/series_0929.json"))}
evs=json.load(open(SP+"/events_0929.json"))
ms=[(e,m) for e in evs for m in e.get("markets") or [] if m.get("status")=="active"]
def d(x):
    try: return D(str(x))
    except: return None
print("active markets", len(ms), "events", len(evs))
cat=C.Counter(e.get("category") for e,m in ms); print("by category:", cat.most_common(20))
freq=C.Counter((ser.get(e["series_ticker"],{}) or {}).get("frequency") for e,m in ms); print("by series frequency:", freq.most_common())
ft=C.Counter((ser.get(e["series_ticker"],{}) or {}).get("fee_type") for e,m in ms); print("fee_type:", ft.most_common())
fm=C.Counter(str((ser.get(e["series_ticker"],{}) or {}).get("fee_multiplier")) for e,m in ms); print("fee_multiplier:", fm.most_common())
print("price_level_structure:", C.Counter(m.get("price_level_structure") for e,m in ms).most_common())
# activity
v24=[d(m.get("volume_24h_fp")) or D(0) for e,m in ms]; oi=[d(m.get("open_interest_fp")) or D(0) for e,m in ms]
print("volume_24h==0:", sum(1 for x in v24 if x==0), " >0:", sum(1 for x in v24 if x>0), " >=100:", sum(1 for x in v24 if x>=100), " >=10000:", sum(1 for x in v24 if x>=10000))
print("open_interest==0:", sum(1 for x in oi if x==0))
# spreads from summary quotes (mapping only)
sp=[]; two=0
for e,m in ms:
    yb, ya = d(m.get("yes_bid_dollars")), d(m.get("yes_ask_dollars"))
    if yb and ya and 0<yb<1 and 0<ya<1 and ya>yb: sp.append(ya-yb); two+=1
sp.sort()
q=lambda p: sp[int(p*(len(sp)-1))]
print("two-sided markets (summary):", two, "spread p10/p50/p90:", q(.1), q(.5), q(.9))
# concentration of volume
tot=sum(v24); top=sorted(v24, reverse=True)
print("24h volume share of top 1% markets:", round(float(sum(top[:len(top)//100]))/float(tot),3) if tot else None)
# series-level activity for category tails
byser=C.defaultdict(lambda: D(0))
for (e,m),v in zip(ms,v24): byser[e["series_ticker"]]+=v
act=[s for s,v in byser.items() if v>0]
print("series with any 24h volume:", len(act), "of", len(byser))
print("can_close_early:", C.Counter(m.get("can_close_early") for e,m in ms))
print("strike_type:", C.Counter(m.get("strike_type") for e,m in ms).most_common())
print("settlement source names (series w/ open mkts):", C.Counter(x.get("name") for s in byser for x in (ser.get(s,{}).get("settlement_sources") or [])).most_common(25))
print("distinct contract terms PDFs:", len({ser.get(s,{}).get("contract_terms_url") for s in byser}))
