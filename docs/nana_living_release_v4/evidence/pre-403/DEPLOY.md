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

`nana-space-4.0.1-debug.apk` retains `life.nana.space.dev` and the original debug
signer. Cover-install, do not uninstall or clear application data. Existing
Keystore pairing persists. This release adds native memory-only credential input
and local speech, so this one native update is necessary; compatible server/Web
updates do not normally require a new APK.

Native credentials go from a protected Android dialog directly to authenticated
HTTPS; they never cross JS/localStorage, logs or the Subject Store. The new
`HOST_VAULT` bundle feature supplies cryptography50/cffi/pycparser offline. The
matched Debian13 image qualifies those dependencies; generic portable bundles
without this opt-in still work but do not offer durable binding.

An authorized Host Operator may set the original HostConfiguration's
`provider_vault` to `/opt/nana-core/data/host/provider-vault` (host mapping
`/srv/nana-core/data/host/provider-vault`), outside the Subject `home`. The parent
must be private and owned by UID999. The service initializes a0700 directory,
0600 wrapping key and authenticated encrypted CAS document. Preserve this host
binding separately from Subject export: copying both key and ciphertext exposes
the credential to the holder. This does not protect against root/service-UID
compromise. Source/identity packages contain neither file.

The original approved `serve --live-provider-authorized` startup opt-in remains
required; no configuration or key creates spending authority. Native HOST_ADMIN
BIND/REVOKE fetch the current vault revision and preserve config/profile CAS.
After initial bind or rotation, explicitly restart the original Core child so it
inherits a new memory-only FD. BFF/container restart restores an already approved
binding without re-entering its value. Without `provider_vault`, bindings remain
memory-only. Shared-reference revocation first disables all dependent profiles,
then removes the active binding; it neither cancels dispatched calls nor proves
forensic erasure of old encrypted snapshots. Revoked/UNKNOWN requests never retry.

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


## Current API additions and platform bindings

Capability-gated APIv2 additions: `conversation/history`, `life/shares`,
`platform/bilibili`, `providers/credentials`. History restores only opted-in
original Person-Self speech; unretained text cannot be reconstructed. Shared
cards are original C-approved candidates with delivery NONE, not delivered
messages. Every projection intersects the paired binding's scope/entity/privacy
and source withdrawal. Existing clients may ignore these additive capabilities.

QQ/Bili ports reuse original Manager/Grant/Kernel and independent Verify. For a
real channel, the trusted host constructs PlatformActivation from the **existing**
canonical receipt fields plus a descriptive surface binding/account. No old
canonical approval file or digest changes. The channel is enabled and exact,
account matches, and exclusive-writer confirmation is required for writes.
Binding mode PLATFORM_ADAPTER_NO_SEND grants no sending permission: each send
still needs the original explicit capability/resource Grant, C judgment,
DeliveryAdmission and Manager PASS. Account Bili verifies NAV MID before its
duplicate precheck. Execution reserves3 requests; independent Verify another1.
QQ reserves account precheck+POST2 plus independent GET1. A failed account check
cannot mark an old matching post successful. Unavailable platform receipts keep
UNKNOWN; no resend, including after restart. Live platform effects are NOT_RUN.

Full source freeze/search/withdraw/review-plan tooling is delivered as
`tools/legacy_archive.py`; run it with the selected release's own interpreter
(including -I mode), not host Python with guessed dependencies. It requires
explicit file selection and Subject/lineage/hash pins. Real private read needs
its own approval. Plans do not import private history: original
RealMemoryIngress remains closed. Do not remove that fence or call a source
archive a second Subject Store.

See HOST_TASK_CARD.md for the one consolidated host handoff.


## Credential decoder and active-version compatibility

Current runtime source is c8aa8c986219199d0d027ccce0791788516e9d85. Its sealed
metadata declares secret_binding_contract2. The authenticated anonymous FD pins
vault path/revision/ciphertext digest; a running child rejects future selection
from its old snapshot after rotation/revoke/corruption, including cached targets.
The guard does not undo an already dispatched call. Do not fall back to an
unguarded FD to make an old binary start. An incompatible restart/rollback is
rejected before stopping a healthy Core. An empty vault may use the original
offline legacy path; original memory-only contract1 remains supported.

The new independent SDK seal retains13ddd484,af584900,3665d39,dbfb37e and current
c8. Old13/af archives are the exact original trusted archives, not relabeled
rebuilds. The image checks each Python/SQLite/OpenSSL/Pydantic binding atUID999.
This preserves available old versions; it does not grant all old binaries FD2
compatibility. A host active alias absent from the candidate, wrong ownership,
invalid state/integrity or unavailable interpreter returns
HOST_CONFIGURATION_REVIEW_REQUIRED with exact context before staging/reuse.
Neither configured nor persisted active aliases are silently rewritten. Actual
30845fb/hotfix compatibility still requires the host reconciliation in the card.
