#!/usr/bin/env bash
# Timed wrapper started by sarb-collector.service. Runs the frozen collector only inside the approved window
# (/srv/sarb/WINDOW, exactly 28 days, written by start.sh). A restart resumes into the same data directory
# (streams are appended; the fee ledger reloads from it). At or after END_UTC it exits 0 and is not restarted.
set -euo pipefail
. /srv/sarb/WINDOW
now=$(date -u +%s); end=$(date -u -d "$END_UTC" +%s); rem=$(( end - now ))
if [ "$rem" -le 0 ]; then echo "collection window ended at $END_UTC"; exit 0; fi
exec /usr/bin/python3 -m sarb.collector --duration-s "$rem" --data-dir "/srv/sarb/data/run_$(echo "$START_UTC" | tr -d ':-')"
