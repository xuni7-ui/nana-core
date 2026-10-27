# Unified First-Life release — continuation, not a second Core

This extends First-Life Android V2/rev3 release delivery with the complete
9217e3f descendant of Real Living 7a1bce9. No duplicate release was found locally
or in fetched remote refs. Host Operator and CotEX branches remain independent.

The image derives from the previously qualified exact image
`sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee`.
It preserves Debian13, private CPython3.12.14 at `/opt/nana-core/runtime`, SQLite
3.51.3, OpenSSL3.5.7 and the original Web. Adds the hash-bound Core9217e3f release,
installed offline as UID999. ENV selects only the new release. Old release files
in inherited layers are inert; there is no automatic fallback or second Runtime.
This is not CotEX V3 UI integration or a newly authorized production activation.

## Handoff checks (safe preparation only)

1. Download all image parts and `image.json` from artifacts/first-life-unified-release.
   Run `python tools/nana_first_life_unified_release/verify.py <directory>`.
2. Concatenate parts in manifest order and pipe to `docker load` (gzip accepted).
   Inspect loaded image ID against image.json, architecture linux/amd64, User999:999.
   Default `docker run --rm --network none --read-only --cap-drop ALL <image-id>`
   verifies SDK only; it does not create/open a Subject. Do not invoke serve yet.
3. Use existing rev3 safe runtime export/install workflow: extract the complete
   non-sensitive `/opt/nana-core/runtime` from this exact image into a fresh staging
   tree; verify hashes/links, restore private release UID999 ownership and permissions.
   Runtime includes new `core-releases/9217e3f3550dc5a875c42ac6de53035dd73deae2`.
   An old or empty `/srv/nana-core/runtime` bind will hide the new release and must
   not be accepted. No system Python modification, LD_PRELOAD or SQLite substitution.
4. Keep host `/srv/nana-core/{runtime,data,logs,backups}` mappings to the same
   `/opt/nana-core/` directories, runtime read-only, writable data999:999/0700.
   Keep original compose profile inactive, host publication127.0.0.1:18765→18766,
   private HTTPS only, no Funnel, hostroot, Docker socket or AstrBot mounts.
5. Before any later approved activation, preserve existing canonical plan binding,
   stop/owner/lineage fences, backup and exact existing identity. Update approved
   host release entries to new root/Python/source pin, not a new Subject. Existing
   production home must never be initialized by this developer qualification tool.
   Keep old verified runtime/image for rollback; no active-plan hot downgrade.

Formal Genesis, existing canonical service activation, private history, old-writer
switch, QQ delivery and real model allowance still require their existing gates.
The isolated lifecycle creates an explicitly DEV fixture only. Do not run it on
`/srv`, existing identities or production data. Bwrap remains BLOCKED.

## Reproduce

Build exact portable Core with existing build.py --revision9217e3f(fullSHA in manifest)
and pinned wheelhouse. In a clean Docker context place core.tar.gz, trusted original
unpack.py and the checked-in unified Dockerfile. Verify original base image ID first.
Build with --network none --pull=false --build-arg CORE_SHA256=<build.json digest>.
No public CA/credentials are baked in; this overlay build performs no network access.

Run qualify.py --source <fullSHA> --image <built-image> --work <fresh-owned-dev-dir>
--web-sha2568d55d97d59b6cefef74fe18651092960ac3fd5b3399606ee19b07f098a0fc90c
(with a space between flag and value). It reuses the original harness and tests
published HTTP, login, ten pages, original C offline chat, crash/recreation/backup/
B8 same-identity recovery and old-source fencing. It performs zero provider calls.

## Actual scope and limits

See evidence/lifecycle.json and abi.json. Real cloud host deployment and physical
Android/private HTTPS pairing are NOT_RUN here, not inferred from isolated Docker.
TLS CERT_REQUIRED is checked locally; the unchanged SDK's earlier live TLS evidence
is inherited, not described as a new external TLS test. Human naturalness NOT_RUN,
First-Life NOT_READY/BetaNO. Master/63criteria/schema13/43tables/Manager unchanged.
First image attempts failed on development disk exhaustion; raw logs retained.
Only rebuildable local cache and this run's temporary copied SDK were cleaned.
