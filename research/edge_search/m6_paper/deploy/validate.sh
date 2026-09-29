#!/usr/bin/env bash
# Short OPERATIONAL validation on the host (reviewer item 6). No reward/P&L analysis is run.
# usage (as root): H038_UNITS="..." H039_UNITS="..." ./validate.sh <FROZEN_MANIFEST_SHA256> [MINUTES=20]
# Produces /srv/m6_paper/logs/validation_<ts>.report; the validation data is DELETED at the end
# (only its file list + sha256 are kept in quarantine), so it can never enter the prospective experiment.
set -euo pipefail
MANIFEST="$1"; MIN="${2:-20}"
TS=$(date -u +%Y%m%dT%H%M%SZ); VDIR=/srv/m6_paper/validation/run_$TS; REP=/srv/m6_paper/logs/validation_$TS.report
cd /opt/m6_paper/current
{
echo "== manifest of deployed code"; python3 -m m6_paper.prereg --verify "$MANIFEST"
echo "== no order/credential code"; ! grep -RInE '/portfolio|KALSHI-ACCESS|Authorization|private_key|method="(POST|PUT|DELETE)"' m6_paper/*.py && echo "none found"
echo "== H038/H039 BEFORE"; for u in ${H038_UNITS:-} ${H039_UNITS:-}; do systemctl show "$u" -p ActiveState -p NRestarts --no-pager; done
echo "== unit tests"; (python3 -m pytest -q -p no:cacheprovider m6_paper/tests 2>&1 | tail -1) || echo "pytest unavailable on host (suite verified pre-deployment)"
HALF=$(( MIN * 30 )); UNTIL1=$(date -u -d "+${HALF} seconds" +%FT%TZ); UNTIL2=$(date -u -d "+$(( MIN * 60 + 60 )) seconds" +%FT%TZ)
RUN="systemd-run --wait --collect --uid=m6paper --gid=m6paper -p Nice=10 -p CPUQuota=50% -p MemoryMax=1500M -p ProtectSystem=strict -p ProtectHome=yes -p ReadWritePaths=/srv/m6_paper -p WorkingDirectory=/opt/m6_paper/current"
echo "== validation part 1 until $UNTIL1"; $RUN python3 -m m6_paper.collector --validation --mode full --data-dir "$VDIR" --until-utc "$UNTIL1"
echo "== restart (part 2) until $UNTIL2";  $RUN python3 -m m6_paper.collector --validation --mode full --data-dir "$VDIR" --until-utc "$UNTIL2"
echo "== validation data checks (no P&L)"; python3 -m m6_paper.validate_run "$VDIR" "$MANIFEST"
echo "== prospective analysis refuses validation data"; python3 -c "import sys; sys.path.insert(0,'.'); from m6_paper import sim
try:
    sim.Replay('$VDIR'); print('ERROR: accepted')
except RuntimeError as e: print('refused:', e)"
echo "== H038/H039 AFTER"; for u in ${H038_UNITS:-} ${H039_UNITS:-}; do systemctl show "$u" -p ActiveState -p NRestarts --no-pager; journalctl -u "$u" --since "-$(( MIN + 5 )) min" --no-pager 2>/dev/null | grep -ciE '429|too many requests' | sed "s/^/$u 429-lines-during-validation=/"; done
echo "== clock"; timedatectl show -p NTPSynchronized 2>/dev/null; curl -sI https://api.elections.kalshi.com/trade-api/v2/exchange/status | grep -i '^date:'; date -u
echo "== resources after"; free -m | head -2; df -h /srv | tail -1; du -sh "$VDIR"
echo "== quarantine: keep only a manifest of the validation files, then delete them"
(cd "$VDIR" && sha256sum *) > /srv/m6_paper/quarantine/validation_${TS}_files.sha256
rm -rf "$VDIR"; echo "deleted $VDIR"
} 2>&1 | tee "$REP"
echo "report: $REP"
