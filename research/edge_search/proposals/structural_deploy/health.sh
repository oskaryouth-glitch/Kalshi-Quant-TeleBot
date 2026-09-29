#!/usr/bin/env bash
# Operational health ONLY (no-peek): reads the ops and universe streams, disk and unit state. Never opens
# candidates/counts/rule511/statscreen/books, and never runs sarb.report or sarb.reconstruct during collection.
# usage: ./health.sh        (as root or sarb)
set -euo pipefail
. /srv/sarb/WINDOW
DIR="/srv/sarb/data/run_$(echo "$START_UTC" | tr -d ':-')"
systemctl show sarb-collector.service -p ActiveState -p SubState -p NRestarts -p MemoryCurrent --no-pager
cd /opt/sarb/current/repo/research/structural_arb
python3 ../edge_search/proposals/structural_deploy/sarb_ops.py health "$DIR" /srv/sarb/WINDOW
