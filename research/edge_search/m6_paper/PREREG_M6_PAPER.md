# M6 paper experiment: pre-registration freeze record

- **Status:** **PROPOSED FREEZE, NOT STARTED.** Collection begins only after the independent reviewer approves `PRE_START_AUDIT.md`.
  - The collector refuses to run without `--i-have-reviewer-approval-to-start`.
  - A start that is later approved must use exactly these hashes. The collector writes them into its `meta` stream at start.
- **Spec version:** `m6-paper-v2`. Design `DESIGN.md` v2, including the reviewer amendments of 2026-09-29.
- **Regenerate** the hashes with `python -m m6_paper.prereg` from `research/edge_search/`.
- **Manifest sha256** (over all file hashes below, sorted by path): `b8c18ef3881d9c4343fb778d3bd62d9c8bd7352cf8166559ceeded05fda7233d`.

## Frozen items and where each is defined

| frozen item | definition (code) | spec constants (`spec.py`) |
|---|---|---|
| Selection rule | `selection.py`: `eligible`, `evaluate` (x15, C\*, L\*, score), `ranked`, `admit` (Arm P greedy), `u_draw` (Arm U); `sim.Replay._on_epoch` | `MIN_REMAINING_S`, `PAYOUT_TARGET`, `MAX_X`, `ACCOUNTS`, `U_*`, `EPOCH_HOURS_UTC`, `TOP_TRACK` |
| Reward calculation | `lip.py` (`configure`, `side_share`, `snapshot_score`; equal to the PT1-frozen functions, tested on 400 random books); `sim.VariantState.on_poll` (sampling, coverage); `sim.payout` (P̂, hourly-batch SE, $1 floor, conservative variant) | `GAP_S`, `BATCH_S`, `Z_CONSERVATIVE`, `PAYOUT_FLOOR`, `BOOK_POLL_MEAN_S` |
| Queue / fill model | `fills.py` (`match_trade`: queue, own-order priority, trade-through); `sim.VariantState._quote` (repricing, replenishment, \|q\| ≤ x, latency) | `LATENCY_NS`, `PRICE_MIN/MAX`, `JOIN_IF_BID_SUM_GE`, `IMPROVE_HALF_WIDTH` |
| Three fill assumptions | `fills.queue_update`: V_T / V_P / V_C | `VARIANTS` |
| Settlement accounting | `accounting.Position` (netting), `contract_values` (settled, liquidation, flat), `fill_pnl`; `sim.episode_ledger` | `SETTLEMENT_CUTOFF_DAYS` |
| Fees | `accounting.fee`, `maker_fee`; `sim.World.fee_state` (series + scheduled changes + event override); selection fee state in `selection.fee_state` | `TAKER_COEF`, `MAKER_COEF`, `DIRECT_G`, `NONDIRECT_G`, `UNKNOWN_FEE_STATE` |
| Capital accounting | `sim.Account.committed`, `tick_capital`; `selection.admit`; capital check in `_quote` | `ACCOUNTS`, `CAPITAL_COST_APR` (reported only) |
| Bootstrap / inference | `analysis.bootstrap_lb95` | `BOOT_N`, `BOOT_SEED` |
| Stopping rule | `sim.Replay._checkpoints`, `entries_open`; `analysis.decide` (no-peek enforcement); `status.py` (counts only) | `CHECKPOINT_DAY`, `MAX_DAY`, `MIN_EPISODES`, `INVALID_*` |
| Kill / survive criteria | `analysis.verdict`, `analysis.m6_overall`; the worst of V_T/V_P/V_C decides | — |

## File hashes (sha256)

```
b03502155346f93d2b15ebda73097d84e70ecc10b1f05085ddbf66a0741a04c3  DESIGN.md
8e774353e5ec41b0bb5c95e15d4e8788d2b4d08e1b7369c79e7072e352e74df2  spec.py
abe2de660a417a2c46e7d9b0d89b4d15ccc091251dae47034ded04b10a8ad8ca  lip.py
1688611e32ba412a58fffd420604e93b1779bef6d48b0b8ce2e3ee9c5e5615cd  selection.py
0dc27a3d1d68bb9f3e5468a46b226462161e747308a41503893e687eaf6a96e4  fills.py
7b8f7a21e8a4cfa482955048e89429e9d409c8d9c86c25acccbab9d14560192e  accounting.py
78b24bf82bd1f9a732add6eb472d74fcfce048695b4b105bc42c2bc430c02d76  sim.py
5eb7cf05721626335d8a0a61592892628f1bd7a73adb79a9bf9f7fbdefe123f3  analysis.py
f5b00ecbf42d130f94a3ff5a065afc5ad1a5f0babc2a5856cc7b124a6e37328a  collector.py
24093dd677e6c1a1673dd0e68a7609e213b0fb723d8a623f56c4c87d9cced448  storage.py
9f6d88da55da8e1f3a270efdd5fa2da2a673dd1e2a66b278f14b6be5f18f5fa8  status.py
651648418bf8e0323439713b96c1fc989fd767530c2ebdc6fe560907da88aba5  prereg.py
ee26ddbca18e4bdc2fae1394b087a7b60ab5889836a66f755aea92e9e469ae09  smoke_check.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  __init__.py
98e3778748db390adbc1e7f5e6f085e2b2305d59d4069abb18593c1a7b9d58e6  tests/conftest.py
b477acdfc7507c65cf04ecac905e5dfdc27b1be97f7c4aa45a69c54e4f1f1082  tests/test_lip_accounting.py
29eb72aaba129afce50851e8b54a770d27f7b7b3f94b940b80e290001db7cae0  tests/test_fills.py
0e324e699958fc709b15f36571e66c3e3265f58b585cb997c263d4ec8ff3e118  tests/test_selection.py
7095303c3895228f244276e75d94b7689b4241fcb978345a2f2fd97800fbe315  tests/test_sim.py
23c1131df31138693d8a64debdf3a353ea59354ffbb389f872d30e1321b086f9  tests/test_collector_analysis.py
b8c18ef3881d9c4343fb778d3bd62d9c8bd7352cf8166559ceeded05fda7233d  MANIFEST
```

## Deviation rule

Once collection starts, any change to a hashed file is a recorded deviation. It must be listed in RESULTS with its reason, and it may not change a threshold, sample, selection, fill assumption, fee, accounting or inference rule. If the reviewer approves pre-start changes, the files are re-hashed and this record is updated **before** the start.
