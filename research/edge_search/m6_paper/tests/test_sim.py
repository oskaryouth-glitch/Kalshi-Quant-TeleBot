"""End-to-end replay on synthetic recorded streams (no network)."""
import shutil
from decimal import Decimal as D

import pytest

from m6_paper import analysis as AN
from m6_paper import selection as SEL
from m6_paper import sim as SIM
from m6_paper import spec as S
from m6_paper import status as STATUS
from m6_paper import storage as ST

NS = 10**9
T0 = SEL.ts_ns("2026-10-01T03:00:00Z")
EPOCH = SEL.ts_ns("2026-10-01T06:00:00Z")
BOOK = {"yes_dollars": [["0.39", "900"], ["0.40", "600"]], "no_dollars": [["0.54", "800"], ["0.55", "700"]]}
PROGRAM = {"id": "pA", "market_ticker": "MA", "incentive_type": "liquidity", "start_date": "2026-10-01T00:00:00Z",
           "end_date": "2026-10-02T12:00:00Z", "period_reward": 1_000_000, "target_size_fp": "1000.00",
           "discount_factor_bps": 5000}
MARKET = {"ticker": "MA", "event_ticker": "EV-MA", "status": "active", "close_time": "2027-01-01T00:00:00Z",
          "volume_24h_fp": "10", "price_ranges": [{"start": "0", "end": "1", "step": "0.01"}]}


def trade(t_ns, taker, yes_price, count, tid):
    import datetime as dt
    iso = dt.datetime.fromtimestamp(t_ns / NS, dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return {"ticker": "MA", "trade_id": tid, "created_time": iso, "taker_side": taker, "count_fp": f"{count}.00",
            "yes_price_dollars": f"{D(yes_price):.4f}", "no_price_dollars": f"{1 - D(yes_price):.4f}"}


def build(root, trades=(), books=None, end_h=31, poll_s=60, program=PROGRAM):
    w = ST.Writer(root)
    w.write("meta", {"t_ns": T0, "kind": "start"})
    w.write("feestate", {"t_ns": T0, "events": {"EV-MA": {"series_ticker": "S-MA"}},
                         "series": {"S-MA": {"fee_type": "quadratic", "fee_multiplier": 1}}, "fee_changes": []})
    w.write("markets", {"t_ns": T0, "markets": {"MA": MARKET}})
    w.write("epoch", {"t_ns": EPOCH + 30 * NS, "epoch_ns": EPOCH, "programs": [program], "markets": {"MA": MARKET},
                      "books": {"MA": BOOK}, "series_fee": {"S-MA": {"fee_type": "quadratic", "fee_multiplier": 1}},
                      "event_series": {"EV-MA": "S-MA"}})
    w.write("tracked", {"t_ns": EPOCH + 60 * NS, "add": [{"ticker": "MA", "program_id": "pA"}], "set": ["MA"]})
    t, last = EPOCH + 90 * NS, None
    books = books or {}
    while t < EPOCH + end_h * 3600 * NS:
        b = books.get(t, BOOK)
        w.write("books", {"t_ns": t, "books": {"MA": b} if b is not last else {}, "same": [] if b is not last else ["MA"]})
        last = b
        t += poll_s * NS
    if trades:
        w.write("trades", {"t_ns": EPOCH + 2 * 3600 * NS, "trades": list(trades)})


@pytest.fixture
def data(tmp_path):
    root = str(tmp_path / "d")
    first_poll = EPOCH + 90 * NS
    build(root, trades=[trade(first_poll + 5 * NS, "no", "0.40", 600, "t1"),      # consumes the 600 ahead of us
                        trade(first_poll + 6 * NS, "no", "0.40", 3, "t2")])       # fills 3 of our YES bid
    return root


def test_entry_latency_queue_fill_and_inventory_cap(data):
    rp = SIM.Replay(data).run(EPOCH + 3 * 3600 * NS)
    st = rp.states["V_T"]
    for name, K in S.ACCOUNTS.items():
        acct = st.accounts[name]
        eps = [e for e in st.episodes if e.account == name]
        c = SEL.candidates({"epoch_ns": EPOCH, "programs": [PROGRAM], "markets": {"MA": MARKET}, "books": {"MA": BOOK},
                            "series_fee": {"S-MA": {"fee_type": "quadratic", "fee_multiplier": 1}},
                            "event_series": {"EV-MA": "S-MA"}})[0]
        assert bool(eps) == (c.cstar <= K)
        if not eps:
            continue
        e = eps[0]
        assert e.entry_ns == EPOCH + 30 * NS and e.cand.x == c.x
        f = e.fills[0]
        assert f.side == "yes" and f.count == min(3, c.x) and f.price == D("0.40")
        assert acct.cap_max <= K
        yes = [o for o in acct.orders["MA"] if o.side == "yes"]
        assert sum(o.size for o in yes) <= c.x - acct.pos("MA").q        # |q| <= x rule


def test_rewards_are_sampled_and_payout_floor_applies(data):
    rp = SIM.Replay(data).run()
    e = next(e for e in rp.states["V_T"].episodes if e.account == "P200")
    assert e.ended_ns == SEL.ts_ns(PROGRAM["end_date"]) and e.end_reason == "program_end"
    p = SIM.payout(e)
    assert p["p_hat"] > 0 and e.samples[0][1] == 0          # the first poll after entry has no live order yet
    assert p["conservative"] <= p["primary"]
    assert (p["primary"] == 0) == (p["p_hat"] < 1)


def test_capital_limit_never_exceeded_in_any_variant(data):
    rp = SIM.Replay(data).run()
    for st in rp.states.values():
        for name, K in S.ACCOUNTS.items():
            assert st.accounts[name].cap_max <= K


def test_cancellation_variants_order_fills(tmp_path):
    root = str(tmp_path / "v")
    shrunk = {"yes_dollars": [["0.39", "900"], ["0.40", "100"]], "no_dollars": BOOK["no_dollars"]}
    t_shrink = EPOCH + 90 * NS + 5 * 60 * NS
    build(root, trades=[trade(t_shrink + 30 * NS, "no", "0.40", 200, "t1")], books={t_shrink: shrunk}, end_h=4)
    rp = SIM.Replay(root).run()
    filled = {v: sum(f.count for e in rp.states[v].episodes if e.account == "P200" for f in e.fills) for v in S.VARIANTS}
    assert filled["V_T"] <= filled["V_P"] <= filled["V_C"] and filled["V_C"] > filled["V_T"]


def fills_before(rp, cut):
    return [(v, e.account, f.t_ns, f.side, f.price, f.count) for v, st in rp.states.items() for e in st.episodes
            for f in e.fills if f.t_ns <= cut]


def test_no_lookahead_future_data_cannot_change_the_past(tmp_path):
    cut = EPOCH + 90 * NS + 20 * NS
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    base = [trade(EPOCH + 95 * NS, "no", "0.40", 600, "t1"), trade(EPOCH + 97 * NS, "no", "0.40", 2, "t2")]
    build(a, trades=base + [trade(EPOCH + 3600 * NS, "no", "0.40", 50, "t3")])
    build(b, trades=base + [trade(EPOCH + 1800 * NS, "yes", "0.45", 999, "t9")],
          books={EPOCH + 90 * NS + 600 * NS: {"yes_dollars": [], "no_dollars": []}})
    ra, rb = SIM.Replay(a).run(), SIM.Replay(b).run()
    assert fills_before(ra, cut) == fills_before(rb, cut) and fills_before(ra, cut)
    ea = [(e.account, e.entry_ns, e.cand.x) for e in ra.states["V_T"].episodes]
    assert ea == [(e.account, e.entry_ns, e.cand.x) for e in rb.states["V_T"].episodes]


def fake_episode(arm, ended_ns, eid):
    c = SEL.Candidate(eid, "T" + eid, "EV" + eid, 0, 1, D(1), D(1000), D("0.5"), 1, D("0.4"), D("0.5"), "join_best",
                      D(1), D(1), D("0.5"), D(2), D(1), D(1), D(0), "quadratic", D(1), [])
    return SIM.Episode(eid, arm, arm, "V", c, 0, 1, ended_ns=ended_ns)


def test_stopping_rule(tmp_path):
    root = str(tmp_path / "s")
    ST.Writer(root).write("meta", {"t_ns": T0, "kind": "start"})
    rp = SIM.Replay(root)
    d35 = rp.day0 + 35 * SIM.DAY
    for v, st in rp.states.items():
        st.episodes = ([fake_episode("P30", d35 - 1, f"a{i}") for i in range(20)] +          # P30: 20 by day 35
                       [fake_episode("P100", d35 - 1, f"b{i}") for i in range(19)] +         # P100: 19, 20th on day 40
                       [fake_episode("P100", rp.day0 + 40 * SIM.DAY - 1, "b19")] +
                       [fake_episode("P200", d35 - 1, f"c{i}") for i in range(20 if v != "V_C" else 19)])  # one variant short
    rp._checkpoints(rp.day0 + 61 * SIM.DAY)
    s = rp.arm_status
    assert s["P30"]["decision_day"] == 35 and len(s["P30"]["decision_sets"]["V_T"]) == 20
    assert s["P100"]["decision_day"] == 40 and len(s["P100"]["decision_sets"]["V_P"]) == 20
    assert s["P200"]["verdict_state"] == "INSUFFICIENT_EVIDENCE" and s["P200"]["decision_day"] == 60
    assert not rp.entries_open("P30", d35 + 1) and rp.entries_open("P100", d35 + 1)


def test_no_peeking_and_counts_only_status(data, capsys):
    with pytest.raises(AN.NotYet):
        AN.decide(data, "P200")
    out = STATUS.main(data)
    flat = repr(out).lower()
    assert "net" not in flat and "pnl" not in flat and "reward" not in flat and "payout" not in flat
    assert out["completed_episodes"]["P200"]["V_T"] == 1


def test_ledger_values_every_episode(data):
    rp = SIM.Replay(data).run()
    rows = SIM.episode_ledger(rp, rp.last_t)
    r = next(r for r in rows if r["variant"] == "V_T" and r["account"] == "P200")
    assert r["n_fills"] == 1 and r["tracked_ok"] and r["net"] == r["reward_conservative"] + r["trading_pnl"]
