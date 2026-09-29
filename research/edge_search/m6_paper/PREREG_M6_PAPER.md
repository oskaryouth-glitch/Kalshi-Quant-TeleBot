# M6 paper experiment: pre-registration freeze record

- **Status:** **PROPOSED FREEZE, NOT STARTED.** Collection begins only after the independent reviewer approves `PRE_START_AUDIT.md`.
  - The collector refuses to run without `--i-have-reviewer-approval-to-start`.
  - A start that is later approved must use exactly these hashes. The collector writes them into its `meta` stream at start.
- **Spec version:** `m6-paper-v3`. Design `DESIGN.md` v3, including both sets of reviewer decisions of 2026-09-29: the stopping rule; 2 requests/s; recorded, uncompensated gaps; fee provenance; the fill-assumption completion rule. Implementation interpretations: `INTERPRETATIONS.md`, hashed.
- **Regenerate** the hashes with `python -m m6_paper.prereg` from `research/edge_search/`.
- **Manifest sha256** (over all file hashes below, sorted by path): `d8a1aa0a237a1adbca22480ec4eced19b6c040813abc46ba55801f575ea9cd02`.

## Frozen items and where each is defined

| frozen item | definition (code) | spec constants (`spec.py`) |
|---|---|---|
| Selection rule | `selection.py`: `eligible`, `evaluate` (x15, C\*, L\*, score), `ranked`, `admit` (Arm P greedy), `u_draw` (Arm U); `sim.Replay._on_epoch` | `MIN_REMAINING_S`, `PAYOUT_TARGET`, `MAX_X`, `ACCOUNTS`, `U_*`, `EPOCH_HOURS_UTC`, `TOP_TRACK` |
| Reward calculation | `lip.py` (`configure`, `side_share`, `snapshot_score`; equal to the PT1-frozen functions, tested on 400 random books); `sim.VariantState.on_poll` (sampling); `sim.covered` (intervals > 60 s earn nothing; gaps never compensated); `sim.payout` (P̂, hourly-batch SE, $1 floor, conservative variant); gap records in `collector` (`ops` `collection_gap`) | `GAP_S`, `BATCH_S`, `Z_CONSERVATIVE`, `PAYOUT_FLOOR`, `BOOK_POLL_MEAN_S` |
| Queue / fill model | `fills.py` (`match_trade`: queue, own-order priority, trade-through); `sim.VariantState._quote` (repricing, replenishment, \|q\| ≤ x, latency) | `LATENCY_NS`, `PRICE_MIN/MAX`, `JOIN_IF_BID_SUM_GE`, `IMPROVE_HALF_WIDTH` |
| Three fill assumptions | `fills.queue_update`: V_T / V_P / V_C | `VARIANTS` |
| Settlement accounting | `accounting.Position` (netting), `contract_values` (settled, liquidation, flat), `fill_pnl`; `sim.episode_ledger` | `SETTLEMENT_CUTOFF_DAYS` |
| Fees | `accounting.fee`, `maker_fee`; `sim.World.fee_state` (known at fill vs applicable by cutoff, with provenance); selection: series-level state at the epoch only (`selection.fee_state`, `fee_provenance`); raw fee objects with receive times (`collector.epoch`, `poll_feestate`, `poll_fee_changes`) | `TAKER_COEF`, `MAKER_COEF`, `DIRECT_G`, `NONDIRECT_G`, `UNKNOWN_FEE_STATE` |
| Capital accounting | `sim.Account.committed`, `tick_capital`; `selection.admit`; capital check in `_quote` | `ACCOUNTS`, `CAPITAL_COST_APR` (reported only) |
| Bootstrap / inference | `analysis.bootstrap_lb95` | `BOOT_N`, `BOOT_SEED` |
| Stopping rule | `sim.Replay._checkpoints`, `entries_open`; `analysis.decide` (no-peek enforcement); `status.py` (counts only) | `CHECKPOINT_DAY`, `MAX_DAY`, `MIN_EPISODES`, `INVALID_*` |
| Kill / survive criteria | `analysis.verdict`, `analysis.m6_overall`; the worst of V_T/V_P/V_C decides | — |

## File hashes (sha256)

```
b1710460618081d4aeffd85777448e8c32c2b9c595539390fafb1e01d5cd79fc  DESIGN.md
52945d5de80def1fe29e105f549978c2a8b5f70b527fb2e0922bc9339bd882ed  INTERPRETATIONS.md
bfab4b61687b493751baff702619031cd79f126d45b6a31f5661e54c2dd69679  deploy/README.md
bd4c053d53cf1c30140d4aa11dfe6be845e2c8aa5673e9bb396552ade593ce67  spec.py
abe2de660a417a2c46e7d9b0d89b4d15ccc091251dae47034ded04b10a8ad8ca  lip.py
cf258c659d22077033428d23318309995ee5fd091aae8267d643bdd41ee146a7  selection.py
0dc27a3d1d68bb9f3e5468a46b226462161e747308a41503893e687eaf6a96e4  fills.py
7b8f7a21e8a4cfa482955048e89429e9d409c8d9c86c25acccbab9d14560192e  accounting.py
5506751df82da78bca0ece04b8eec6bd6012fd31a8be18f8f6c925813e5b96bf  sim.py
5eb7cf05721626335d8a0a61592892628f1bd7a73adb79a9bf9f7fbdefe123f3  analysis.py
09ea5988810da95511a5abfd13db46fb0a5cd5a9024c84ff4b6bc7adaf2f09bf  collector.py
24093dd677e6c1a1673dd0e68a7609e213b0fb723d8a623f56c4c87d9cced448  storage.py
9f6d88da55da8e1f3a270efdd5fa2da2a673dd1e2a66b278f14b6be5f18f5fa8  status.py
9f06e29bd44618ecf8c870118849b5c802c27df149119030346af8c77006e8ad  prereg.py
ee26ddbca18e4bdc2fae1394b087a7b60ab5889836a66f755aea92e9e469ae09  smoke_check.py
8d52b871b4c2136a6485e7d628607c5ffdfb2c6db5165fb68788a8885d2d40a5  size_probe.py
f304f7fe5126441b3e7359ea64b4c9b81be673495fadd6798bc20caa5c2705ab  validate_run.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  __init__.py
11454d0306c5615613790e5147f99e9b5c6215b4b70ca756564245f83c99daa7  deploy/m6-paper-collector.service
bf34aa58f4adda072b1a1ae42c8c5a758888a6186cca26a9815330d9f85b5432  deploy/preflight.sh
c3c155863918b969979a651531526c888bcc1d71120b559adc15bde76d56ba7d  deploy/install.sh
15ecc6d61d0dda096a7248579438c3cab3e65535e22791e21d156e626a650ecc  deploy/validate.sh
98e3778748db390adbc1e7f5e6f085e2b2305d59d4069abb18593c1a7b9d58e6  tests/conftest.py
b477acdfc7507c65cf04ecac905e5dfdc27b1be97f7c4aa45a69c54e4f1f1082  tests/test_lip_accounting.py
29eb72aaba129afce50851e8b54a770d27f7b7b3f94b940b80e290001db7cae0  tests/test_fills.py
0e324e699958fc709b15f36571e66c3e3265f58b585cb997c263d4ec8ff3e118  tests/test_selection.py
7095303c3895228f244276e75d94b7689b4241fcb978345a2f2fd97800fbe315  tests/test_sim.py
3fac7cf2462b7ba5fd5d7c11c853865fd57641eb17d8e8de8bb79ed38d3b141b  tests/test_collector_analysis.py
908144c3dceda843199897138973ac0ca1c17b995f2d099b76e14c052c145307  tests/test_v3_changes.py
d8a1aa0a237a1adbca22480ec4eced19b6c040813abc46ba55801f575ea9cd02  MANIFEST
```

## Deviation rule

Once collection starts, any change to a hashed file is a recorded deviation. It must be listed in RESULTS with its reason, and it may not change a threshold, sample, selection, fill assumption, fee, accounting or inference rule. If the reviewer approves pre-start changes, the files are re-hashed and this record is updated **before** the start.
