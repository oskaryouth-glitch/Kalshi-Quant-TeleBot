# M6 paper experiment: pre-registration freeze record

- **Status:** **PROPOSED FREEZE, NOT STARTED.** Collection begins only after the independent reviewer approves `PRE_START_AUDIT.md`.
  - The collector refuses to run without `--i-have-reviewer-approval-to-start`.
  - A start that is later approved must use exactly these hashes. The collector writes them into its `meta` stream at start.
- **Spec version:** `m6-paper-v4`. Design `DESIGN.md` v4 incorporates every reviewer decision of 2026-09-29: the stopping rule; 2 requests/s; recorded, uncompensated gaps; fee provenance; the fill-assumption completion rule; A5 6-hour UTC batch SE; A7 permanent episode-scoped termination; A9 prominent breach reporting. All interpretations A1–A10 and B1–B5 are approved or amended and FROZEN (`INTERPRETATIONS.md`), and the six additional coded choices are FROZEN (`DESIGN.md` §14). **Supersedes** candidate manifests `d8a1aa0a…` (v3) and `b8c18ef3…` (v2).
- **Regenerate** the hashes with `python -m m6_paper.prereg` from `research/edge_search/`.
- **Manifest sha256** (over all file hashes below, sorted by path): `5dcb3af7227108ed7175b3cdb4bc48d84d234432f1b63dea913981d3415d4811`.

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
| Payout SE batching (A5) | `sim.batch_of`, `sim.batch_means_input`, `sim.payout` (fixed 6-h UTC blocks; < 2 batches → conservative payout 0) | `BATCH_S = 21600` |
| Episode termination (A7) | `sim.World.first_non_active`, `sim.VariantState.expire` (first observed non-active status during the episode, at its receive time; permanent; recorded) | — |
| Tracking breaches (A9) | `sim.Replay.breaches`, `status.py`, `analysis.decide` (`TRACKING_BREACHES`; never excluded or repaired) | `TRACK_GRACE_NS` |
| Six additional coded choices | `DESIGN.md` §14: entry and eligibility timing (`sim.Replay._on_epoch`); own-order queue priority (`fills.match_trade`); YES-first tie (`sim.VariantState._quote`); admission C\* with maker fee vs reserve (`selection.admit`, `sim.Account.committed`); backfill from the previous check (`collector.completeness`); first causal poll after each markout horizon (`sim.VariantState._markouts`) | — |

## File hashes (sha256)

```
42b951b44d86e84e71a3c892a78c70289115a97c5a0e2a631603787a0dc1c91c  DESIGN.md
44598c4b07489cc1138a6726e3d8f14d656e1603b0b368c7267828529ee25515  INTERPRETATIONS.md
bfab4b61687b493751baff702619031cd79f126d45b6a31f5661e54c2dd69679  deploy/README.md
fdedc3c9f5df8995f63cbc33b99679a12c271be722556af70f399d5849565415  spec.py
abe2de660a417a2c46e7d9b0d89b4d15ccc091251dae47034ded04b10a8ad8ca  lip.py
cf258c659d22077033428d23318309995ee5fd091aae8267d643bdd41ee146a7  selection.py
0dc27a3d1d68bb9f3e5468a46b226462161e747308a41503893e687eaf6a96e4  fills.py
7b8f7a21e8a4cfa482955048e89429e9d409c8d9c86c25acccbab9d14560192e  accounting.py
8253fef54cd6b4da3048988f655c9df0c9c17732218284ddd04e5edbc8a5c91d  sim.py
0968d2f6cf3c3b52806afefa905a4f4734e00ac740a6db558ba7f63f6b985ace  analysis.py
09ea5988810da95511a5abfd13db46fb0a5cd5a9024c84ff4b6bc7adaf2f09bf  collector.py
24093dd677e6c1a1673dd0e68a7609e213b0fb723d8a623f56c4c87d9cced448  storage.py
02f9d65314b8b4556c82222ab4e18f08c9980df26d13654d45048dd49cdc73ab  status.py
6f15e87c273e8657274e3c48d934dc0d240da34d34623294d8892084214cd86f  prereg.py
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
fb8f5ff9de7a5e2d4c6b5992fffb01db858b6973d814b5d7da4ea1a5ee297e86  tests/test_v4_amendments.py
5dcb3af7227108ed7175b3cdb4bc48d84d234432f1b63dea913981d3415d4811  MANIFEST
```

## Deviation rule

Once collection starts, any change to a hashed file is a recorded deviation. It must be listed in RESULTS with its reason, and it may not change a threshold, sample, selection, fill assumption, fee, accounting or inference rule. If the reviewer approves pre-start changes, the files are re-hashed and this record is updated **before** the start.
