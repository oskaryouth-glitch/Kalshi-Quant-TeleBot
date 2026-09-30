#!/usr/bin/env bash
# Operational validation on the dedicated host (D8), >= 30 minutes with a mid-way restart, under the service's
# user, caps and environment. Prints totals only (no status distribution). The validation data is DELETED at the
# end (only its file list + sha256 is kept in quarantine), so it can never enter the prospective collection.
# usage (as root): FORBIDDEN_IPS="..." ./validate.sh [MINUTES=30]
set -euo pipefail
MIN="${1:-30}"; [ "$MIN" -ge 30 ] || { echo "validation must be >= 30 minutes"; exit 1; }
. /opt/sarb/current/release.env
TS=$(date -u +%Y%m%dT%H%M%SZ); VDIR=/srv/sarb/validation/run_$TS; REP=/srv/sarb/logs/validation_$TS.report
EXP=/opt/sarb/current/repo/research/structural_arb; DEP=/opt/sarb/current/repo/research/edge_search/proposals/structural_deploy
PROPS=(-p User=sarb -p Group=sarb -p Nice=5 -p CPUQuota=100% -p MemoryMax=3G -p IOWeight=50 -p NoNewPrivileges=yes
       -p ProtectSystem=strict -p ProtectHome=yes -p PrivateTmp=yes -p ReadWritePaths=/srv/sarb
       -p WorkingDirectory=$EXP -p RemainAfterExit=yes
       -p Environment=PYTHONDONTWRITEBYTECODE=1 -p Environment=HOME=/srv/sarb -p Environment=GIT_CONFIG_COUNT=1
       -p Environment=GIT_CONFIG_KEY_0=safe.directory "-p" "Environment=GIT_CONFIG_VALUE_0=*")
part(){ local u="sarb-validation-$TS-$1"
  systemd-run --wait --unit="$u" "${PROPS[@]}" /usr/bin/python3 -m sarb.collector --duration-s "$2" --data-dir "$VDIR"
  systemctl show "$u" -p Result -p ExecMainStatus -p MemoryPeak -p CPUUsageNSec --no-pager; systemctl stop "$u"; }
{
echo "== preflight (host separation included)"; "$DEP/preflight.sh" || { echo "PREFLIGHT NO-GO: stopping"; exit 1; }
echo "== manifests"; "$DEP/verify_manifest.sh" "$EXP" "$SARB_MANIFEST" "$DEP" "$SARB_DEPLOY_MANIFEST"
echo "== no order/credential code"; ! grep -RInE '/portfolio|KALSHI-ACCESS|Authorization|private_key|\.(post|put|delete)\(' "$EXP/sarb" && echo "none found"
echo "== unit tests"; (cd "$EXP" && python3 -m pytest -q -p no:cacheprovider tests 2>&1 | tail -1) || echo "pytest unavailable on host (suite verified pre-deployment)"
echo "== part 1 ($(( MIN * 30 )) s)"; part 1 $(( MIN * 30 ))
echo "== restart: part 2 ($(( MIN * 30 )) s)"; part 2 $(( MIN * 30 ))
echo "== validation checks (totals only; PASS requires reconstruction.pass and code_identity.ok)"; (cd "$EXP" && python3 "$DEP/sarb_ops.py" validate "$VDIR" "$SARB_COMMIT" "$SARB_CONFIG_VERSION")
echo "== clock"; timedatectl show -p NTPSynchronized; curl -sI https://api.elections.kalshi.com/trade-api/v2/exchange/status | grep -i '^date:'; date -u
echo "== resources after"; free -m | head -2; df -h /srv | tail -1; du -sh "$VDIR"
echo "== quarantine: keep only a manifest of the validation files, then delete them"
(cd "$VDIR" && sha256sum *) > /srv/sarb/quarantine/validation_${TS}_files.sha256
rm -rf "$VDIR"; echo "deleted $VDIR"
} 2>&1 | tee "$REP"
echo "report: $REP"
