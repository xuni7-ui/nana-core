# ADR-DV1-001 — One runtime schedules the existing subject

2026-10-15. Base ea65dabaa907b8bd777723d5ccc9527e1014d0c5. Offline development only.

D owns when C runs, not what Nana believes/wants. One NanaRuntime foreground
coordinator drains one persistent EventQueue, dispatches wakes and uses the
existing SubjectLoop for ALL judgments/intentions. No SocialLoop/GoalLoop or
reflection decision daemon. Model inference is optional, bounded and replaceable.

## Storage / authority contract

Same ContinuityStore, SQLite >=3.51.3, existing artifacts/privacy journal/replay
and single-writer flock. Explicit dev migration v8 adds runtime_lease,
runtime_queue, runtime_schedules and runtime_cognition_calls. No second state DB.
Lease/health are operational state, never Self Memory. Lease heartbeat uses a
short operational transaction without changing the cognitive event stamp; queue
and schedule changes use the existing event/projection transactions.

Acquisition requires the existing exclusive local Store lock. Each acquisition
increments durable epoch and binds runtime_instance_id/PID/process-start/boot
identity. Transactions on a runtime-managed Store require the active instance's
fence before BEGIN and before COMMIT. Expired/lost owner cannot renew or commit
C decisions. Zombie retaining file lock blocks takeover rather than risking two
writers. New process with lock can recover old in-flight queue state. Official
backup/replay is quarantine and cannot acquire live runtime authority.

This is local Store authority, not distributed consensus. Network filesystems,
privileged raw copies, hostile root and independent clones are NOT supported
single-writer proof. Cross-machine migration must shut down/quarantine old writer
and transfer one canonical Store; there is no partition failover feature.

RuntimeClock = injected UTC + monotonic elapsed + persisted high-water. Rollback
cannot revive expired work. Source occurrence time stays source time. Timers
persist UTC deadlines; process monotonic values are never reused across boots.

## Queue and scheduler

READY/DEFERRED → PROCESSING → DONE/IGNORED/EXPIRED. PROCESSING after crash checks
existing subject cycle before retry: committed cycle is acknowledged once;
uncommitted C transaction resumes idempotently. Queue source key and optional
stream/sequence dedup persist. Capacity/backpressure bounds nonterminal queue.
Only known synthetic source/event DTOs accepted. No execution command payload.

C's existing admission boundary owns retention. Kept input references its existing
deletable subject record; timer payloads with memory refs use that same record
lineage. Unretained/DO_NOT_REMEMBER bodies are never durably queued. Their replay
uses a metadata-only envelope and cannot recreate discarded content. Erased or
stale supporting sources retire queued work. No raw body in queue audit rows.

Scheduler emits source-linked one-shot/deadline/low-frequency review/condition
check events. Periodic lateness coalesces to one occurrence; no catch-up storm.
Unresolved-source wakes have stable condition IDs, terminal once fired. A timer
is a check opportunity, not motivation or execution permission.

## Cognition / outage

NO_COGNITION = lightweight time/projection update only. LIGHT_COGNITION = C cheap
policy. FULL_COGNITION = frozen existing ModelPort proposal then C validation.
Daily attempt budget, persistent reservation, cooldown and failure backoff;
reserved calls after crash become UNKNOWN and are never auto-retried. Other
lightweight runtime work continues. Runtime call ledger contains operational
IDs/holds/status, not another copy of context/private memory. Existing S5 HTTP
CallLedger remains an evaluation-specific separate ledger, not silently reused
for lifelong context persistence. Real endpoint integration is NOT_RUN.

Model resources run in short supervised fixture subprocesses with bounded JSON,
timeout, termination/reaping and progress heartbeat. No Store/authority handles
cross the boundary. No thread can later mutate subject state after a timeout.
Health/lease heartbeats cannot invalidate otherwise frozen cognition. Subject
mutations/events do invalidate it through the existing context freshness stamp.

## Small C extension required by D scenario

C-V2 has SOCIAL_INTERACTION enum, not a complete SocialInteractionProposal policy
or InteractionLesson. Add source-backed generic memory cues (interest/discovery/
relationship topic), semantic social proposals (no fixed utterance), and an
independently checked interaction feedback rule to the SAME C/Experience/Reflection
services. No source cue is authority. Shared-joke history may support TEASE;
privacy/boundary/availability/urgency may instead require ASK/WAIT/SILENCE.

A teasing hint is NOT authorization to read a directory. The scenario separately
supplies an exact synthetic standing-delegation snapshot; only an ordinary
synthetic resource is eligible. Credentials/payment/other-person secrets,
unknown or forbidden resources remain denied. D creates only a synthetic read
proposal; an explicit world fixture returns observation. Never actual file access.
Interaction feedback must bind an actual prior proposal and independently recorded
synthetic reaction; model success claims cannot enable a lesson or authority.

## Verification gates

72 virtual hours without user input; 30 virtual mixed days; actual bounded
wall-clock process run/scheduler/heartbeat/SIGKILL/restart/stop; source-bound
folder-curiosity narrative plus interaction-lesson ablation. All real models,
hosts, private data, social delivery and E/G actions remain NOT_RUN.

Commit sequence: D0 facts/contract; D1 lease/queue/scheduler; D2 coordinator/model
budget/CLI; D3 C cue/social/interaction-learning integration and synthetic ports;
D4 system scenarios/recovery fixes; FINAL full regression/evidence/manifest.
No blocking architecture ambiguity identified; no change to C-V2 invariants.
