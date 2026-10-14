# C–D Continuous Self offline candidate — delivery

CONTINUOUS_SELF_OFFLINE_CANDIDATE = **READY** (synthetic/offline only).

- Repository: `xuni7-ui/nana-core`
- Branch: `dev/nana-core-continuous-self-codex`
- Base: `b3ff62ac944fe95c7a29217071c3885aaa5f04bb`
- Product source: `579a0bd885d4cb77b227c5e27d1ac0f5249885b0`
- Final tested checkpoint: `289a7a5` (only fixture precondition/doc after product source).
- Final delivery commit adds evidence/documentation; inspect branch HEAD for full SHA.
- Main and R045 remain `18bc736d...` and `ef7750e0...`, respectively.
- New dependencies: **0**. New development SQL tables: **12**, total user tables27.
  Explicit migrations v1→v6; v6 adds only an index. Default Store remains v1.
- Preexisting untracked `nana-r03-codex-10581aea.bundle` preserved; not committed.

## Capability results

All C1–C7 / D1–D4 below are IMPLEMENTED / TESTED. Runtime results refer to real
**local offline processes**, never a production host or real model.

| Requirement | Delivered behavior / evidence |
|---|---|
| C1 canonical identity | Original Store UUID + revision/provenance/CAS; restart/replay/managed host-copy stable |
| C2 memory | Seven facets, separate evidence/belief/summary/lesson; source/time/privacy/authority metadata |
| C3 correction/supersession | Exact family + time/source checks, explicit correction links, conflict/stale filtering |
| C4 deletion | Artifact/hash/index/relation/record-history closure purge, WAL truncation, managed backup tombstones |
| C5 relationship | Sourced history/preferences/norms/boundaries/open topics + promises/projects, no identity write |
| C6 commitments | Candidate vs operator-adopted; legal states, overdue, exact-target independent fulfillment proof |
| C7 project | Structured goal/state/milestones/decisions/questions/blockers/progress/next actions, CAS history |
| D1 SelfFrame | Derived from live sources, canonical SELF binding, no reverse truth write |
| D2 ContextAssembler | Privacy before retrieval and for task input; bounded candidates, budget, manifest, whole disputes |
| D3 ModelPort | Strict v2 serialized input/proposal; two different fixtures, unchanged persistent subject state |
| D4 experience | Independent artifact quality check → narrow trial rule → activated lesson → restart/context/proposal |

## Final verification

`python -m pytest -q tests`: **865 passed / 0 failed / 1 skipped**, 58.58s console
(58.564s JUnit). The sole skip is E12. Twenty permanent C/D tests were added; no
preexisting test was removed or weakened. Configured pytest now includes C/D.
The full run includes old R03–R044 host/receipt/bridge tests, next-stage readiness,
S0–S6/development/web/migration and all current integration tests.

Actual Core runtime: **CPython3.12.14 / SQLite3.53.1 / Pydantic2.13.4**. SQLite gate
>=3.51.3 remains. This task has not independently run new C/D on SQLite3.51.3.
The old stdlib-client isolation test uses the actual system Python3.13.5 /
SQLite3.46.1 via its expected temporary launcher. It is not a 3.12 ABI claim.

- A fresh real interpreter recovered identity, relationships, corrected preference,
  adopted promise, project and lesson with **identical subject-state digest**.
- The original corrected event time remains200µs, never restart time.
- Actual SIGKILL after durable delete intent recovers before reads.
- Physical synthetic canary is absent from controlled DB/WAL/backup/replay.
- Learned raw proposal: READ_SOURCE→LOCATE_SOURCE→DRAFT; matched lesson suspension:
  READ_SOURCE→DRAFT. Same underlying history/identity/memory/project/experience.
- Missing locator is checked from the actual synthetic result artifact; model
  `success:true` does not determine the outcome.
- Action/Attempt/Grant/Budget are all0 in the combined candidate. ActionKernel
  fencing remains active. No proposed operation is actually dispatched here.
- Wheel imports from a fresh extracted directory, bundles all six SQL schemas and
  creates a complete schema6 Store; see wheel_check.json. This development wheel
  is **not** an approved R045 replacement or deployment artifact.

Intermediate failures are disclosed in results.json/initial_regression_failures.json.
A borrowed-view compatibility regression was fixed; a missing old interpreter
launcher restored. A later permission test needed explicit chmod under inherited
umask077. Original rejection assertions and all old tests were retained.
Raw historical tracebacks stay in ignored local experiment storage; the Git report
contains sanitized test names/causes, not environment dumps.

## Reproduce

```sh
.venv/bin/python -m pytest -q tests/continuous_self
.venv/bin/python -m pytest -q tests
```

The full historical host tests require their existing temporary old-SQLite client
launcher. In this environment `/tmp/nana-bootstrap-build/compat-python-old` is a
0700 stdlib shell launcher executing `/usr/bin/python3 "$@"`, whose measured
SQLite is3.46.1. Do not spoof version strings or inject a private runtime into a
running host. See results.json for the exact interpretation of this check.

Core API, data contracts, state transitions, delete/restore protocol and a runnable
synthetic example: [developer contract](nana_continuous_self_api.md).

## Known limitations / review before real integration

1. Real memory ingress remains **hard disabled**. Even all qualification flags true
   returns REAL_MEMORY_IMPORT_DISABLED. No real user data was imported.
2. Populated v1→new private schema conversion is still blocked. Existing immutable
   plaintext needs an independently reviewed offline conversion, not ALTER-only.
3. This synthetic canonical identity is not a claim of adopting current production
   Nana's identity lineage. Actual host migration/adoption has not run.
4. Managed restore requires the current external privacy journal. Cross-machine
   anchor/path relocation, arbitrary unregistered exports, provider retention,
   caller RAM, root whole-disk rollback and forensic SSD erasure are not certified.
   Busy controlled backups report pending rather than erasure success.
5. The journal is bounded16MiB. Long-volume compaction, semantic relevance beyond
   bounded lexical candidates, and general multi-claim resolution remain future
   work. Conservative unresolved/hidden contradictions may require narrower
   context or reviewed clarification; no automatic tie-breaking was invented.
6. Default token counting is a UTF8 byte engineering estimate. A real v2 adapter
   still needs provider framing/tokenizer, authorized endpoint and CallLedger.
7. Lessons currently support only the existing missing-locator read rule. General
   semantic learning, real model transfer and E12 remain NOT_RUN.
8. Independent fulfillment checking is target-bound but domain checker correctness
   still needs evidence; a trusted checker assertion is not an Action receipt.
9. one_live_goal is unchanged. No autonomous scheduling, real action execution,
   production memory/execution authority transfer or second Runtime was added.
10. New development schema/Core code needs review before becoming a new approved
    release. Do not insert it into the frozen R045 host bundle.

## Preserved real-world boundary

REAL_MEMORY_IMPORT_ENABLED = NO
real model calls = 0; E12 = NOT_RUN
production changes = 0; real host operations = 0
real private memory/message/secret values read = 0
real messages sent = 0; extra paid service = none
production review pins = EMPTY; real runtime proof pins = EMPTY
main changed = NO; R045 changed = NO

No conclusion here upgrades Nana's parallel B5-3, real dispatcher, host binding,
real message or real semantic evidence. Those remain owned by the other executor.

NEXT_REAL_INTEGRATION_POINT: after Nana's B5-3 production qualification and a
separate exact privacy/identity/data-subset authorization, review the new schema,
legacy conversion/deletion/restore protocol and begin a **small read-only Memory
Shadow**. Iris remains authoritative; Core gets no writer or execution authority.
E12 still requires two independently authorized real development models.
