# structural_arb: dedicated-host deployment runbook (PROPOSED, not frozen, not started)

This deployment package is modelled on M6's `deploy/`. It sits outside `research/structural_arb/`, so the experiment manifest `456eafb5…` is unchanged. It has its own deploy manifest (`../STRUCTURAL_DEPLOY_HASHES.txt`), which is frozen together with the experiment manifest.

**Isolation (D4).**
- A **dedicated host with its own public IP**, separate from M6 and from H038/H039. Preflight check G7 refuses a host whose public IP is listed in `FORBIDDEN_IPS`, or that has an M6 unit or directory, or any unit in `FORBIDDEN_UNITS`.
- Own system user `sarb`, code in `/opt/sarb/releases/<manifest>/repo` (a root-owned git clone at the frozen commit), data in `/srv/sarb`.
- Resource caps: CPU 100%, 3 GB RAM, nice 5.
- No credentials in the environment; public GETs only.
- The request limit is **unchanged** (`MAX_REQUESTS_PER_SECOND = 5`, burst 6).

## Steps (as root, from a checkout of the repo that contains the frozen commit)

1. **Preflight (read-only).**
   - Run `FORBIDDEN_IPS="<M6/H038/H039 host public IP>" ./preflight.sh | tee preflight_report.txt`.
   - GO needs G1–G7, including **≥ 100 GB free under `/srv`** (D6).
   - **If any check fails, stop.**
2. **Install (disabled; nothing starts).**
   - Run `./install.sh <COMMIT> <CONFIG_VERSION> <MANIFEST> <DEPLOY_MANIFEST>`.
   - It refuses unless the experiment files hash to MANIFEST, the deploy files hash to DEPLOY_MANIFEST, `config.py` carries the frozen CONFIG_VERSION, and the tree is clean.
3. **Operational validation (D8), at least 30 minutes, with a mid-way restart.**
   - Run `FORBIDDEN_IPS=… ./validate.sh 30`.
   - It re-runs preflight, both manifest checks, the no-order-code scan and the unit tests.
   - It then runs two collector parts under the service's user, caps and environment.
   - It reports totals only:
     - requests, 429s, cycle errors;
     - gzip integrity;
     - code identity (git SHA, dirty flag, CONFIG_VERSION on every record);
     - "N of N P2/P3 records reconstruct exactly";
     - integrity ratio;
     - terms-filing status per registry template;
     - memory peak;
     - footprint projected to 28 days.
   - It then **deletes** the validation data, keeping only a sha256 list in `/srv/sarb/quarantine`.
   - Return `preflight_report.txt` and `/srv/sarb/logs/validation_<ts>.report`.
4. **START: only after the owner's explicit approval of the frozen package.**
   - Run `./start.sh <MANIFEST>`.
   - It re-checks ≥ 100 GB free, writes `/srv/sarb/WINDOW` (START_UTC, END_UTC = START + exactly 28 days) and `/srv/sarb/APPROVED`, then enables the service.
   - The unit's `ExecStartPre` refuses to start unless APPROVED equals the installed manifest, WINDOW exists and both manifests re-verify.
   - `run.sh` passes the collector exactly the time remaining until END_UTC, so a restart resumes into the same data directory.
   - At END_UTC the collector stops. The service then exits 0 and is not restarted.
5. **During collection: operational health only (D3).**
   - Run `./health.sh`. It reads only the `ops` and `universe` streams, plus disk and unit state.
   - Nobody opens `candidates`, `counts`, `rule511`, `statscreen` or `books`, and nobody runs `sarb.report`, `sarb.reconstruct` or `terms_retro_report` before evaluation opens.
   - The collector's own log line includes a per-cycle P2 count. That is the number of candidates evaluated, not a status. Read the log only when diagnosing an error.
   - **No config, rate or code change during collection.** The only permitted operator actions:
     - restart after a crash or reboot;
     - free disk that belongs to nothing in the experiment;
     - stop the run if it harms the host, recording that as downtime.
   - Nothing in the health output is a reason to extend, shorten or re-run the window.
6. **Evaluation: once, when it opens at END_UTC + 24 h.**
   1. A human completes `late_filing_review.json` (§4.4 of the proposal).
   2. Run `sarb_ops.py evaluate DATA_DIR /srv/sarb/WINDOW <COMMIT> <CONFIG_VERSION> late_filing_review.json`.
   3. It computes the pre-specified verdict. Only after that does it attach the descriptive report.
