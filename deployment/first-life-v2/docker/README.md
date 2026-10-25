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
not a compatible direct host runtime. The exact supplied archive has now passed isolated Debian13 ssl/hashlib/sqlite,
loaded-library, validated TLS, nonroot four-volume and original Core lifecycle
qualification. Matching an OS name alone remains insufficient; see
../../../docs/nana_first_life_android_v2/CLOUD_RUNTIME_VALIDATION.md. Actual cloud
production deployment is NOT_RUN.

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
The original BFF keeps its loopback-only listener at container TCP18765. A
fixed infrastructure-only relay forwards container TCP18766 to that loopback
port; Docker publishes **host 127.0.0.1:18765 -> container 18766**. It copies
bytes without changing Host/Origin/authentication, has at most eight connections,
bounded buffers and idle/lifetime deadlines, and exits with the original BFF.
It is not a second Core/SubjectLoop. Container-local health alone does not
qualify host published-port reachability; qualify the published path separately.

For an already approved first login initialization, the sole optional entry is
`serve --password-fd 0`: provide only that password through an anonymous pipe
into `docker run -i` with the same approved image, mounts and restrictions.
Do not put plaintext in argv, environment, Compose, files or logs, and do not
attach a TTY. The original gateway consumes its existing bounded input; the relay
never reads it. Reopen after initialization with plain `serve`, which reuses the
existing credential hash. This delivery does not authorize first activation,
genesis, a real password or production changes.

Original owner/lease/epoch, stop latch, UNKNOWN reservation, no replay/fallback,
identity/lineage and old-writer fencing remain authoritative. Healthcheck is
liveness only; authenticated Supervisor status provides actual Core readiness.
Upgrade requires stopped owner, verified backup, pinned compatible image/release,
source/privacy checks and same home. No automatic active-plan downgrade.

bwrap remains BLOCKED on cloud. No direct exec fallback, no extra old-container
privileges. S9 and other autonomous capacities are retained. bz2/lzma/readline
are not introduced as mandatory dependencies or new compilation work.
