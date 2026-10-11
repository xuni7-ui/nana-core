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

## Pending measured compatibility

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
