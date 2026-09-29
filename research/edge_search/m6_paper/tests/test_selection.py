"""Frozen selection (DESIGN §4)."""
from decimal import Decimal as D

from m6_paper import selection as SEL
from m6_paper import spec as S

NS = 10**9
NOW = SEL.ts_ns("2026-10-01T00:00:00Z")


def prog(pid, ticker, start="2026-09-30T00:00:00Z", end="2026-10-07T00:00:00Z", reward=1_000_000, target="1000.00"):
    return {"id": pid, "market_ticker": ticker, "incentive_type": "liquidity", "start_date": start, "end_date": end,
            "period_reward": reward, "target_size_fp": target, "discount_factor_bps": 5000}


def mkt(ticker, vol="0", status="active", mve=None):
    return {"ticker": ticker, "event_ticker": "EV-" + ticker, "status": status, "volume_24h_fp": vol,
            "mve_collection_ticker": mve, "price_ranges": [{"start": "0", "end": "1", "step": "0.01"}]}


BOOK = {"yes_dollars": [["0.40", "600"], ["0.39", "900"]], "no_dollars": [["0.55", "700"], ["0.54", "800"]]}


def test_eligibility_rules():
    assert SEL.eligible(prog("a", "A"), mkt("A"), NOW)
    assert not SEL.eligible(prog("a", "A", end="2026-10-01T23:59:00Z"), mkt("A"), NOW)     # < 24 h left
    assert not SEL.eligible(prog("a", "A"), mkt("A", mve="C"), NOW)
    assert not SEL.eligible(prog("a", "A"), mkt("A", status="closed"), NOW)
    assert not SEL.eligible(prog("a", "A", start="2026-10-02T00:00:00Z"), mkt("A"), NOW)


def test_x15_is_the_smallest_size_reaching_150_and_cstar_formula():
    c = SEL.evaluate(prog("a", "A"), mkt("A"), BOOK, ("quadratic", D(1)), NOW)
    assert c.mode == "join_best" and (c.py, c.pn) == (D("0.40"), D("0.55"))
    assert c.projected >= S.PAYOUT_TARGET
    c1 = SEL.evaluate(prog("a", "A"), mkt("A"), BOOK, ("quadratic", D(1)), NOW)
    x = D(c.x)
    assert c1.cstar == x * D("0.40") + x * D("0.55") + x * D("0.55") and c.reserve == x * D("0.55")
    cm = SEL.evaluate(prog("a", "A"), mkt("A"), BOOK, ("quadratic_with_maker_fees", D(1)), NOW)
    assert cm.cstar > c.cstar and cm.lstar > cm.reserve


def test_ranking_one_per_market_ties_by_id_and_greedy_admission():
    cands = [SEL.evaluate(prog(pid, t, reward=r), mkt(t), BOOK, ("quadratic", D(1)), NOW)
             for pid, t, r in (("p2", "A", 1_000_000), ("p1", "A", 1_000_000), ("p3", "B", 3_000_000))]
    r = SEL.ranked(cands)
    assert [c.ticker for c in r].count("A") == 1 and next(c for c in r if c.ticker == "A").program_id == "p1"
    adm = SEL.admit(r, set(), D(0), r[0].cstar)
    assert [c.program_id for c in adm] == [r[0].program_id]
    assert SEL.admit(r, {r[0].ticker}, D(0), D(10**6))[0].ticker != r[0].ticker


def test_u_draw_is_deterministic_stratified_and_windowed():
    progs = [prog(f"z{i}", f"Z{i}", start="2026-09-30T12:00:00Z") for i in range(15)] + \
            [prog(f"n{i}", f"N{i}", start="2026-09-30T12:00:00Z") for i in range(15)] + \
            [prog("old", "OLD", start="2026-09-20T00:00:00Z")]
    ms = {**{f"Z{i}": mkt(f"Z{i}") for i in range(15)}, **{f"N{i}": mkt(f"N{i}", vol="5") for i in range(15)}, "OLD": mkt("OLD")}
    cands = [SEL.evaluate(g, ms[g["market_ticker"]], BOOK, ("quadratic", D(1)), NOW) for g in progs]
    a = SEL.u_draw(cands, NOW, SEL.epoch_day(NOW))
    assert [c.program_id for c in a] == [c.program_id for c in SEL.u_draw(list(reversed(cands)), NOW, SEL.epoch_day(NOW))]
    assert len(a) == 20 and sum(c.volume_24h == 0 for c in a) == 10 and "old" not in {c.program_id for c in a}
