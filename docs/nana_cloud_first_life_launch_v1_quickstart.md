# First-Life development entry and remaining gates

Run from the repo's existing `.venv`. This is independent development, not a live
Nana deployment. Existing RAE/CDL qualification is inherited; no private history,
old key, QQ/Bili account or user device is needed. GLOBAL_STAGE remains H.

## Inspect actual storage

While the original headless Runtime is running with `--control`:

```bash
printf '%s\n' '{"operation":"view","view":"storage"}' | .venv/bin/python -m nana_core.life request --home <explicit-private-home> --json
.venv/bin/python -m nana_core.life health --home <explicit-private-home> --json
```

Use actual paths instead of placeholders. Numeric storage projection shows DB
pages, reusable free pages, WAL/SHM/privacy sidecar sizes, largest tables/indexes
and event-kind byte counts for the latest4096 events. It does not return payloads.
Events, lineage, outcomes/actions, UNKNOWN and deletion journal are retained.
Memory search terms and life/context views are rebuildable; operational logs may
rotate. WAL pages may be checkpointed/reused. There is no automatic audit pruning
or unverified history archive.

Host `life.json` settings add `max_state_mb` (default256),
`max_state_growth_mb_per_hour` (32), `storage_review_seconds` (60),
`storage_growth_grace_seconds` (600) and `storage_growth_window_seconds` (600).
These are additional host ceilings, never Grants or personality instructions.
Growth is measured from logical database pages plus the deletion anchor; physical
family size includes WAL/SHM and the actual anchor. The first growth window is
startup grace; subsequent windows enforce the rate. Measurements and stop state
persist in private host-local `storage-monitor.json` across restart, excluded
from the original three-file B8 package.

PASSIVE checkpoint never forces a pinned reader out. A hard/rate breach is
latched and stops the writer before it accepts new control/chat events after
restart. Corruption/clock conflict fails closed. Health exposes the stop state.
Do not delete Subject history or blindly reset this host monitor to resume.
A trusted offline operator must first inspect the cause, capacity and policy;
changing a resource limit does not renew old execution Grants or replay effects.

## One private chat client, same running Subject

The existing CDL quickstart creates an explicit fresh home and headless Runtime.
Include `--daily-life` when initializing to bind `cloud.cli` and two shadow
entrances. Then a separate terminal can attach without starting another Runtime:

```bash
.venv/bin/python -m nana_core.life chat --home <explicit-private-home> --privacy PROJECT
```

Use only approved PUBLIC/PROJECT content. This flag does not authorize relabeling
private content as PROJECT. No PERSONAL/SECRET or private-history import is
approved. The client uses a private same-UID socket, current lease PID and fresh
event IDs, and never retries an uncertain request. `/quit` exits the client only;
the original Runtime continues. Body/history is volatile and not saved as a
transcript. Ctrl-C/EOF does not start or kill another Subject.

Without an explicitly configured/authorized real provider, this entry states its
limited offline behavior. It cannot qualify naturalness. A provider must first
receive **new** permission and a safe FD/SecretResolver binding, approved endpoint,
model, PUBLIC/PROJECT scope, call/cost ceiling and timeout. No old Key/UNKNOWN
request is reused or searched. Configure host-local providers using the existing
ProviderCommand/CAS service; credentials never go in JSON or command arguments.
A running offline qualification harness is not silently converted into a paid
chat session. Stop/requalify the authorized runtime deliberately and preserve its
same home/lineage and unresolved reservations.

## Human-authored structured ratings

After actual real-provider free conversation, the user may submit a strict JSON
rating through stdin:

```bash
.venv/bin/python -m nana_core.life review --home <same-home> --json < <explicit-local-rating.json>
```

Fields: `review_id` (fresh UUID), `identity_id` (actual Subject UUID),
`category` (`NATURALNESS` or `SHARED_LIFE`), `observed_minutes`,
`naturalness/grounding/continuity/boundaries` (integers1–5),
`excessive_analysis/unsupported_experience` (booleans), `result` (`PASS` or
`NEEDS_WORK`), and fixed `reviewer=HUMAN`. No text/transcript/comments field is
accepted. The immutable0600 rating lives under home/human-reviews/; duplicate ID
or wrong identity is rejected. These are **human-declared operational ratings**,
not model evidence or an automatic FirstLife/Beta upgrade. A developer fixture
using this DTO is never proof a real user reviewed anything. Current real human
review remains NOT_RUN.

## Rehearse ownership and rollback without production

```bash
.venv/bin/python -m tools.nana_first_life.rehearsal --repo "$PWD" \
  --root /workspace/nana-staging/rehearsal-fresh \
  --output /workspace/nana-staging/rehearsal-result.json
```

Use a fresh root. This starts three **sequential** actual Core CLI processes as
synthetic legacy-role, new-owner and rollback-owner. It rejects transfer while
the old writer is active, stops it, retires the source through original B8,
activates the same Subject, accepts one inbound-only synthetic observation, then
rolls forward to a fresh rollback home. It never overwrites a newer lineage with
an old snapshot and never inherits old Grants. It is not a rehearsal on actual
AstrBot/QQ production; production inventory remains unobserved and unauthorized.

## Isolated staging

```bash
.venv/bin/python -u -m tools.nana_first_life.staging --repo "$PWD" \
  --root /workspace/nana-staging/first-life-fresh --seconds 86405
```

Use a new root. The supervisor runs the original CDL qualification runner with
one actual Core Runtime/Store and an owned external development app, source-frozen
finite work/learning, long idle, backup/deletion, actual SIGKILL and original B8
fresh-host transfer. No real provider/account/send/private data is used.
`progress.json` is refreshed operational metadata, not Subject truth. Only an
actual successful result after86400 seconds may become `PASS_24H_DEV`; short
runs say SHORT and interruption says PARTIAL. At completion the test source is
retired and the fresh-host result is paused with old Grants revoked.

This managed workspace's persistence/lifetime is not attested as a permanent
cloud server. Production requires a separately confirmed Linux host, durable
home/backup directories, credentials and inventory. Do not put a formal home in
/tmp. The dev runner's /workspace path alone does not prove disk durability.

Interrupt only the recorded supervisor process with SIGTERM; it signals its own
qualification child to clean up. Never kill by a broad process name. On lost
supervisor/environment, inspect progress/actual lease PID before resuming; never
launch a second writer, reinitialize its home or auto-regrant.

Production inventory, writer transition, real social delivery and cutover need
separate explicit approval. Do not ask for production approval before the real
provider/human/staging/inventory gates have concrete evidence.

## This checkpoint's long-run location

The pinned development build is `645899b32220e66a702e75d59a279a3a9685693f` at
`/workspace/nana-staging/first-life-source-645899b3`. Its isolated runner root is
`/workspace/nana-staging/first-life-24h-01`, with `progress.json`,
`qualification.log` and (only after successful completion) `result.json`.
The supervisor log is the adjacent `first-life-24h-01.supervisor.log`.

Do not edit/remove the detached worktree while it is running. On resuming work,
read progress, inspect the actual recorded owner and result/exit status, verify
unchanged source and measured duration, then update evidence/PROJECT_BRAIN with
observed facts. `RUNNING_NOT_QUALIFIED` is not a scheduled promise or a24h PASS.
If the environment disappears or the process fails, keep PARTIAL and do not
invent elapsed time. No auto-commit or automatic readiness promotion runs at the
end. Long-run source home is retired by B8; the fresh-host result is paused and
must be deliberately rebound/requalified before real use.

## Current DeepSeek authorization / host binding gate

User authorized DeepSeek, `https://api.deepseek.com`, requested `deepseek-flash`, OpenAI-compatible, PUBLIC/PROJECT only, at most20 calls/$1 equivalent. These are requested settings, not verified model/endpoint qualification. Historical TianToken UNKNOWN is independent and remains parked.

A personal-vault entry named `DEEPSEEK_API_KEY` is not yet a binding: current managed environment revision281 reports no secrets or runtime variables. This task exposes a status-only tool, no environment configuration mutation tool. Apply the secret binding using the Cloud environment configuration workflow and its user review; recheck current readiness before access. Do not paste the value or create a plaintext credential file. Once the host supplies the explicitly bound credential, pass it only through an in-memory pipe/FD to the existing `ExplicitFDResolver`; do not put its value in process arguments, JSON, logs or Subject data. No automatic credential discovery, no old-key reuse. Until bound, new live calls stay0 and human dialogue review remains NOT_RUN.

## Live functional qualification / private human entry (current checkpoint)

DeepSeek text path completed the six public/project fixture cases, with17 cumulative real calls including rejected/partial attempts. These are developer-observed functional results across documented configuration revisions, not human naturalness acceptance. The failed attempts remain failures and retain budget reservations. The old TianToken UNKNOWN is unrelated and parked.

The same development reference Subject as the first accepted DeepSeek probe is currently serving the original private IPC control entry (not production Nana or imported private history):

```sh
python -m nana_core.life chat --home /workspace/nana-staging/first-life-deepseek-01/life --privacy PROJECT --topic first-life
```

Only PUBLIC/PROJECT input is authorized. No private history, credentials or SECRET input. The client shows candidate wording directly and saves no transcript. There is no public URL/UI. The current memory-only credential process is bounded to7200 seconds and managed-workspace survival is not attested; if stopped, health fails and there is no automatic credential recovery/restart. There are3 remaining model-call slots, usually one complete2-call interpretation/render turn. Do not reset the configuration or create a new home to evade the20-call mission limit. A wider human conversation needs new budget permission after that limit; human review stays NOT_RUN until actually performed.

The host configuration now supports optional `provider_total_calls_limit` and `provider_total_reserved_cost_micro`, reusing original CognitionSession reservation records for lifetime limits. Qualification values are20 and1000000 nominal USD micro, with50000 reserved per attempt (including failures). This is conservative host accounting, not a verified provider bill or provider-side spend cap. Actual charge is UNKNOWN. Daily/hourly ceilings still intersect Runtime policy.

Qualification uses bounded context16384 and output2048 with the same ContextAssembler; default8192/1024 is preserved. Optional ProviderProfile `chat_thinking_mode` defaults to `PROVIDER_DEFAULT`; `DISABLED` explicitly emits the compatible vendor extension `thinking.type=disabled` for cognition only. Enable only for a provider with documented support; it is not assumed to work on every OpenAI-compatible service. DeepSeek support was checked at https://api-docs.deepseek.com/guides/thinking_mode/ . Changing host options is CAS/versioned and invalidates old route snapshots, never rewrites old requests or Subject identity.

The separate24h staging process remains pinned to645899b and does not use this provider credential. Check its actual `progress.json`/`result.json` before claiming duration. Beta/First-Life readiness remains blocked by human review and the remaining staging/production gates.

## Corrected review context (current; earlier live-entry notes are historical)

The previous entry is stopped. No live review runs automatically after this repair.
The existing reference home is now bound by host CAS to `current_project_state`:

```json
{"relative_path":"PROJECT_BRAIN/09_STATE.md","source_id":"project.mainline.current","scope":"project-work","privacy_class":"PROJECT","max_age_us":86400000000}
```

The selected file has one `CORE_PROJECT_CURRENT_STATE_V1` JSON header near its top; only that bounded header is projected, not the whole document. Maintain it in the same SSOT: increment revision and set a fresh `as_of_us` when factual mainline state changes. Stage/workstream/progress/open_gates/evidence_refs are bounded typed fields. No secrets, private history, developer logs or personal-experience attribution. Do not duplicate this header or substitute an unsourced cache. A stale/missing/corrupt source blocks the required query path; the result is also checked before dispatch and acceptance. Host binding is configuration, not portable Subject memory or execution permission.

Clear project-status queries now use PROJECT_STATUS inside the original SubjectLoop. Receipt metadata has no preset intent. The original topic-refusal gate still wins. Offline fixtures prove both model phases receive current state and preserve privacy/support/token rules. These tests do not demonstrate live wording or human naturalness.

Cumulative DeepSeek calls remain19/20; the last slot is deliberately unused. New paid review requires a new small authorization, explicit memory-only resolver/FD binding and unchanged PUBLIC/PROJECT scope. Do not run the qualification case runner just to open a review: it would spend calls on old cases. Reopen only the same existing paused reference home with the original bounded runtime entry after that authorization, using fresh message/request IDs and preserved reservations. Do not reset budgets, replay old UNKNOWN, or attach provider credentials to the separate24h staging.
