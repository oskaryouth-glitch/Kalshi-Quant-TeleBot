# M6: instructions for the Hetzner `kalshi-collector` host operator (preflight, install, 20-minute validation)

- **Scope:** run the three frozen M6 deploy scripts for manifest `5dcb3af7227108ed7175b3cdb4bc48d84d234432f1b63dea913981d3415d4811`, then send back the reports below.
- **This does NOT start M6.**
  - Do not create `/srv/m6_paper/APPROVED`.
  - Do not run `systemctl enable` or `start` for `m6-paper-collector`.
  - Do not change any threshold.
- **H038/H039:**
  - They are only queried: unit state, and a count of 429 lines in their journals.
  - Nothing of theirs is read, written, restarted or reconfigured.
  - They have priority. On any sign of degradation, abort M6 (step 5) and report.
- **Time needed:** about 35 minutes, of which the validation takes about 22 minutes wall-clock.
- **Where to run:** as root, inside `tmux` or `screen`, so that a dropped SSH session cannot interrupt the validation.

## Step 0: identify H038/H039 (read-only)

```bash
systemctl list-units --all --no-pager | grep -iE 'h038|h039|kalshi|collector'
```

Write down the exact unit names and data directories of H038 and H039.
- If they do not run as systemd units (docker, cron, tmux, …), **stop here** and report how they run. The preflight and validation checks assume systemd units.

## Step 1: get the frozen code (a fresh checkout, away from H038/H039 files)

```bash
mkdir -p /root/m6_src && cd /root/m6_src
git clone --branch claude/kalshi-pricing-scanner-wbdav0 https://github.com/oskaryouth-glitch/Kalshi-Quant-TeleBot.git repo
cd repo && git checkout --detach 0ae71707b59b983864078257ed84caea2861e52e
git log -1 --format='%H %s' | tee /root/m6_checkout_commit.txt
```

- **If the host cannot reach GitHub:** run `git bundle create m6.bundle 0ae71707b59b983864078257ed84caea2861e52e` on any machine with the repository, copy the bundle over, then `git clone m6.bundle repo && cd repo && git checkout --detach 0ae71707b59b983864078257ed84caea2861e52e`.
- The install step refuses any code that does not hash to the frozen manifest, so a later commit of the branch also works: `m6_paper/` is unchanged since `0ae7170`.

## Step 2: preflight (read-only; changes nothing)

```bash
cd /root/m6_src/repo/research/edge_search/m6_paper/deploy
export H038_UNITS="<H038 unit names>" H039_UNITS="<H039 unit names>" H038_DATA=<H038 data dir> H039_DATA=<H039 data dir>
./preflight.sh 2>&1 | tee /root/m6_preflight_report.txt
```

**GO requires all of the following.** They are the frozen criteria, unchanged:
- ≥ 40 GB free on the filesystem holding `/srv` (`srv_free_GB=`);
- ≥ 1.5 GB `MemAvailable`;
- 1-minute load < 0.7 × cores;
- NTP synchronised;
- Python ≥ 3.11;
- every H038/H039 unit `ActiveState=active`, with no restart in the last 24 h.

**If any criterion fails, STOP.** Do not install. Send back the report.

## Step 3: install (disabled; nothing starts)

```bash
./install.sh 5dcb3af7227108ed7175b3cdb4bc48d84d234432f1b63dea913981d3415d4811 2>&1 | tee /root/m6_install_output.txt
{ systemctl is-enabled m6-paper-collector.service; systemctl is-active m6-paper-collector.service
  test ! -e /srv/m6_paper/APPROVED && echo "APPROVED absent"; } 2>&1 | tee -a /root/m6_install_output.txt
```

Expected:
- `MANIFEST OK 5dcb3af7…`;
- `installed 5dcb3af7… (disabled; not started)`;
- `disabled`, `inactive`, `APPROVED absent`.

Anything else: **stop and report**.

## Step 4: H038/H039 429 baseline, then the 20-minute validation

First, capture a baseline over the same window length the validation measures (25 minutes). This is read-only:

```bash
for u in $H038_UNITS $H039_UNITS; do
  echo "$u 429-lines-in-25-min-before-validation=$(journalctl -u "$u" --since '-25 min' --no-pager 2>/dev/null | grep -ciE '429|too many requests')"
done | tee /root/m6_h038_h039_429_baseline.txt
```

Then run the validation:

```bash
H038_UNITS="$H038_UNITS" H039_UNITS="$H039_UNITS" ./validate.sh 5dcb3af7227108ed7175b3cdb4bc48d84d234432f1b63dea913981d3415d4811 20
```

What it does:
- verifies the deployed manifest;
- scans for order or credential code;
- records H038/H039 state before;
- runs the unit tests (if pytest is present);
- runs 10 minutes of validation collection as `m6paper`, under the unit's caps, then a restart and about 11 more minutes;
- checks the validation data (no P&L is computed);
- confirms the simulator refuses validation data;
- records H038/H039 state after, including 429 lines during the validation;
- checks the clock and resources;
- **deletes** the validation data, keeping only a sha256 list.

It prints `report: /srv/m6_paper/logs/validation_<ts>.report`.

## Step 5: abort procedure (only if H038/H039 show any degradation, or anything looks wrong)

```bash
pkill -u m6paper -f 'm6_paper.collector'          # touches only processes of the m6paper user
for d in /srv/m6_paper/validation/run_*; do [ -d "$d" ] || continue
  (cd "$d" && sha256sum *) > "/srv/m6_paper/quarantine/$(basename "$d")_ABORTED_files.sha256"; rm -rf "$d"; done
```

Report what you saw, and when.

## Step 6: post-checks

```bash
{ systemctl is-enabled m6-paper-collector.service; systemctl is-active m6-paper-collector.service
  test ! -e /srv/m6_paper/APPROVED && echo "APPROVED absent"
  ls -la /srv/m6_paper /srv/m6_paper/validation /srv/m6_paper/quarantine /srv/m6_paper/logs
  for u in $H038_UNITS $H039_UNITS; do systemctl show "$u" -p ActiveState -p NRestarts -p ActiveEnterTimestamp --no-pager; done
  df -h /srv; free -m; date -u; hostname; } 2>&1 | tee /root/m6_postcheck.txt
```

## What to send back (all of it, unedited)

1. `/root/m6_checkout_commit.txt`
2. `/root/m6_preflight_report.txt`
3. `/root/m6_install_output.txt`
4. `/root/m6_h038_h039_429_baseline.txt`
5. `/srv/m6_paper/logs/validation_<ts>.report` (the full report)
6. `/srv/m6_paper/quarantine/validation_<ts>_files.sha256`, plus any `*_ABORTED_files.sha256`
7. `/root/m6_postcheck.txt`
8. A short note:
   - the `H038_UNITS`, `H039_UNITS`, `H038_DATA` and `H039_DATA` values used;
   - whether step 5 was needed, and why;
   - anything unusual.

## How the reports will be reviewed (the frozen criteria; nothing is relaxed)

- **Preflight:** all six GO criteria in step 2.
- **Validation report** (`validation_<ts>.report`):
  - `MANIFEST OK 5dcb3af7…`;
  - `none found` for order or credential code;
  - tests pass, or "pytest unavailable";
  - both validation parts complete;
  - in the `validate_run` JSON:
    - `all_validation: true`;
    - `restarts: 1`, with `restored_tracked_on_restart` recorded;
    - `meta_manifest_matches: true` and `disk_code_manifest_matches: true`;
    - `gzip_integrity_ok: true`;
    - no `loop_exceptions`;
    - `collection_gaps` recorded;
    - `rate_429` and book-poll cadence reported;
    - `clock_ok: true`;
  - the simulator line reads `refused: …`, never `ERROR: accepted`;
  - clock NTP-synchronised;
  - the validation directory deleted.
- **H038/H039:**
  - every unit is still `active` after validation, with `NRestarts` unchanged from before;
  - 429 lines during validation are **no higher** than the 25-minute baseline (deploy README: any increase is NO-GO).
- **Install state:** the service is disabled and inactive, and `APPROVED` is absent.

If all of this passes, the reports go to final review. **START remains a separate, explicit decision by the owner.** No START happens as part of these instructions.
