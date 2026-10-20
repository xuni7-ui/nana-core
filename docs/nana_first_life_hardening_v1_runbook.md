# First-Life development runbook — prepared, NOT STARTED

Applies only to an explicitly selected isolated development home. Never use the
original `first-life-24h-01`, production, a user desktop, or an imported private home.
Foundation and human integration qualification remain separate. Exact executable
commit must be recorded before launch; host configuration is not Subject identity.

## Gate and entry (three commands after separate gate release)

1. `python -m tools.nana_first_life_hardening.preflight --repository .`
   returns the committed Matrix gate, current HEAD and remaining criteria. It never
   starts anything. OPEN exits 2. S4 requires the original actual final artifact;
   elapsed progress alone cannot release it. This mission does not release First-Life.
2. After Foundation closure and explicit integration start: use the existing
   `python -m nana_core.life init --home /tmp/nana-first-life-dev --project "$PWD" --demo-materials --daily-life --json`
   only for a **fresh** home. Initialization has no provider or external action authority.
   Never initialize over an existing Subject or confuse this synthetic home with
   the reference Subject. Continuing an existing Subject uses its existing home.
3. `python -m nana_core.life run --home /tmp/nana-first-life-dev --headless --control --seconds 600 --json`
   runs foreground, one writer; bounded offline mode. No new provider use, social
   send or Hands authority follows from starting the process.

Use the pinned checkout's Python environment. Do not mix code revisions during a
residency. Ordinary stop/restart uses the same home and identity. Do not run two
checkouts against one home or copy a running DB manually.

## Observe, pause, stop, restart

- Health: `python -m nana_core.life health --home /tmp/nana-first-life-dev --json`.
  Process readiness is not Beta readiness or provider quality qualification.
- Inspector: `python -m nana_core.life.inspector --home /tmp/nana-first-life-dev --scope project-work --entity project-user`.
  Finite read-only metadata, not another Runtime. UNKNOWN means insufficient current
  support, unavailable source or bounded coverage; do not synthesize a motive.
- Pause: send `{"operation":"control","command":"pause"}` to the existing
  `python -m nana_core.life request --home /tmp/nana-first-life-dev --json` via stdin.
  Resume uses `resume`; stop uses `stop`. No shell is executed by IPC.
- Emergency stop: foreground Ctrl-C/SIGTERM **of the verified dev owner only**.
  For a killed process, restart the same home after original PID/epoch checks;
  UNKNOWN effects remain UNKNOWN, never replay automatically.
- After stop, restart command 3; Inspector identity must match the pre-stop identity.
  A different identity is a stop condition. Never reset/reinitialize to hide it.

## Chat and credentials — not authorized by this runbook

The existing private PUBLIC/PROJECT chat entry is
`python -m nana_core.life chat --home /tmp/nana-first-life-dev --privacy PROJECT`.
Do not run real dialogue review until Foundation/integration gates and fresh
provider budget/credential authorization permit it. Do not reuse chat keys. A
trusted host supplies an explicit pipe/FD into the existing SecretResolver;
credentials must never be argv values, files, environment/config, logs or Store.
Missing resolver: stop only the live subgoal. No automatic retry/fallback after
UNKNOWN. Never expand the 20-call historical budget or consume this mission's
zero paid-call allowance. Human review remains NOT_RUN until actual observation.

## Backup, restore, rollback, logs and cleanup

- Active backup: existing IPC `{"operation":"backup","name":"before-review"}`.
  Read-only Inspector is not a backup tool. Backup is quarantined, not runnable.
- Stopped backup: existing `python -m nana_core.life backup --home /tmp/nana-first-life-dev --destination /tmp/nana-first-life-review.db --json`.
- Transfer/restore: existing B8 `transfer --retire-source` / `receive` protocol,
  expected package digest, explicit destination ID and fresh host configuration.
  Do not copy secrets, runtime handles or Grants; do not activate a review backup
  by editing quarantine. Validate deletion anchor, lineage and pending UNKNOWN.
- Rollback: stop the verified development writer, retain failure evidence, choose
  the previous tested code commit in another checkout, and reopen a compatible
  current home. No schema downgrade, stale DB overwrite, Grant resurrection or
  second active restored instance. If migration is involved, use existing verified
  quarantined restore procedures; no migration is introduced here.
- Logs: bounded `runtime.log`/`.1`, command summaries and sanitized metadata only;
  never paste conversation/model payloads or credentials. Inspector does not write logs.
- Evidence: exact commit, identity, epoch, source IDs, states, independent effects,
  test reports and user-authored ratings separately. Developer changes are not
  Nana learning; HTTP success is not human naturalness.
- Cleanup only the explicitly created disposable dev home after its verified
  process stops and evidence is retained. Never remove the old untracked bundle,
  original staging, privacy anchor, provenance or UNKNOWN to make tests green.

## Interpret the boundary

`RESTRAINED` is C's own decision; `MANAGER_BLOCKED` is a post-judgment veto;
`ACTION BLOCKED` is an execution gate result. Compare original cycle/disposition
refs with gate/Action metadata. Manager PASS is no Grant. Inspector intentionally
omits raw purposes, private surprise content and governance prose. Missing metadata
is UNKNOWN, not “Nana never wanted it”.
