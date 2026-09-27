# sarb — structural pricing inconsistency scanner (research, read-only)

Tests whether *executable* structural inconsistencies exist on Kalshi after fees, spreads,
depth, contract rules and timing. It starts from the null hypothesis that none exist.
See `DESIGN.md`.

**Safety.** The scanner makes no orders and uses no credentials: only unauthenticated GETs to
a public allowlist, enforced by `tests/test_client.py`. It shares no code or data with `src/`,
`telegram_ui/`, H022 or H038.

```bash
cd research/structural_arb
python -m pytest -q                                      # unit tests
python -m sarb.collector --cycles 1 --max-events 50     # forward snapshots -> data/ (git-ignored)
python -m sarb.report data/sarb_candidates.jsonl.gz     # summarize research log
```

The collector needs outbound HTTPS to `api.elections.kalshi.com`.

| Module | State |
|---|---|
| client, orderbook, fees (provisional rounding), timing, payoff verifier, research_log, collector, report | built + tested |
| contracts (settlement equivalence), relationships R1–R5, evaluator | pending checkpoint review |
