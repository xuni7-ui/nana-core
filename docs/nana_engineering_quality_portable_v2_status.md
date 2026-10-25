# Engineering Quality & Portable Runtime V2 — final status

GLOBAL_STAGE H / Advanced Growth. This is engineering/portable qualification, not
a new Foundation domain, live-model qualification or production release.

Runtime source: `e322f017900c060a5739347a76c7e63545773d1a`.
Full-regression source: `9e67c837dde708128e9051d4bcbc0d20114521d8`.
Base: `87f73d235d593a0d852bca409b0e73e0ef67cc5e`.
Later fixture/tests changes do not change Core, packaging, runtime builder or the
qualification addon bytes. Evidence records this equality rather than pretending
the package was built from a later commit. Final documentation commit is the
handoff anchor; its HEAD is obtained from Git, never a self-referential digest.

## Acceptance

| Gate | Status | Actual evidence and limits |
|---|---|---|
| SQLITE_PRECHECK_CONSISTENCY | PASS | Shared actual binding, >=3.51.3 plus JSON/FTS5, native modules; installer and target venv before pip/Subject; Store before mkdir |
| SQLITE_SUPPORTED_RUNTIME | PASS | Non-root privately built CPython3.12.14/SQLite3.51.3/libffi; real full installed lifecycle, 184 runtime imports, no monkeypatch/system replacement |
| UNSUPPORTED_SQLITE_REJECTION | PASS | Actual system3.46.1 refused before venv/pip/Store; actual missing-ctypes Python and misbound venv also refused |
| BWRAP_CAPABILITY_QUALIFICATION | PASS | Actual installed exact-policy probe, six namespaces, no host paths/env, NoNewPrivs, zero capabilities, read-only work; missing/denied fixtures fail closed |
| PACKAGE_RUNTIME_BOUNDARY | PASS | Exact197 source assets;231-file archive;184 imports under installed -O/-I; excluded lab/demo/fake_world; separate five-file qualification addon |
| ASSERT_SIDE_EFFECT_FIX | PASS | Actual prctl normal/-O and failure path; backup quarantine normal/-O; zero asserts in shipped runtime,47 explicit developer guards |
| CODE_MAINTAINABILITY | PASS_SCOPED | 29-file AST-identical formatting checkpoint; preflight responsibility helpers; measured global debt remains, not blanket cleanup |
| SOCKET_PATH_READINESS | PASS | Final absolute encoded path <=107 bytes, ASCII/multibyte negative cases before Subject/child startup; no automatic relocation |
| PRECISION_V2_COMPATIBILITY | PASS_SCOPED | Existing independent oracle on published and fresh parameters/graphs; installed9→6 checked+3 repair, one file move; unchanged authority/UNKNOWN boundaries |
| FULL_REGRESSION | 1542 passed / 0 failed / 0 errors / 12 skipped / 656.233s | Actual full source-pinned suite; skips retained with exact reasons |
| OFFLINE_INSTALL | PASS | Two independent fresh venvs, pinned/hash-locked offline wheels, actual isolated installed runtime; no inherited repository PYTHONPATH |
| PORTABLE_REBUILD | PASS | Runtime and qualification addon each built twice, byte-identical archive hashes |
| IDENTITY_RECOVERY | PASS | Actual SIGKILL, same-identity restart and official B8 transfer, old writer fence/Grants revoked, quarantined backups/deletion/UNKNOWN preserved |
| SECURITY_BOUNDARY | PASS_SCOPED | Original One Subject/Store/Loop/lineage, Kernel/Grant/Manager/Budget/Privacy/Verify constraints; source/manifest checks and sanitized new-file scan |
| FRONTEND_CONTRACT_CHANGED | NO | B10/versioned adapter DTO unchanged; host CLI preflight additive fields documented below |
| PRODUCTION_CHANGED | NO | No main/R045/production/private/user-device/real-social/paid-provider operation |

“SCOPED” applies to the stated Linux owned-development environments and original
independent checks; it is not universal planning, all-host compatibility, general
sandbox proof or production qualification.

## What changed and why

SQLite3.51.3 is retained because of the official WAL-reset corruption fix, not just
SQL syntax. A host with older SQLite no longer passes install/preflight and then
fails during identity creation. JSON/FTS5 probes alone cannot certify the fix.
The selected interpreter and actual venv both need the same contract. A fake
`.venv/bin/python` cannot silently direct pip writes into a host/global Python.

Generated-code isolation remains AST whitelist + actual bwrap + clear environment
+ minimal read-only mounts + resource/timeout limits; absence of usable isolation
blocks that optional skill, not an otherwise capable basic Runtime. No direct-exec
fallback was added. The availability probe itself confers no invocation authority.

Runtime release contents are an explicit reviewable manifest with static import
closure and known dynamic workers. Lab/qualification/demo services live in a
separate opt-in developer addon. Real learning, skill execution, controlled Hands,
provider routing, checkpoint and migration modules remain in the runtime.

`assert libc.prctl(...)` is now an explicit checked syscall. Other critical backup
and qualification checks survive -O. Socket byte-length errors surface before
creating or moving an identity, preserving ownership and lease requirements.

## Quality and cost measurements

Scope: `src/nana_core` Python, including nested/private functions and docstrings.
Physical lines26195→29525, token-bearing lines23367→26423, files236→237.
Lines>120:3089→2720; >200:755→692; multi-statement semicolons1603→1326.
Functions1406→1416; docstring-bearing functions74→82; annotated returns39→43.
Public-named top-level classes/functions813→821, with docstrings102→108;
public-named methods654→656, with docstrings23→25. Names not starting underscore
are only a static proxy for public contracts; docstring presence is not a proof
of adequate API documentation. Global contract-documentation debt remains.
These are raw counts, not completion percentages. Formatting expands physical
lines deliberately. Core state machines were not arbitrarily split for a score.

Ruff global debt C901145→146,F40175→75,F84110→10,F4033→3,F40515→15.
No F821/E9 findings. Explicit fail-closed guards add decisions; no claim global
complexity fell. The preflight monolith was split into dependency/resources/
read-only Subject checks (AST decision estimate28→10, not a removed Ruff C901 finding); other old high-complexity functions remain. Strict
mypy passes only the new shared host contract (`--follow-imports=skip`), not all Core.

Same CPython3.12.14/SQLite3.53.1 synthetic-host samples: Store reopen median
3.669→4.693ms, privacy1000 checks2.854→3.182ms, sandbox median66.290→66.191ms,
peak process RSS26208→28416KiB. New optional isolation probe37.483ms. These are
bounded samples and expose safety-check overhead; no whole-system speedup claim.
Minimum-binding installed lifecycle was qualified separately on SQLite3.51.3.

Actual old/new archives on the same private minimum-binding Python, three fresh
process launches each: preflight median1200.5→1854.5ms; observed ready-health
median2820.6→2373.6ms. Runtime RSS50864–50880→51504–51972KiB. Both retain one
identity through all three clean restarts. Samples include a health subprocess
and80ms polling, reuse OS caches and expose timing noise; no cold-cache or whole
Nana speedup is inferred. No concurrent full regression was running in this sample.

## Precision, identity and failure evidence

Published parameters20→20 feasible successes; published graphs13→13. Fresh
post-freeze seed2425685341 parameters20→20, graphs12→12; all independently
accepted false successes remain0. Fresh graph structure differs, not only names.
This preserves original symbolic capability; it is not semantic generalization
or LLM ablation. Benchmark task hashes and original independent judgers are kept.

Actual installed owned document/file/form services exercise original C→F→Kernel
→Verify→failure→G→C; six verified operators survive, three repair steps remain,
one file move. Restart and lawful B8 transfer preserve Subject/checkpoint and fence
old writer/Grants. No unverified/UNKNOWN effect is silently reused or replayed. The First-Life development entry remains pinned to its original branch; three isolated unit tests now explicitly bind their exact development branch, with every old assertion retained and a new wrong-branch negative case. This does not authorize First-Life or provider execution from the quality branch.

Retained failures are useful evidence: wrapper mkdir before SQLite refusal,
initial fake_world manifest omission, first custom Python missing_ctypes, vanished legacy temporary-interpreter prerequisite,
interrupted first full run, old unit-test branch-context mismatch, and two fixture-cadence experiment failures. The
original recovery test's12 assertion ASTs (8Goals/10effects/40s cuts) are unchanged.
Only its test-input availability is explicit1s; production cadence is unchanged.
A separate concurrent test independently replays actual authorized writes and
requires every repair to follow a real incorrect result and no duplicate success.

## Artifact and reproduce

Runtime231 files, fixed sourcee322, SHA256:
`25ad9723cc9d4ac31eea6b67f8661b332fc53fb6bff298d540c038fb5ada10de`.

Qualification addon5 files, same source, SHA256:
`bb572d22159966c95b206aba783162b1556bd185bf890161b293d5f73af622c4`.

See [quickstart](nana_engineering_quality_portable_v2_quickstart.md) for official
source URLs/content pins, isolated non-root Python build, offline double build,
installation and safe migration. The Python prefix is host-specific, not a
relocatable identity payload. Runtime wheel pins are unchanged. Dev Ruff/mypy
pins are isolated and do not add runtime dependencies. Schema13/43business tables,
new business tables0. Integrity manifests do not contain their own digest.

An independent reviewer can run:

```sh
python -m tools.nana_quality.check --archive /approved/nana-first-life-portable-v1.tar.gz
python -m tools.nana_foundation_audit.check
```

The first checker hashes archive/evidence/source and validates declared gates;
it does not open a Store or call a provider. It verifies recorded qualification,
not an independent new execution. To actually repeat installed qualification use
the addon README and the optional-import probe provided in this evidence folder.
Run the full suite independently with the environment specified in regression.json, including an explicit `--old-sqlite-python` interpreter with SQLite3.46.1. The old client-isolation assertion remains exact; a missing/incompatible fixture fails rather than skips. It does not select the Runtime interpreter.

## Remaining gates and compatibility

Host-only preflight adds `sqlite_runtime`, `python_native`, `optional_capabilities`,
`failed_checks`, `checks.socket_path_length` and `checks.python_native`; existing
fields keep their meaning. Nana Space B10/Versioned Adapter schemas are unchanged.
The new optional sandbox readiness field must not be mistaken for execution Grant.
There is no old executable hot-downgrade qualification for extended active plans;
use quiesce/backup/official lineage transfer and compatible version instead.

Original Master bytes and fixed63 definitions/IDs/denominator are unchanged.
S1–S9Foundation Qualified/S10Partial/61qualified criteria remain historical
controlled qualifications. Old five-hour result remains PARTIAL_EXTERNAL_LIMIT;
new residency PENDING_EXTERNAL_STABLE_ENV. Human Naturalness/semantic/model
ablation NOT_RUN; First-Life NOT_READY; Beta NO. Engineering installation success
does not close these gates or authorize online Nana cutover. No new true-provider
call, private-history import, user-device control, social send or production change.

No extra user authorization is needed to reproduce these isolated engineering
checks. A real online handoff still needs its separate environment, human review,
credentials/model budget and production approval; this task does not initiate it.
