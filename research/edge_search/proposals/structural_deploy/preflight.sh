#!/usr/bin/env bash
# structural_arb pre-deployment check for a DEDICATED host. READ-ONLY: changes nothing.
# usage (as root): FORBIDDEN_IPS="<public IP of the M6/H038/H039 host> ..." ./preflight.sh | tee preflight_report.txt
# GO requires ALL of:
#   G1 >= 100 GB free on the filesystem holding /srv       G2 >= 4 GB MemAvailable
#   G3 1-min load < 0.7 x cores                             G4 NTP synchronised
#   G5 python3 >= 3.11 with `requests`                      G6 public API reachable (HTTP 200)
#   G7 host separation: this host's public IP is not in FORBIDDEN_IPS, and no M6/H038/H039 unit or
#      directory exists here (m6-paper-collector, /srv/m6_paper, and any unit named in FORBIDDEN_UNITS)
set -u
fail=0; ok(){ echo "GO    $1"; }; no(){ echo "NO-GO $1"; fail=1; }
echo "== structural_arb preflight $(date -u +%FT%TZ) on $(hostname)"
free_gb=$(df -B1 --output=avail /srv 2>/dev/null | tail -1 | awk '{printf "%d",$1/1e9}')
[ "${free_gb:-0}" -ge 100 ] && ok "G1 /srv free ${free_gb} GB" || no "G1 /srv free ${free_gb:-?} GB (< 100)"
mem_gb=$(awk '/MemAvailable/{printf "%.1f",$2/1e6}' /proc/meminfo)
awk -v m="$mem_gb" 'BEGIN{exit !(m>=4)}' && ok "G2 MemAvailable ${mem_gb} GB" || no "G2 MemAvailable ${mem_gb} GB (< 4)"
cores=$(nproc); load=$(cut -d' ' -f1 /proc/loadavg)
awk -v l="$load" -v c="$cores" 'BEGIN{exit !(l<0.7*c)}' && ok "G3 load $load / $cores cores" || no "G3 load $load / $cores cores"
[ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ] && ok "G4 NTP synchronised" || no "G4 NTP not synchronised"
python3 -c 'import sys, requests; sys.exit(sys.version_info < (3, 11))' 2>/dev/null && ok "G5 $(python3 --version) + requests" || no "G5 python3 >= 3.11 with requests"
code=$(curl -s -o /dev/null -w '%{http_code}' https://api.elections.kalshi.com/trade-api/v2/exchange/status)
[ "$code" = "200" ] && ok "G6 Kalshi public API HTTP 200" || no "G6 Kalshi public API HTTP $code"
myip=$(curl -s --max-time 10 https://checkip.amazonaws.com | tr -d '[:space:]')
sep=1
[ -z "${FORBIDDEN_IPS:-}" ] && { echo "      FORBIDDEN_IPS not given"; sep=0; }
for ip in ${FORBIDDEN_IPS:-}; do [ "$ip" = "$myip" ] && sep=0; done
for u in m6-paper-collector.service ${FORBIDDEN_UNITS:-}; do systemctl cat "$u" >/dev/null 2>&1 && { echo "      unit present: $u"; sep=0; }; done
[ -e /srv/m6_paper ] || [ -e /opt/m6_paper ] && { echo "      M6 directories present"; sep=0; }
[ "$sep" = 1 ] && ok "G7 separate host (public IP $myip)" || no "G7 host separation (public IP ${myip:-unknown})"
echo "== details"; nproc; free -m | head -2; df -h /srv 2>/dev/null | tail -1; ls -la /srv/sarb /opt/sarb 2>/dev/null || echo "no existing sarb footprint"
[ "$fail" = 0 ] && echo "PREFLIGHT: GO" || echo "PREFLIGHT: NO-GO (do not install)"
exit "$fail"
