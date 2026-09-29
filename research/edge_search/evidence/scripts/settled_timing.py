"""Settlement-mechanics fields of recently settled NON-combo markets (no prices or outcome-conditioned statistics).
Input: settled_nonmve.json from fetch_settled_nonmve.py."""
import json, sys, collections as C
from datetime import datetime
def t(x): return datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp() if x else None
s = json.load(open(sys.argv[1]))
print("n", len(s), "result:", C.Counter(m.get("result") for m in s))
print("can_close_early:", C.Counter(m.get("can_close_early") for m in s))
print("settlement_timer_seconds:", C.Counter(m.get("settlement_timer_seconds") for m in s).most_common(6))
print("top series:", C.Counter(m["event_ticker"].split("-")[0] for m in s).most_common(12))
print("scalar settlements:", [(m["ticker"], m.get("settlement_value_dollars")) for m in s if m.get("result") == "scalar"])
lag = sorted(t(m["settlement_ts"]) - t(m["close_time"]) for m in s if m.get("settlement_ts") and m.get("close_time"))
q = lambda a, p: a[int(p * (len(a) - 1))]
print("settlement_ts - close_time (s) p10/p50/p90/p99:", [round(q(lag, p)) for p in (.1, .5, .9, .99)])
