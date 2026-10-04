# Repository migration plan (rewards-platform → its own repo)

**Status:** PLAN ONLY. Not executed (founder direction, 2026-10-04). Execute **before** adding
provider credentials, production databases or other secrets.

## Why

The rewards company lives in `rewards-platform/` inside an unrelated Kalshi trading-bot repository
(D-001). That was a safe temporary choice. Before real secrets and integrations, it needs its own
repository: access control, CI, issue tracking, and an unambiguous canonical context for humans and
agents.

## Current state (verified 2026-10-04)

- All rewards work is on branch `claude/modest-newton-fxn557` of `oskaryouth-glitch/Kalshi-Quant-TeleBot`.
  It has **never been merged into the Kalshi `main`**, and no Kalshi files were modified.
- 6 commits touch `rewards-platform/` (plus `.github/workflows/rewards-platform.yml`, which lives
  **outside** the prefix).
- **No secrets committed.** A grep for secret/password/api-key terms finds only explanatory copy
  (partner page) and a test comment. `.env*` is gitignored; `.env.example` contains empty values
  only. Re-check with a history scanner (step 2) before trusting this.
- A workaround exists because of the Kalshi root `.gitignore`: `rewards-platform/.gitignore`
  re-includes `src/lib/` (the root ignores Python `lib/` dirs).

## Steps

1. **Founders create an empty private repository** (name per the cleared brand, D-004). Don't
   initialize it with a README, so the first push is clean.
2. **Scan history for secrets** on a fresh clone of the branch:
   `npx --yes gitleaks detect --source . --log-opts="--all"` (or trufflehog). Expect no findings.
3. **Extract history for the subdirectory** (built-in git, no extra tools):
   ```bash
   git clone --branch claude/modest-newton-fxn557 https://github.com/oskaryouth-glitch/Kalshi-Quant-TeleBot rp-extract
   cd rp-extract
   git subtree split --prefix=rewards-platform -b rewards-only
   ```
   This produces a branch whose root is the former `rewards-platform/`, preserving every commit that
   touched it (messages, authors, dates). Alternative with cleaner history rewriting:
   `git filter-repo --subdirectory-filter rewards-platform` (requires installing git-filter-repo).
4. **Push to the new repo:**
   ```bash
   git push https://github.com/<owner>/<new-repo> rewards-only:main
   ```
5. **Follow-up commit in the new repo:**
   - Move CI: copy `.github/workflows/rewards-platform.yml` from the Kalshi branch to
     `.github/workflows/ci.yml`; remove the `defaults.run.working-directory`, the `paths` filters and
     the `rewards-platform/` prefixes in artifact paths and `cache-dependency-path`.
   - Optionally remove the `!/src/lib/` re-include from `.gitignore` (harmless if kept).
   - Update README (remove "lives inside an unrelated repository"); record **D-0xx: standalone
     repository** superseding D-001; update REPO_MIGRATION status to DONE.
6. **Verify in the new repo:** `npm ci && npm run verify`; e2e with a Postgres; CI green on `main`;
   `git log --oneline | wc -l` shows the extracted commits; a recursive diff against the old
   subdirectory shows no differences except the follow-up commit.
7. **Hosting:** point the deploy at the new repo (root directory = repo root). Set environment
   variables in the host's secret store only (`.env.example` lists them). `DATABASE_URL` is a
   server-only secret; nothing secret may use the `NEXT_PUBLIC_` prefix.
8. **Leave the Kalshi repository untouched.** Don't merge `claude/modest-newton-fxn557` into Kalshi
   `main`. After the new repo is verified, the branch can be archived or deleted by the owner (a
   destructive step, so the owner decides).

## Secrets and environment

| Variable                                                       | Secret?               | Where                                                                                                              |
| -------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `DATABASE_URL`                                                 | **Yes**               | Host secret store; CI uses an ephemeral Postgres service                                                           |
| `NEXT_PUBLIC_*` (site URL, entity, address, contact emails)    | No (public by design) | Host env                                                                                                           |
| Future provider API keys, postback secrets, payout credentials | **Yes**               | Host secret store or a secrets manager; never in the repo, fixtures or tests; separate sandbox and production keys |

Add a secret-scanning step (e.g. gitleaks) to CI in the new repo before the first provider
credential exists.

## How Claude and Codex should use the new repo as canonical context

- **Single source of truth:** the new repository. Chat history is not canonical. Decisions live in
  `docs/DECISIONS.md`, current priorities in `docs/CURRENT_PHASE.md`.
- **Agent entry points:** `AGENTS.md` (read by Codex and other agents; contains project rules) and
  `CLAUDE.md` (imports `AGENTS.md`). Both stay at the repo root.
- **Session start:** read `README.md` → `docs/CURRENT_PHASE.md` → the docs relevant to the task.
  Run `npm ci` (consider a session-start hook) and `npm run verify` before committing.
- **Rules carried over:** copy guard, no fabricated data, no placeholder facts, integer money,
  LEGAL-001 statuses can only be changed by recorded counsel resolutions, raw provider data
  preserved.
- **Branching:** feature branches with PRs into `main`. CI must pass. Agents never push to `main`
  directly.
