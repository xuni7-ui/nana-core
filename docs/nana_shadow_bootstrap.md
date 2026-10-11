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

Pydantic2.13.5 compatibility will be measured separately. No interval broader than actually tested patch releases will be declared supported.
