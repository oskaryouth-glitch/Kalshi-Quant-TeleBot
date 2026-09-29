import json, sys, re
evs=json.load(open("events_0929.json"))
ser={s["ticker"]:s for s in json.load(open("series_0929.json"))}
want=sys.argv[1:]
seen=set()
for e in evs:
    st=e["series_ticker"]
    if st in want and st not in seen:
        ms=[m for m in e.get("markets") or [] if m.get("status")=="active"]
        if not ms: continue
        seen.add(st); m=ms[len(ms)//2]; s=ser.get(st,{})
        print("=====", st, "|", e.get("title"), "| cat:", e.get("category"), "| n_mkts:", len(ms), "| mutually_exclusive:", e.get("mutually_exclusive"))
        print("  sources:", [x.get("name")+" "+x.get("url","") for x in s.get("settlement_sources") or []], "| terms:", s.get("contract_terms_url"), "| fee:", s.get("fee_type"), s.get("fee_multiplier"))
        print("  ticker:", m["ticker"], "| strike:", m.get("strike_type"), m.get("floor_strike"), m.get("cap_strike"), "| close:", m.get("close_time"), "| exp_exp:", m.get("expected_expiration_time"), "| pls:", m.get("price_level_structure"))
        print("  quotes y_bid/y_ask:", m.get("yes_bid_dollars"), m.get("yes_ask_dollars"), "vol24:", m.get("volume_24h_fp"), "oi:", m.get("open_interest_fp"))
        print("  PRIMARY:", (m.get("rules_primary") or "")[:900])
        print("  SECONDARY:", (m.get("rules_secondary") or "")[:1400])
missing=[w for w in want if w not in seen]
print("not found:", missing)
