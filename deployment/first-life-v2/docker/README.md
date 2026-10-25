# Selected independent Debian13 Docker — PREPARATION ONLY

Supersedes the previous systemd recommendation. Host /srv/nana-core/{runtime,data,
logs,backups} maps to container /opt/nana-core/{runtime,data,logs,backups}.
Existing runtime **prefix /opt/nana-core/runtime** is preserved. UID/GID999 from
the actual cloud report, no supplemental Docker group, root, docker.sock,
CAP_SYS_ADMIN, seccomp relaxation or old AstrBot restart. Core image runs read-only
with explicit data volumes, quotas and bounded Docker logs. The existing Core's
bounded runtime.log remains part of its persistent home, not a symlink bypass.
Backups must additionally use an approved original-home backup binding/collection
step after genesis; mounting a nested home before genesis would create the home
and must not be confused with an existing canonical identity.

Current cloud runtime/data/old backups are in overlay, not persistent. Only the
approved /AstrBot/data/_nana_core_handoff/ may now receive **non-sensitive** runtime
archive, Core archive, deployment instructions, checksums and qualification
results. Never copy Subject/identity/DB/private history/key/production backups.
Preparing that handoff is authorized; this workspace has no cloud access binding.
Do not claim to have copied there without actual access.

Both supplied audits were read. The later read-only evidence explicitly retracts
host-systemd verification; it is UNKNOWN and no longer a gate because Docker is
selected. Debian runtime uses OpenSSL3.5.7 from its old container; Ubuntu3.0.13 is
not a compatible direct host runtime. Candidate independent Debian13 must verify
actual ssl/hashlib/sqlite imports and loaded dependencies. Matching an OS name
alone is insufficient. Actual supplied cloud runtime archive is still required.

Build context must be the exact .dockerignore allowlist. `runtime.tar.gz` must
contain only relative runtime/... members from /opt/nana-core/runtime, with an
independent SHA256 and no data/config/key. `core.tar.gz` is the exact reproducible
portable Core archive; `unpack_core.py` is its trusted digest-checked unpacker.
Runtime extractor rejects traversal, escaping links, hardlinks/devices, sensitive
paths/credential patterns and oversized inputs. It never initializes a Subject.
The base target can build/verify OS dependencies independently; **this is not
actual supplied-runtime qualification**. Full target requires both exact digests
and fixed CORE_SOURCE_COMMIT. Use BuildKit secret CA mounts in managed builders;
never copy proxy certificates or credentials into image layers.

Full image copies the qualified SDK and offline-installed Core release at its
final absolute path. Before any approved service activation, operator exports
that same non-sensitive runtime tree into host /srv/nana-core/runtime, validates
file digests/UIDs/permissions and remounts it read-only. Do not mask the image with
an empty bind or relocate the SDK. Data/backup/host-config directories require
UID999 and private0700 subdirectories. No formal home is created automatically.

Default CMD=verify. It imports no Core, opens no Store, does no model call and
fails closed when runtime is absent/incompatible. `serve` needs an explicit
existing host config and original Supervisor's canonical approval/fence receipts;
no HTTP/APK genesis, import, old-writer shutdown or real social send. Compose uses
an inactive approval profile and `create_host_path:false`; it does not create
production folders or start a formal Subject merely by being delivered.

Restart policy restarts the infrastructure container, not semantic requests.
Original owner/lease/epoch, stop latch, UNKNOWN reservation, no replay/fallback,
identity/lineage and old-writer fencing remain authoritative. Healthcheck is
liveness only; authenticated Supervisor status provides actual Core readiness.
Upgrade requires stopped owner, verified backup, pinned compatible image/release,
source/privacy checks and same home. No automatic active-plan downgrade.

bwrap remains BLOCKED on cloud. No direct exec fallback, no extra old-container
privileges. S9 and other autonomous capacities are retained. bz2/lzma/readline
are not introduced as mandatory dependencies or new compilation work.
