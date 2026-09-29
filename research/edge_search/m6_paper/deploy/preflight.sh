#!/usr/bin/env bash
# M6 pre-deployment headroom report for the kalshi-collector host. READ-ONLY: changes nothing.
# usage: H038_UNITS="unit1 unit2" H039_UNITS="unit3" H038_DATA=/path H039_DATA=/path ./preflight.sh > preflight_report.txt
# GO requires: >= 40 GB free on the filesystem holding /srv (M6 upper bound ~12.6 GB over 90 days, x3 margin),
#   >= 1.5 GB MemAvailable, 1-min load < 0.7 x cores, clock NTP-synchronised, python3 >= 3.11,
#   and every H038/H039 unit active with no restarts in the last 24 h.
set -u
echo "== M6 preflight $(date -u +%FT%TZ) on $(hostname)"
echo "== CPU";    nproc; cat /proc/loadavg
echo "== RAM";    free -m; grep -E 'MemAvailable|SwapFree' /proc/meminfo
echo "== DISK";   df -h / /srv 2>/dev/null; df -B1 --output=avail /srv 2>/dev/null | tail -1 | awk '{printf "srv_free_GB=%.1f\n",$1/1e9}'
echo "== IO";     (command -v iostat >/dev/null && iostat -dx 1 2 | tail -n +4) || cat /proc/diskstats | head -5
echo "== CLOCK";  timedatectl show -p NTPSynchronized -p TimeUSec 2>/dev/null; (chronyc tracking 2>/dev/null | grep -E 'System time|Last offset') || true
echo "== PYTHON"; python3 --version
echo "== NETWORK (public API reachability only)"; curl -s -o /dev/null -w 'kalshi api HTTP %{http_code} %{time_total}s\n' https://api.elections.kalshi.com/trade-api/v2/exchange/status
echo "== H038/H039 units (baseline; M6 must not change these)"
UNITS="${H038_UNITS:-} ${H039_UNITS:-}"
if [ -z "${UNITS// }" ]; then
  echo "H038_UNITS/H039_UNITS not given; candidate units:"; systemctl list-units --all --no-pager | grep -iE 'h038|h039|kalshi|collector' || true
fi
for u in $UNITS; do
  systemctl show "$u" -p ActiveState -p SubState -p NRestarts -p ActiveEnterTimestamp -p MemoryCurrent -p CPUUsageNSec --no-pager
  journalctl -u "$u" --since "-24h" --no-pager 2>/dev/null | grep -ciE '429|too many requests' | sed "s/^/$u 429-lines-24h=/"
done
for d in ${H038_DATA:-} ${H039_DATA:-}; do echo "$d: $(du -sh "$d" 2>/dev/null | cut -f1), newest file $(find "$d" -type f -printf '%TY-%Tm-%TdT%TH:%TM %p\n' 2>/dev/null | sort | tail -1)"; done
echo "== existing M6 footprint"; ls -la /srv/m6_paper /opt/m6_paper 2>/dev/null || echo "none"
