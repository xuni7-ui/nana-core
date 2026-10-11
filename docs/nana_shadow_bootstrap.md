# Shadow Bootstrap blocker closure

## Evidence and scope

Development baseline: `8ff57a3a227ee1c35ed34cf314866300e34d01f8`. Approved, unmodified Core package remains `ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513`.

The user reports host Python 3.12.14 / SQLite 3.46.1 / Pydantic 2.13.5, Python3.13 using SQLite3.46.1 without Pydantic, no `/opt/nana_shadow`, and no approved package on that host. **No raw host report is present in PROJECT_BRAIN or the saved First Shadow evidence.** These are user-reported blockers, not independently host-tested facts. This task has no host channel, does not log in and does not inspect private records or credentials. Environment spec48 again has no configured host capability/credentials/outbound identity. First real Shadow remains BLOCKED_NO_HOST_CHANNEL; the old runtime gate would additionally reject the reported host versions.

## SQLite audit

No Core SQL syntax requires SQLite3.51.3. Source audit:

| Feature | Actual dependency and code |
|---|---|
| Schema/json_valid | `storage/schema_v1.sql`: JSON validity CHECKs; JSON1 predates 3.46, built-in since 3.38 |
| UPSERT/partial indexes | `storage/sqlite_store.py::_put`, schema live-goal/effect indexes; UPSERT since3.24, partial indexes since3.8 |
| PRAGMA/FK | Store uses foreign_keys, busy_timeout, journal_mode=WAL, synchronous=FULL, user_version, quick_check, foreign_key_check and table_info |
| Transactions | Explicit BEGIN IMMEDIATE/COMMIT/ROLLBACK, deferred FKs and append-only triggers |
| Backup/replay | Store.backup uses Python Connection.backup; replay rebuilds projections with INSERT/UPSERT |
| Python APIs | row_factory, setlimit, set_authorizer, progress handler, URI readonly/immutable; Python3.12 supplies the required binding APIs |
| RETURNING/STRICT/generated/window | Not used; receipt `STRICT_*` error names are DTO checks, not SQL STRICT tables |
| Migrations | Core schema_version1; replay/import/projection upgrades, no implicit production migration |

However, **SQLite3.51.3 is a WAL durability fix, not just a syntax version**. SQLite's official release notes and WAL documentation identify the WAL-reset corruption race, affecting versions3.7.0–3.51.2, fixed3.51.3 and later (also backported to3.44.6/3.50.7). It requires competing write/checkpoint connections. Store has a single-writer flock, but an external SQLite connection/checkpointer does not automatically obey that lock; other ledgers also use WAL. The current general storage contract does not prove all such accesses impossible. Ordinary regression/SIGKILL passing does not certify the race is absent. Therefore do not lower the production Store's gate just because SQL executes on3.46.1.

References: https://www.sqlite.org/releaselog/3_51_3.html and https://www.sqlite.org/wal.html#walreset. Fetched official evidence is recorded in `docs/nana_shadow_bootstrap_evidence/upstream_runtime_audit.json`. The original gate was not documented with this rationale; this audit supplies the concrete upstream durability evidence without claiming a locally reproduced corruption.

## Measured compatibility

The development experiment builds CPython3.12.14's actual `_sqlite3` binding from pinned official sources, statically linking actual SQLite3.46.1 or3.51.3. It does not replace a version string or mock SQLite. Source URLs, downloaded hashes and licenses are recorded. The 3.46.1 comparison will be separated from the supported Shadow runtime; no experimental gate exception is shipped.

Pydantic2.13.5 full regression: **291 passed / 1 skipped(E12)** on actual Python3.12.14/SQLite3.53.1. 29 DTO schemas/serialization/strict-extra-frozen error types have the identical aggregate hash under2.13.4 and2.13.5. Core uses optional/Literal response contracts; no discriminated-union discriminator is currently used. Accept only the measured patch interval `>=2.13.4,<=2.13.5`; runtime preflight explicitly accepts those two strings. No2.13.6/2.14 support is inferred.

The exact reported host combination was reproduced using CPython3.12.14's real binding statically linked to SQLite3.46.1, with Pydantic2.13.5: **144 passed / 65 failed / 82 setup errors / 1 skipped**. These failures retain the real Store/preflight gate; it was not patched to manufacture a pass. Separate low-level real3.46.1 schema/UPSERT/rollback/backup/SIGKILL-WAL checks pass. The upstream corruption race was not reproduced, and its absence is not inferred. Initial comparison harness failures were missing test subprocess PYTHONPATH, corrected in the harness without changing tests; initial logs remain separate.

## Isolated dependency runtime

Only SQLite reliability needs isolation. Reuse the already suitable host **CPython3.12.14** binary, in a temporary Shadow process. Privately load the standard-library `_sqlite3` binding built from official CPython3.12.14 and statically linked SQLite3.51.3; privately load fixed Pydantic2.13.5 wheels. This is an **isolated dependency runtime**, not a bundled full Python executable. It avoids shipping a large second interpreter and does not change the AstrBot process, system libsqlite, site-packages, venv, PATH or global LD_LIBRARY_PATH. Runtime entry is `run_shadow.sh`, an equivalent single入口.

Requirements: Linux x86_64, CPython3.12.14, glibc>=2.34. Build inspected actual ELF GLIBC symbol requirements, not just compiler host version. The real Nana host's architecture/libc was not supplied or measured; ABI compatibility remains UNKNOWN until selected-interpreter preflight. The bundle fails closed on a mismatch and performs no repair/install. All runtime source URLs, SHA256, compiler/flags, file hashes and licenses are included. SQLite and CPython are built from pinned official archives, not latest. Five exact wheels are checked against their PyPI release SHA256.

Preflight reports **HOST_GLOBAL_ENV** before private binding/dependency loading and **SHADOW_RUNTIME_ENV** after it. The latter decides adapter-local readiness. Select another reviewed executable with `./run_shadow.sh --python /known/python preflight`. No sensitive variables are configured.

## One-file upload and smallest host sequence

Recommended transport: upload the final `.tar.gz` using the server panel into a directory the operator already controls. This development session has no host transfer channel and does not upload to production. Obtain the archive and its SHA256 through the reviewed development delivery; verify that SHA256 before extracting. Do not use a checksum stored only inside an untrusted archive as proof of authenticity.

```bash
set -eu
mkdir -p /opt/nana_shadow
cd /opt/nana_shadow
sha256sum UPLOADED_ARCHIVE.tar.gz
tar -xzf UPLOADED_ARCHIVE.tar.gz
cd EXTRACTED_BOOTSTRAP_DIRECTORY
./run_shadow.sh preflight
./run_shadow.sh probe
./run_shadow.sh restart-check
./run_shadow.sh rollback
./run_shadow.sh collect
```

Use an equivalent independent user-owned directory if `/opt` is unavailable; no sudo/system install is part of the package. Every entry supports `--dry-run`; all immutable files, private runtime and fixed Core package are hash checked before importing Core or creating data. A mismatch is BLOCKED_PACKAGE_INTEGRITY. Only `data/` is mutable. Probe is foreground, 30 seconds by default and at most600 seconds; stop from another terminal with `./stop_shadow.sh`. Rollback retains DB/evidence and is repeatable. SIGKILL must first report UNKNOWN_UNCLEAN_TERMINATION; restart-check preserves the same identity/event and never dispatches an action.

Alternative A: if the operator already has a trusted authenticated GitHub origin, fetch only `dev/nana-core-v1-shadow-bootstrap`/the specified commit and verify HEAD; no new token. Fetching source alone does not create the native runtime binary: use the prepared archive or rebuild from pinned inputs on a separate development machine. Alternative C: use an already explicitly authorized file-transfer channel to send the same bundle only. No IP guesses, scans, SSH credential generation or secret transfer.

## Hook and native wrappers

HookCompatibilityProbe reads distribution version and optionally parses explicitly selected API-module source names. It never imports/initializes AstrBot, registers a hook, restarts or claims dynamic registration/unregistration/probe isolation from name presence. Those remain UNKNOWN and FIRST_REAL_MESSAGE_STREAM_SHADOW remains BLOCKED.

Pinned Iris0.3.0 L1 is a **volatile** `_queues[session].segment_1/2/3` container of ContextMessage.to_dict fields, not a native persisted JSON wrapper. The adapter preserves this distinction. Profiles use native `user_profile:{persona}:{group}:{user}` / `group_profile:{persona}:{group}` KV keys and profile_to_dict fields. Read-only wrapper interoperability is implemented for operator-created frozen **synthetic** envelopes, with schema-only(default), count-only, hash-only, redacted-sample. Schema-only opens no supplied snapshot. A count_metadata interface accepts numeric metadata without reading payloads. Hash/redaction of actual records would require reading those records; that is still a future explicit privacy authorization, not silently allowed because output is hashed. Production KV/runtime extraction remains disabled/unverified; no native disk format is invented. Unknown/missing/conflicting wrapper fields are rejected and never silently dropped. No import, Grant, Strategy or Action is created by wrapper export.

## Final delivery receipt (2026-10-11 UTC)

The actual delivered SQLite binding, not an earlier build, was loaded for the final full regression: CPython3.12.14 / SQLite3.51.3 / Pydantic2.13.5, **306 passed / 0 failed / 0 errors / 1 skipped**. Only E12 is skipped. Binding SHA256 is `c18e64abba400c9c1ee91327680ce388dd51b4fb090b52ad829257ba19d82705`. The same runtime inside the extracted archive passed all four dry-run script checks, preflight, probe, actual restart, actual SIGKILL(-9), initial UNKNOWN rollback, recovery, repeat rollback, collection, and deliberate file-tamper rejection. Identity/initial event time persist; unique probe/Evidence/candidate/shadow plan/decision each remain one; executable Actions/Grants/budgets remain zero. Plan is a Shadow draft in the existing memory projection, not an executable plans-table row.

| Artifact | Value |
|---|---|
| Archive | `nana-shadow-bootstrap-3aba4eb4253c.tar.gz` |
| Archive bytes | 3,268,730 |
| Archive SHA256 | `22ae38de7d2c751717a4ef351d0dc8f75491f2274a1bfea11e0a2e38c251b149` |
| Core source SHA | `ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513` (55 original files unchanged) |
| Operator support source SHA | `3aba4eb4253cb30f27141831a4c983d714594e3a` (clean committed support) |
| Private runtime bytes | 8,537,017 including its manifest; 8,518,899 content bytes excluding manifest |
| Runtime content-map SHA256 | `95c7215bc78d43cae809e99fcc65c1572cd611c87ae273afb80138b61c01e6ec` |
| Package content-map SHA256 | `3e786cbe90e590931a381547f87e0a8b4c8f3685c87736a84b3d1f7e04443b93` |

Runtime/package aggregate hashes are SHA256 of canonical per-file hash maps, not hashes of compressed tar streams. Runtime's own manifest is excluded from its aggregate to avoid self-reference, and is protected by the outer manifest. Full source/artifact/ELF/license metadata: `nana_shadow_bootstrap_evidence/final_bundle.json`. Compatibility assertions are bounded by `nana_shadow_bootstrap_evidence/compatibility_matrix.json`; extracted archive evidence is `final_bundle_validation.json`; full regression XML/log and loaded driver receipt are alongside it. The final evidence-only commit can differ from support source SHA without changing this already-tested archive. The archive is a generated local delivery file, not a binary committed to GitHub or uploaded to the Nana host.

After manually uploading **that single file**, the exact operator commands are:

```bash
set -eu
mkdir -p /opt/nana_shadow
cd /opt/nana_shadow
printf '%s  %s\n' '22ae38de7d2c751717a4ef351d0dc8f75491f2274a1bfea11e0a2e38c251b149' 'nana-shadow-bootstrap-3aba4eb4253c.tar.gz' | sha256sum -c -
# Continue only if the checksum above says OK. Use a new destination; do not overwrite an existing extraction.
test ! -e nana-shadow-bootstrap-3aba4eb4253c && tar -xzf nana-shadow-bootstrap-3aba4eb4253c.tar.gz
cd nana-shadow-bootstrap-3aba4eb4253c
./run_shadow.sh preflight
# Continue only if adapter_local_probe_ready is true. AstrBot/hook UNKNOWN does not prove host binding.
./run_shadow.sh probe
./run_shadow.sh restart-check
./run_shadow.sh rollback
./run_shadow.sh collect
```

There is no model/secret configuration. If the appropriate interpreter is not the default command, use `./run_shadow.sh --python /operator-reviewed/python ...` for the same commands. If permissions do not allow `/opt`, use a new user-owned directory; the script does not request sudo. Incompatible architecture/libc/interpreter means BLOCKED and no install/repair. No actual host hook is installed by any command: a successful future run would establish **real-host adapter-local engineering Shadow**, not an AstrBot message-stream Shadow.

Production login/changes/private memory/secret-value reads/external messages are all zero this task. Model calls zero, E12 NOT_RUN, no new paid service. Official source/wheel downloads are development build traffic, not public Web Capability acceptance. New Core SQL tables zero; no global dependencies installed; five privately pinned dependency wheels and one private SQLite binding are included. Manual transfer, actual host ABI/preflight, dynamic hook and native production KV extraction remain explicit boundaries. The two initial gate/package blockers now have a ready development-side workaround, but no claim is made that a file absent on the server is already there.

## Developer reproduction (not host installation)

Use a separate Linux x86_64 CPython3.12.14 build workspace with GCC, binutils and matching Python headers. Obtain the **exact** two source archives in `tools/nana_host_shadow/isolated_runtime.py::SOURCES`, named `Python-3.12.14.tgz` and `sqlite-fixed.zip`. Place exact wheel files from `WHEEL_PINS` into `INPUTS/wheels/` and copy the recorded `nana_shadow_bootstrap_evidence/wheel_sources.json` into `INPUTS/wheel_sources.json`. URLs and SHA256 for every input are in that recorded metadata. Builder refuses a different source hash, wheel set/hash or a build whose ELF GLIBC requirement exceeds2.34. No network download or latest-version resolution occurs inside the builder.

From the recorded clean support commit, generate a **new** destination with:

```bash
python -m tools.nana_host_shadow.bootstrap OUTPUT/nana-shadow-bootstrap-3aba4eb4253c --repo . --inputs INPUTS
python docs/nana_shadow_bootstrap_evidence/reproducers/bootstrap_validation.py OUTPUT/nana-shadow-bootstrap-3aba4eb4253c.tar.gz validation.json
```

The second command uses new temporary directories and real subprocesses/SIGKILL. The compatibility harness records its temporary development paths; adjust them to your pinned input and built-binding paths when reproducing old-version/full-regression comparisons. All source/build flags are pinned; the archive includes creation/build environment metadata, so a fresh build's whole archive hash is **not** promised identical. It must receive a new reviewed checksum receipt. Never build by replacing files inside the delivered artifact.

Startup isolation is enforced by the delivered release: `-I -B -S`, with missing flags rejected before bundle access. Global `.pth`/sitecustomize are not executed; installation metadata is read without importing global packages. Targeted tests:25 passed. Historical 67bc archive receipts remain in Git history and are superseded for operator delivery by this 3aba release.
