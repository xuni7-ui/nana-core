# Nana Living V4 — one matched delivery

This package prepares a compatible new release slot. It does not recreate the
formal Subject, replace its Store, fence QQ or authorize model/social spending.
Keep the present service and rollback image until a separately approved switch.

## Prepare on the Docker daemon host / explicit Host Operator

Use the unpacked `NANA_CORE_LIVING_V4_RELEASE` directory. Python 3.10+ stdlib,
access to the explicitly authorized local Docker socket and the existing
root-owned `/srv/nana-core` are required. Docker CLI is not required. Do not
mount that socket into the ordinary Core/BFF/LLM container.

```sh
cd NANA_CORE_LIVING_V4_RELEASE
sha256sum -c SHA256SUMS
./deploy.sh --check
./deploy.sh --dry-run
./deploy.sh --install
./deploy.sh --install
```

The first two commands never alter existing host data. A not-yet-loaded image
is reported explicitly. Install streams the delivered gzip parts to Docker,
checks the exact image, stages `/srv/nana-core/slots/<source>/runtime`, preserves
numeric owners, validates every entry, then verifies the installed read-only
mount with the same private Python/SQLite/OpenSSL/Pydantic used by Core.
Success is `READY_FOR_SWITCH`, never `ACTIVE`. Repeat success is idempotent with
zero persistent changes. Conflict reports name the file, expected/actual digest
and reason; no overwrite/automatic repair of sealed slots occurs.

The disposable staging Operator runs as root only to preserve original numeric
owners; it has no network, Docker socket, Subject handle or service-control API.
The eventual ordinary service stays UID/GID999, cap-drop ALL, read-only root,
no-new-privileges and bounded CPU/RAM/PIDs. The matched image is Nana/Debian13,
not AstrBot. No global Ubuntu OpenSSL or system Python change is needed.

## Preserve the existing binding before a live switch

If `data/host/host.json` exists with private permissions, preparation writes a
typed **proposal only** beside the new slot. It appends a release candidate,
preserves every old release, active alias, identity, activation, role and budget,
and points Web at the matching archive. It does not install this proposal.
If the actual host path differs, or the original DTO rejects it, stop and use
`python3 -B tools/host_facts.py` to reconcile metadata. Do not guess or copy a
different Subject. The host-reported `30845fb` and hotfixes must be compared
before replacing the live BFF, which this development environment cannot access.

After approval, the Host Operator must back up the current private configuration,
retain its hash/owner/mode and original Compose topology, register the validated
proposal in the original authenticated Supervisor, and switch the existing
service to the new image plus the new read-only runtime bind. Keep `/srv/nana-core`
data/logs/backups mappings, `127.0.0.1` BFF and private Tailscale HTTPS8443. Do not
create a competing Compose project or change the existing writer/identity token.
No Funnel/public control exposure is part of this release.

Use `preflight` on the matched image with the **existing** binding and volumes
before start. It reports actual namespace/UID, schema13, DB checks, management
roles, unresolved requests and provider configuration without an owner lock or
model call. Namespace-invisible owners remain unverified. Health401 proves only
the authenticated gateway; inspect authenticated bootstrap and provider readiness
to establish Subject/route state.

## Upgrade / rollback through the original authority

For an already registered compatible release, use the original Host Admin
confirmation UI. The helper `tools/switch_release.py` reuses that protocol; the
wrapper's rollback mode accepts `--base`, `--subject-id`, `--release-id` and an
explicit `--password-fd`. It verifies identity/admin, performs original consistent
BACKUP with a verified receipt, requests one version confirmation and sends one
transition. UNKNOWN is never retried; inspect the original receipt. Never pass a
password on the command line/environment, restore an older live DB, or invent an
activation flag. Backups remain quarantined under the existing recovery policy.

The initial change of Supervisor image/runtime mount is a Host Operator operation,
not something a Core-version API alone can perform. Preserve the old image,
runtime and host configuration for an approved failure rollback. Schema13 and
PRECISION_V2 are unchanged; active plans must not be hot-downgraded to old formats.

## Android / Web

`nana-space-4.0.0-debug.apk` retains `life.nana.space.dev` and the original debug
signer. Cover-install, do not uninstall or clear application data. Existing
Keystore pairing persists. This release adds native memory-only credential input
and local speech, so this one native update is necessary; compatible server/Web
updates do not normally require a new APK.

Native credentials go from a protected Android dialog directly to authenticated
HTTPS and a bounded memory-only server resolver. They do not cross JS/localStorage,
logs/config/Store. Host Admin, native pairing, host opt-in, configured reference,
revision and original execution budgets all remain required. A deliberate Core
restart is required after binding; the parent BFF keeps the resolver in memory.
**BFF/container restart loses this binding** and requires explicit rebinding;
durable secure host-vault integration is not implemented or claimed. No model call
is authorized by configuring a key or route. Defaults and mission total ceilings
remain unchanged. Readiness is a local gate check, not paid HTTP qualification.

Before asking for a credential, the authorized Host Operator must have selected
`serve --live-provider-authorized` with the original approved route/privacy/budget.
Without that startup opt-in, a parent-memory binding cannot reach the Core child
and readiness stays `RUNTIME_PROVIDER_UNBOUND`. Set the approved startup mode
before input; restarting the BFF afterwards clears its memory-only binding.

ASR uses Android31+ on-device recognition only, if installed, and explicit mic
permission. Text remains a draft until Send. TTS chooses a local Chinese voice;
missing local service is unavailable, never an implicit paid/cloud fallback.
Physical phone speech/notification and real private HTTPS are not qualified by
this development build.

## Known external gates

No production service changed here. Actual cloud hotfix reconciliation, approved
Supervisor switch, safe model binding/budget, real ten-message dialogue, phone
pairing/speech, B1 PC backup, private history import, QQ/Bilibili account actions,
human review and formal24h life need their original permissions/environment.
The Bilibili addition supports bounded public metadata/search and original
source→World→Concern→C integration; metadata is not watching. Full autonomous
watching/DM/commenting is incomplete. Code skills remain blocked until bwrap is
actually qualified. First-Life/Beta are not upgraded by this package.
