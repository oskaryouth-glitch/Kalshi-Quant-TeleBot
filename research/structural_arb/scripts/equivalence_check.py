"""Settlement-equivalence review: explicit state enumeration through the independent payoff
checker (sarb.payoff, used read-only). No scanner code, gate or threshold is changed.

For each candidate pair, the portfolio is YES on the market with the lower strike plus NO on
the market with the higher (or equal) strike. Two state models are checked:
  (a) SHARED: both markets settle on ONE Expiration Value X (what equivalence would give).
  (b) PERMITTED-DIVERGENT: the states that the binding terms do NOT exclude. Each market has its
      own Expiration Value (X_yes, X_no), plus per-market fallback outcomes.
Strict '>' semantics come from the terms (CRYPTO: '"Above X" means strictly greater than X';
AAA market rules: "strictly greater than $X"). No reporting precision is assumed: AAA
expiration values with 2-4 decimals have been observed, so X is real-valued.
"""
from __future__ import annotations

import itertools
import json
import sys
from fractions import Fraction as Fr

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from sarb import payoff as P  # noqa: E402


def gt(k):
    return P.Interval(Fr(k), False, None, False)


def shared_states(k_yes, k_no, extra_fallback):
    """One X for both markets: explicit named boundary regions and fallback states."""
    lo, hi = Fr(k_yes), Fr(k_no)
    pts = [("X < k_yes", lo - 1), ("X = k_yes", lo)]
    if hi > lo:
        pts += [("k_yes < X < k_no", (lo + hi) / 2), ("X = k_no", hi)]
    pts += [("X > k_no", hi + 1)]
    ey, en = gt(k_yes), gt(k_no)
    out = [P.State(f"{name} (X={x})", {"YES_LEG": P.Truth(ey.contains(x), ey.contains(x)),
                                       "NO_LEG": P.Truth(en.contains(x), en.contains(x))}) for name, x in pts]
    for label, truth in extra_fallback:
        out.append(P.State(label, truth))
    return out


def divergent_states(k_yes, k_no, per_market_fallbacks):
    """X_yes and X_no independent over the same boundary regions, plus per-market fallbacks."""
    lo, hi = Fr(k_yes), Fr(k_no)
    reps = sorted({lo - 1, lo, (lo + hi) / 2 if hi > lo else lo, hi, hi + 1})
    ey, en = gt(k_yes), gt(k_no)
    yes_opts = [(f"X_yes={x}", P.Truth(ey.contains(x), ey.contains(x))) for x in reps] + per_market_fallbacks
    no_opts = [(f"X_no={x}", P.Truth(en.contains(x), en.contains(x))) for x in reps] + per_market_fallbacks
    return [P.State(f"{a} | {b}", {"YES_LEG": ta, "NO_LEG": tb}) for (a, ta), (b, tb) in itertools.product(yes_opts, no_opts)]


def run(name, k_yes, k_no, shared_fallback, per_market_fallbacks):
    pos = [P.Position("YES_LEG", "yes"), P.Position("NO_LEG", "no")]
    sh = P.verify(pos, shared_states(k_yes, k_no, shared_fallback))
    dv = P.verify(pos, divergent_states(k_yes, k_no, per_market_fallbacks))
    fails = [l for l, v in zip(dv.labels, dv.payoffs) if v < 1]
    return {"pair": name, "strikes": {"yes_leg_gt": k_yes, "no_leg_gt": k_no},
            "shared_model": [{"state": l, "payoff": str(v)} for l, v in zip(sh.labels, sh.payoffs)],
            "shared_min_payoff": str(sh.min_payoff),
            "divergent_min_payoff": str(dv.min_payoff), "divergent_failing_states": fails[:12],
            "n_divergent_states": len(dv.labels)}


if __name__ == "__main__":
    NO = P.Truth(False, False)
    res = []
    # AAA: missing data -> "resolve based on the last available day's data" = a determinate common X'
    # (already covered by the X regions). Both markets use the same fallback rule, but they may apply
    # it at different Exchange-chosen expiration times, so each market may independently read the
    # previous day's value (another real X): the per-market option is just another X, already
    # covered by X_yes/X_no independence.
    for nm, ky, kn in (("AAA US: KXAAAGASD 4.4650 YES / KXAAAGASW 4.4660 NO", "4.465", "4.466"),
                       ("AAA US: KXAAAGASW 4.4840 YES / KXAAAGASD 4.4850 NO", "4.484", "4.485"),
                       ("AAA NJ: KXAAAGASDNJ 4.3950 YES / KXAAAGASWNJ 4.4000 NO", "4.395", "4.400"),
                       ("AAA NJ duplicate: KXAAAGASDNJ 4.4000 YES / KXAAAGASWNJ 4.4000 NO", "4.400", "4.400")):
        res.append(run(nm, ky, kn, [], []))
    # SOL: no/incomplete data -> "affected strikes resolve to No" (CRYPTO terms): ALL_NO common state,
    # and per-market "No" if only one market's determination is affected.
    res.append(run("SOL: KXSOLD26 >449.99 YES / KXSOL26500 >500 NO", "449.99", "500",
                   [("NO_DATA both -> both resolve No", {"YES_LEG": NO, "NO_LEG": NO})],
                   [("NO_DATA(this market) -> No", NO)]))
    print(json.dumps(res, indent=1))
