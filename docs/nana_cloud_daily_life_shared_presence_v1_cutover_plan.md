# One-owner Cloud Daily-Life cutover — prepared, not authorized/executed

Recommendation: one foreground Core home, one explicitly bound single-user
inbound shadow surface, then a reversible delivery canary only after all gates.
Never run the legacy decision/memory writer and new Core as concurrent Nana brains.

## Current facts and prerequisites

The repository documents legacy AstrBot/QQ and Bili assets. Their *current live*
PID/config/ownership, service names, credentials, network routes, actual traffic
and downtime characteristics were not inspected in this dev task and remain
UNKNOWN. No script in this work changes them. R045 and FIRST_REAL_ASTRBOT_SHADOW
are unchanged. Iris remains the legacy data boundary: no reading/importing its
private memories, and no second authoritative Core memory is attached to it.

Before recommending an actual switch, obtain a separately authorized bounded
production **read-only** inventory and verify the exact current writer and surface
ownership. Do not infer it from repository history. Required before cutover:

1. Fresh legal provider/safe SecretResolver + approved privacy/call/cost budget;
   real qualification and user naturalness/shared-life review pass.
2. At least24h isolated staging and a verified backup/restore rehearsal under
   actual host resource constraints. Unknown effects remain parked.
3. Exact service/host paths and owner identity, independent rollback checkpoint,
   readiness/health probes and monitoring of queue/DB/CPU/RSS/UNKNOWN.
4. Explicit selected surface/user/data classes/retention; permission to receive
   private content is not inferred from a role or a shadow fixture.
5. One final user approval of the concrete canary scope, production ownership
   transition, network/service changes, expected interruption and rollback.

## Recommended transition

Use the existing portable lineage path and a fresh private Core home on the
approved host. Provider credentials and platform credentials are injected as
separate host bindings, never in a SubjectPackage. No private history import by
default. No automatic pending old messages, actions or social candidates replay.

Prepare an inbound-only adapter from exactly one approved development/single-user
surface. It normalizes events to the existing SurfaceObservation/Subject path.
QQ/AstrBot is an Observe/Deliver adapter only; Bili metadata uses existing pure
normalization. Do not start legacy BiliAgent decision/execution as a second brain.
Network changes are limited to that explicitly approved adapter connection; this
version's Core control socket remains local/private, not an exposed internet API.

Pause the legacy writer and verify it actually lost decision/write authority
before activating the new authoritative home/lineage. Stop immediately if this
cannot be proven. Start one Core process, validate lease PID/epoch, identity,
source cutoff, pending verification and no old Grant headroom. A stopped old
runtime cannot regain authority through a generic service auto-restart policy.
No production systemd/container action has been performed by this task.

Start inbound-only: candidates visible to the operator, real sends0. Only after
the separately approved delivery gate may one recipient/surface receive bounded
new messages through explicit social Grant/receipt/Verify. Quiet/busy/refusal and
Manager veto are evaluated. UNKNOWN delivery is reconciled, never blindly resent.
Hands remains the existing owned-resource scope unless a separate target is
explicitly authorized/requalified; no user desktop or general browser enablement.

Observe a bounded canary before increasing duration; target72h only once the
actual approved environment supports it. Expected downtime is **UNKNOWN pending
inventory and rehearsal**, not a fabricated number. The developer rehearsal
measures process recovery, not production service downtime.

## Stop and rollback

Stop on duplicate writer, wrong lineage, missing privacy anchor, source resurrection,
unauthorized send, effect outside scope, blind retry/fallback, malformed ownership,
queue/DB/resource growth beyond measured guard, repeated spam or unsupported claims.
Revoke future delivery/effect Grants and disable the surface at its host binding.
Gracefully stop the new owner; preserve outcomes, UNKNOWN, deletion journal and
verification evidence. Never restore an older snapshot over a live newer writer.

Rollback re-establishes **one** explicitly fenced owner after reviewing any effect
that might already have occurred. A new Core lineage cannot simply be forgotten
while a stale legacy brain is restarted. Returning to legacy service requires
proof of stopped Core and an explicit operator decision about state continuity.
A backup is quarantined until writer fencing and authority are established.
No rollback path copies credentials or pretends physical effects did not happen.

No production command, login, deployment, credential retrieval, social send or
cutover is included. CLOUD_DAILY_LIFE_BETA_READY and FIRST_LIFE_EXPERIENCE_READY
remain NOT_READY until the complete technical, real-provider and human gates exist.
