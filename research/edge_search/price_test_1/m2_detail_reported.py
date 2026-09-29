"""M2-NO descriptive detail for RESULTS.md (REPORTED ONLY; written after the frozen run; does not change
the frozen decision and uses no new threshold).
Re-reads public trades after t* for NBA markets to get price distribution and fill-to-close holding time."""
import json, collections as C, statistics as st, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import pt1_common as P
from decimal import Decimal as D
rs = [r for r in json.load(open(P.OUT / 'm2_results.json')) if r['variant'] == 'close']
px = C.Counter(); hold_w = D(0); cap_w = D(0); per_mkt = []
for r in rs:
    if r['league'] != 'NBA':
        continue
    tr = [t for t in P.trades(r['ticker'], r['t_star'] + 1, r['close_ts']) if P.ts(t['created_time']) > r['t_star']]
    g = D(0)
    for t in tr:
        y, n = D(t['yes_price_dollars']), D(t['count_fp'])
        px[(t['taker_side'], str(y))] += n
        if y <= D('0.20'):
            hold_w += n * (1 - y) * D(r['close_ts'] - P.ts(t['created_time'])) / 86400
            cap_w += n * (1 - y)
            g += y * n
    per_mkt.append((r['ticker'], float(g), r['window_h']))
print('price distribution (taker_side, yes_price): contracts')
for k, v in sorted(px.items(), key=lambda kv: -kv[1])[:15]:
    print('  ', k, v)
print('capital-weighted mean days from fill to market close:', hold_w / cap_w if cap_w else None)
g = sorted(x[1] for x in per_mkt)
print('per-market gross safe capture: median', st.median(g), 'p90', g[int(0.9 * len(g))], 'max', g[-1], 'n', len(g))
print('top 5', sorted(per_mkt, key=lambda x: -x[1])[:5])
