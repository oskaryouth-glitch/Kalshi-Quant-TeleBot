"""Live liquidity-incentive programs joined to market activity (GET /incentive_programs + GET /events?with_nested_markets).
period_reward is in centi-cents (1/10000 dollar)."""
import json, sys, time, collections as C
from datetime import datetime
from decimal import Decimal as D
inc, evs = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
progs = inc if isinstance(inc, list) else inc.get("incentive_programs")
now = float(sys.argv[3]) if len(sys.argv) > 3 else time.time()
t = lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()
live = [p for p in progs if t(p["start_date"]) <= now <= t(p["end_date"])]
print("programs", len(progs), "live", len(live), C.Counter(p.get("incentive_type") for p in live), C.Counter(p.get("incentive_description") for p in live))
rew = [D(p["period_reward"]) / 10000 for p in live]
days = [(t(p["end_date"]) - t(p["start_date"])) / 86400 for p in live]
print("live pool total $", sum(rew), "median per program $", sorted(rew)[len(rew) // 2])
perday = sorted(r / D(str(max(d, 1 / 24))) for r, d in zip(rew, days))
print("reward per day p10/p50/p90", [round(perday[int(q * (len(perday) - 1))], 2) for q in (.1, .5, .9)])
print("target_size", C.Counter(p.get("target_size_fp") for p in live).most_common(5))
print("discount_factor_bps", C.Counter(p.get("discount_factor_bps") for p in live).most_common(3))
print("period days", C.Counter(round(d) for d in days).most_common(5))
mk = {m["ticker"]: (e, m) for e in evs for m in e.get("markets") or []}
z = nz = two = 0; zr = D(0); cats = C.Counter()
for p in live:
    em = mk.get(p["market_ticker"])
    if not em: continue
    e, m = em; cats[e.get("category")] += 1
    if D(m.get("volume_24h_fp") or "0") == 0: z += 1; zr += D(p["period_reward"]) / 10000
    else: nz += 1
    tg = D(p.get("target_size_fp") or "0")
    two += D(m.get("yes_bid_size_fp") or "0") >= tg and D(m.get("yes_ask_size_fp") or "0") >= tg
print("live on zero-24h-volume markets", z, "pool $", zr, "| nonzero", nz, "| top-of-book size >= target on both sides", two)
print("by category", cats.most_common(10))
