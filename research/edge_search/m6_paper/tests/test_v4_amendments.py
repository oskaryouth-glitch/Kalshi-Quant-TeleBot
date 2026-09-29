"""Reviewer amendments of 2026-09-29 (v4): A5 fixed 6-hour UTC batches; A7 permanent, episode-scoped termination;
A9 prominent breach reporting."""
from decimal import Decimal as D

from m6_paper import selection as SEL
from m6_paper import sim as SIM
from m6_paper import spec as S
from m6_paper import storage as ST
from test_sim import BOOK, EPOCH, MARKET, PROGRAM, build, trade

NS = 10**9
H = 3600 * NS
DAY0 = SEL.ts_ns("2026-10-02T00:00:00Z")


# ---------------------------------------------------------------- A5: 6-hour UTC batches
def test_batch_boundaries_are_fixed_utc_six_hour_blocks():
    assert S.BATCH_S == 6 * 3600
    b = SIM.batch_of
    assert b(DAY0) == b(DAY0 + 6 * H - 1)                   # [00:00, 06:00)
    assert b(DAY0 + 6 * H) == b(DAY0) + 1                   # 06:00 starts the next block
    assert b(DAY0 + 6 * H - 1) != b(DAY0 + 6 * H)
    assert b(DAY0 + 12 * H) == b(DAY0) + 2 and b(DAY0 + 18 * H) == b(DAY0) + 3 and b(DAY0 + 24 * H) == b(DAY0) + 4
    assert b(DAY0 - 1) == b(DAY0) - 1                       # 23:59:59.999... belongs to [18:00, 24:00) of the day before
    for h in range(24):                                     # every hour maps to the block of its 6-hour window
        assert b(DAY0 + h * H) - b(DAY0) == h // 6


def fake_episode(samples, reward=D(10)):
    c = SEL.Candidate("p", "T", "EV", DAY0, DAY0 + 24 * H, reward, D(1000), D("0.5"), 1, D("0.4"), D("0.5"),
                      "join_best", D(1), D(1), D("0.5"), D(2), D(1), D(1), D(0), "quadratic", D(1), [])
    e = SIM.Episode("e", "P30", "P30", "V_T", c, DAY0, DAY0 + 24 * H)
    e.samples = samples
    e.cover_ns = 24 * H
    return e


def test_observations_within_one_six_hour_block_are_one_batch_not_six_hourly_batches():
    # polls in 5 different clock hours (01:00-05:59), all inside [00:00, 06:00): hourly batching would have 5
    samples = [(DAY0 + h * H + k * 600 * NS, D("0.4") + D(h) / 100) for h in range(1, 6) for k in range(6)]
    groups = SIM.batch_means_input(samples, [s for _, s in samples])
    assert len(groups) == 1
    p = SIM.payout(fake_episode(samples))
    assert p["p_hat"] >= 1 and p["se"] is None and p["conservative"] == 0 and p["primary"] > 0


def test_two_blocks_give_a_finite_se_and_the_conservative_rule_applies():
    samples = [(DAY0 + 1 * H, D("0.40")), (DAY0 + 2 * H, D("0.42")), (DAY0 + 7 * H, D("0.41")), (DAY0 + 8 * H, D("0.43"))]
    assert len(SIM.batch_means_input(samples, [s for _, s in samples])) == 2
    p = SIM.payout(fake_episode(samples))
    assert p["se"] is not None and p["se"] > 0
    assert (p["conservative"] > 0) == (p["p_hat"] - S.Z_CONSERVATIVE * p["se"] >= 1)


def test_block_edge_observations_split_exactly_at_0600():
    samples = [(DAY0 + 6 * H - 1, D("0.4")), (DAY0 + 6 * H, D("0.4"))]
    assert sorted(SIM.batch_means_input(samples, [s for _, s in samples])) == [SIM.batch_of(DAY0), SIM.batch_of(DAY0) + 1]


# ---------------------------------------------------------------- A7: permanent, episode-scoped termination
def with_status(root, changes):
    w = ST.Writer(root)
    for t, status in changes:
        w.write("markets", {"t_ns": t, "markets": {"MA": {**MARKET, "status": status}}})


def test_first_observed_non_active_status_terminates_permanently_without_backdating(tmp_path):
    root = str(tmp_path / "a7")
    t_obs = EPOCH + 3 * H + 17 * NS
    build(root, trades=[trade(EPOCH + 4 * H, "no", "0.40", 5000, "late")], end_h=8)
    with_status(root, [(t_obs, "paused"), (EPOCH + 5 * H, "active")])       # reactivated later
    rp = SIM.Replay(root).run()
    for st in rp.states.values():
        for e in (e for e in st.episodes if e.account == "P200"):
            assert e.ended_ns == t_obs and e.end_reason == "market_status_non_active"
            assert e.end_status == "paused" and e.end_observed_ns == t_obs
            assert all(f.t_ns <= t_obs for f in e.fills)                    # no fills after termination
            assert all(t <= t_obs for t, _ in e.samples)                    # no reward sampling after termination
        assert not st.accounts["P200"].orders.get("MA")
        assert "MA" not in st.accounts["P200"].active                       # never resumed


def test_old_status_observation_does_not_kill_a_new_episode_entered_later(tmp_path):
    root = str(tmp_path / "a7b")
    build(root, end_h=4)
    with_status(root, [(EPOCH - 2 * H, "paused"), (EPOCH - H, "active")])   # before the entry
    rp = SIM.Replay(root).run(EPOCH + 3 * H)
    e = next(e for e in rp.states["V_T"].episodes if e.account == "P200")
    assert e.ended_ns is None and e.samples


def test_ledger_records_termination_status_and_time(tmp_path):
    root = str(tmp_path / "a7c")
    t_obs = EPOCH + 2 * H
    build(root, end_h=4)
    with_status(root, [(t_obs, "closed")])
    rp = SIM.Replay(root).run()
    r = next(r for r in SIM.episode_ledger(rp, rp.last_t) if r["variant"] == "V_T" and r["account"] == "P200")
    assert (r["end_status"], r["end_observed_ns"], r["ended_ns"]) == ("closed", t_obs, t_obs)


# ---------------------------------------------------------------- A9: breaches reported prominently
def test_breaches_are_reported_not_repaired(tmp_path):
    root = str(tmp_path / "a9")
    build(root, end_h=3)
    rp = SIM.Replay(root).run()
    assert all(v == [] for v in rp.breaches().values())
    root2 = str(tmp_path / "a9b")
    w = ST.Writer(root2)
    w.write("meta", {"t_ns": EPOCH - H, "kind": "start"})
    w.write("markets", {"t_ns": EPOCH - H, "markets": {"MA": MARKET}})
    w.write("epoch", {"t_ns": EPOCH + 30 * NS, "epoch_ns": EPOCH, "programs": [PROGRAM], "markets": {"MA": MARKET},
                      "books": {"MA": BOOK}, "series_fee": {}, "event_series": {}})       # no tracked record at all
    rp2 = SIM.Replay(root2).run()
    br = rp2.breaches()
    assert all(len(v) == len([e for e in rp2.states[k].episodes]) and v for k, v in br.items())
    assert len(rp2.states["V_T"].episodes) >= 1                            # breached episodes stay in the sample
