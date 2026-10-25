# Cloud / Web / APK integration — recommended controlled cutover

This is a deployment plan, **not an executed production change**. Actual FL-A
inventory is operator supplied; its private paths/identifiers are not copied.
The old cloud has **NO_CANONICAL_CORE_ON_HOST**. Developer subjects and shadow
UUIDs are not its existing identity. No private records were read here.

## Current selected topology — supersedes earlier systemd proposal

User fixed independent nonroot **Debian13 Docker**, UID/GID999, host
/srv/nana-core/{runtime,data,logs,backups} mapped to /opt/nana-core same four paths.
Preserve existing private SDK prefix /opt/nana-core/runtime. The later actual
read-only report retracts the claimed host-systemd check; it is not a gate now.
Old /opt and old /root backups are overlay and NOT persistent. Container-built
OpenSSL3.5.7 dependencies cannot be directly executed against Ubuntu3.0.13.
Reuse the existing SDK archive and qualify its actual imports inside the separate
image; do not repeat cloud compilation or add bz2/lzma. See docker/README and
cloud_followup_reconciliation.json for final source levels and preparation scope.

BFF stays independent at127.0.0.1:18765 and proposed private HTTPS8443 only after
network approval. Existing6199 routes/namespaces remain unchanged. No Funnel,
public Core/UDS, SSL bypass, docker.sock, host-root mount or old container restart.
The old systemd unit is retained only as a superseded development artifact.

## Build and inspect independently

`npm ci` in apps/nana-space, `npm run build:live`, then `npx cap sync android`.
JDK21, SDK35/platform-tools and build-tools34.0.0 (AGP8.7.2 default) are needed.
`cd android && ./gradlew assembleDebug testDebugUnitTest lintDebug --no-daemon`.
Wrapper8.11.1-bin has its official distribution SHA pinned. Local SDK paths,
Gradle/npm caches, signing keys, certificates, copied assets/build outputs are
not repository inputs. Debug package life.nana.space.dev is for internal use;
release life.nana.space is unsigned without the user's signer. There is no
fabricated production key. `tools/nana_first_life_android_v2/sign_release.py`
uses explicit password FDs and apksigner stdin, never password argv/env.

The SDK/JDK/Maven network workaround used here is a **build-only loopback public
artifact relay**, not part of the app. It caches only fixed Google/MavenCentral/
Gradle plugin repositories, uses normal TLS through the configured session proxy,
and does not relax APK HTTPS validation. For offline rebuild retain the exact
npm lock, Gradle dependency cache/verification metadata, SDK and JDK in a trusted
builder. Google/Capacitor/JDK licenses remain applicable.

## Existing home startup

Create a private0700 host-state directory and0600 typed HostConfiguration JSON
(as defined in `life/live_api/__main__.py`). Bind **existing** home, exact ID,
derived lineage, realm, scope/entity, fixed registered Release(s), Python, Web
root, exact private HTTPS Origin and roles. Host paths never come from APK input.
`python -m nana_core.life.live_api --config <private-host-json> --password-fd <n>`
creates only salted auth hashes, not an identity. Reopening uses persisted auth
hashes and new session generation. No environment secret discovery.

Live Provider construction requires a new, explicit host authorization/budget,
`--live-provider-authorized --secret-fd <n> --secret-ref <opaque-ref>`. Credential
is consumed from an inherited FD by ExplicitFDResolver; each original Core start
receives a private pipe. No plaintext config/argv/env/Store/evidence. Original
Provider routing, privacy, per-call/day/hour/total reservations and UNKNOWN
remain final. No current model calls or payment authorization are implied.

Production Release validation requires a clean pinned Git source, or a pinned
runtime integrity manifest plus each file digest. Runtime plan contract remains
PRECISION_V2/schema13. Upgrade/rollback accept only host-registered compatible
release IDs; explicit stop, original privacy/schema checks, then same-home start.
No active-plan hot downgrade, automatic rollback after UNKNOWN or identity init.
Preserve an independently verified backup before an approved production update.

## Canonical activation and legacy history

`canonical.plan` records inventory digest, source links and known missing history.
`create_genesis` is a trusted **offline** operator function, requires explicit
CREATE_ONE_CANONICAL_GENESIS_ONLY approval bound to plan digest and a nonexistent
home. Original LifeApplication/Store creates the sole identity. It emits a real
Core genesis event, not a legacy UUID claim, memory import or execution Grant.
An incomplete home after crash is quarantined for inspection; no automatic retry.

`activate` separately consumes an approval bound to the created ID/lineage and
verified fencing of AstrBot agent, Iris, livingmemory, proactive/social writers,
Bili act-pump, SelfEvolution cron and legacy command control. Include Docker
restart/plugin-reload/schedulers and independent receipt validation. The original
Core activation event binds approval/fence digests. Receipts are **trusted host
operator attestations**, not proof against malicious host root. DEV-marker homes
cannot be promoted. HTTP/APK has no genesis or activation endpoint.

Existing Iris exporter reads explicitly supplied **frozen snapshots**, bounded
100 rows per batch. `adapters.reconcile_legacy` validates hash-only manifests,
stable IDs, duplicates/conflicts, timestamps and unresolved links. Actual private
export/import is not performed or enabled here; old synthetic importer guards
remain. Approve exact source classes/retention/deletion/model privacy before
reviewing body mappings. Missing early L1 text and stale L2 coverage remain gaps.
Do not replay action ledgers or import old claims as current execution authority.
SQLite snapshots are individually consistent, not automatically a cross-file
transaction; use approved quiescence/cutoff and per-source snapshot times.

## QQ bridge and migration gates

`InboundConnector` binds authenticated sender metadata, original surface binding,
cutoff and event ID outside message text, enters the same original Core, preserves
platform provenance, and deduplicates by source event. It does not infer Manager/
PrimaryUser authority from content. Controlled tests use QQ-like PROJECT input,
not a live account. Real AstrBot transport deployment and private messages remain
unconnected; legacy Agent must be fenced before any real ingress/cutover. Real
social delivery is unavailable until original delivery Grant and separate cloud
approval are qualified. No new browser/APK social-send backdoor.

## Backup, recovery and rollback

API BACKUP uses the original owner's safe-point operation, returning a reference
and identity, not an arbitrary path. Original backup copies are review-quarantined;
restore/transfer uses existing portable stopped-home validation/lineage/fencing,
not copy-over-running-db. Credentials, host auth state and provider bindings are
not portable Subject truth. A restored host reauthorizes surfaces and execution.
Do not run old and restored active lineages together. If legacy cutover is rolled
back: stop/fence canonical writer first; preserve UNKNOWN and outbound receipts;
then restore the approved old-writer backup. Never replay pending social effects.

## Go / No-Go before production

NOT AUTHORIZED / NOT_RUN: nonroot/account/system provisioning; cloud build and
service install; new private HTTPS listener; actual old-writer fencing; canonical
activation; private Iris bodies/import; real QQ delivery; daily paid Provider
budget/credential; human naturalness; physical Android; release signing; background
push provider; cloud canary/72h. Inventory received is not these approvals.

Recommended next approval after dev delivery: **isolated cloud staging provision
only**, nonroot private Python/SQLite + BFF on18765 and separate approved private
HTTPS, without old-writer shutdown, canonical activation, private import, model
payment or social sends. Its exact shell/service/network diff should be reviewed
with the operator before execution. Rollback removes only that staging service/
listener and leaves existing AstrBot/QQ/root6199 untouched. Do not ask the user to
repeat FL-A inventory or send keys in chat.

## FL-A follow-up decision — 2026-10-25

User confirms the cloud operator prepared private CPython3.12.14/SQLite3.51.3
and a dedicated nonroot user **inside the current container**. This is accepted
as operator-supplied preparation evidence, not repeated or claimed as our direct
host execution. It does not establish persistence of /opt/nana-core, host ABI or
an independent service. `host_probe.py` provides a bounded read-only host check
(systemd PID1/state, explicitly selected Docker Mounts only, selected directory
ownership, actual isolated Python/SQLite/native import). No Store/private body or
Docker Env is read. Exact mounts/final-host execution remain pending evidence.

Recommendation stays **independent nonroot Ubuntu systemd**, not AstrBot/plugin,
nohup, temporary shell or old cron. If actual host systemd is unavailable, use a
separate nonroot Docker service with explicit persistent host binds for Subject,
host metadata and backups, read-only image/root, cap_drop ALL, no docker.sock,
no privileged mode, no host-root mount; qualify runtime INSIDE that final image.
Do not reuse AstrBot's writable layer or change its seccomp/CAP_SYS_ADMIN/restart.
Both choices still require explicit provisioning/network approval before install.

bwrap stays disabled/unqualified on that cloud environment; **Code Skills
BLOCKED**, never direct exec fallback. S9 route is preserved; future qualification
belongs to independent Core or dedicated skill executor. Other capabilities do
not inherit this block. bz2/lzma are not in current REQUIRED_PYTHON_MODULES;
no build or dependency installation is requested without an actual failure.
Existing verified runtime and nonroot preparation are not reimplemented.


## Actual supplied runtime qualified — 2026-10-26

The four-part transfer and exact SDK are now verified in isolated Debian13
Docker. See CLOUD_RUNTIME_VALIDATION.md for image digest, actual host-published
loopback path, cache-preserving offline installation, same-ID crash/recreate
and original B8 restore. New canonical-plan.json and activation-preparation.json
are review material only: approved=false is never fabricated, no Subject UUID
has been allocated for production. Safe cloud access remains absent. Before
any future approved genesis, reconfirm no real canonical home already exists.
No existing AstrBot/QQ/Iris or root6199 route was touched.
