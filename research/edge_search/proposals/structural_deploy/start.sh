#!/usr/bin/env bash
# START (run ONLY after the owner's explicit written approval of the frozen package):
#   ./start.sh <FROZEN_MANIFEST_SHA256>
# Checks the approval matches the installed release and >= 100 GB free, writes the 28-day window, then starts.
set -euo pipefail
MANIFEST="$1"; . /opt/sarb/current/release.env
[ "$MANIFEST" = "$SARB_MANIFEST" ] || { echo "approved manifest != installed release"; exit 1; }
[ ! -e /srv/sarb/WINDOW ] || { echo "a window already exists; refusing to restart the clock"; exit 1; }
free_gb=$(df -B1 --output=avail /srv | tail -1 | awk '{printf "%d",$1/1e9}')
[ "$free_gb" -ge 100 ] || { echo "only $free_gb GB free (< 100); not starting"; exit 1; }
s=$(date -u +%s); START_UTC=$(date -u -d "@$s" +%FT%TZ); END_UTC=$(date -u -d "@$(( s + 28 * 86400 ))" +%FT%TZ)
printf 'START_UTC=%s\nEND_UTC=%s\n' "$START_UTC" "$END_UTC" > /srv/sarb/WINDOW
echo "$MANIFEST" > /srv/sarb/APPROVED
chown sarb:sarb /srv/sarb/WINDOW /srv/sarb/APPROVED; chmod 0444 /srv/sarb/WINDOW /srv/sarb/APPROVED
systemctl enable --now sarb-collector.service
echo "STARTED $START_UTC; collection ends $END_UTC; evaluation opens 24 h later"
