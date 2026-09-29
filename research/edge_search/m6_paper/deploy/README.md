# M6 deployment on the persistent `kalshi-collector` host: operator runbook

**Isolation from H038/H039.**
- Own system user `m6paper`, code in `/opt/m6_paper/releases/<manifest>`, data in `/srv/m6_paper`.
- Own logs (`/srv/m6_paper/logs`, syslog id `m6-paper`), own systemd unit, own resource caps: CPU 50%, 1.5 GB RAM, low IO weight, nice 10.
- No credentials in its environment; public GETs only; no order endpoints anywhere in the code.
- Nothing belonging to H038/H039 is read, written or restarted. The scripts only *query* their unit status and count 429 lines in their journals.

## Steps (as root, from a checkout of the repo at the frozen commit)

1. **Preflight (read-only).** This gives the headroom report the reviewer asked for.

       cd research/edge_search/m6_paper/deploy
       H038_UNITS="<units>" H039_UNITS="<units>" H038_DATA=<dir> H039_DATA=<dir> ./preflight.sh | tee preflight_report.txt

   GO criteria:
   - ≥ 40 GB free under `/srv` (the M6 upper bound is ~12.6 GB over 90 days);
   - ≥ 1.5 GB MemAvailable;
   - 1-min load < 0.7 × cores;
   - NTP synchronised;
   - Python ≥ 3.11;
   - every H038/H039 unit active, with no restarts in the last 24 h.

   **If any criterion fails, stop. Do not deploy.**
2. **Install (does not enable or start).** Run `./install.sh <MANIFEST>`. It refuses code whose hashes do not match the frozen manifest.
3. **Operational validation.**
   - Run `H038_UNITS=… H039_UNITS=… ./validate.sh <MANIFEST> 20`. It runs a 20-minute validation collection with a mid-way restart, as `m6paper` under the same caps.
   - It checks: manifest; absence of order code; restart recovery; 429 rate; recorded gaps; gzip integrity; clock; that the simulator refuses validation data; and H038/H039 before and after.
   - It then **deletes** the validation data. Only a sha256 list is kept in `/srv/m6_paper/quarantine`.
   - Return `/srv/m6_paper/logs/validation_<ts>.report` and `preflight_report.txt` to the reviewer.
4. **Start (only after final reviewer approval).**

       echo <MANIFEST> > /srv/m6_paper/APPROVED
       systemctl enable --now m6-paper-collector

   The unit's `ExecStartPre` refuses to start unless the APPROVED file equals the deployed manifest.

**Shared-IP caveat.** M6 and H038/H039 would share the host's public IP. If H038/H039 use the public API unauthenticated, their rate limit may be shared with M6's 2 requests/s. `validate.sh` counts 429 lines in the H038/H039 journals during validation. **Any increase is a NO-GO.**
