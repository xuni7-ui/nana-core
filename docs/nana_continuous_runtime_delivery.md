# D-V1 delivery — offline candidate

Base: `ea65dabaa907b8bd777723d5ccc9527e1014d0c5`.
Branch: `dev/nana-core-continuous-runtime-codex`.
Tested product checkpoint: `85ae606aac259d0ee96994093009627e1b24581c`.
Final documentation/evidence commit is the Git commit containing this report.

**D_V1_CONTINUOUS_RUNTIME_OFFLINE_CANDIDATE = READY**.
This is a synthetic engineering candidate, not production deployment or real
semantic Nana qualification. User clarification is incorporated: D supplies
time and opportunities, C supplies judgment; S1 is just one scenario.

## Implemented and tested

Standalone NanaRuntime; durable bounded event queue; wake contract; coalescing
scheduler; injectable runtime clock; C background-attention opportunities;
source-backed internal events; bounded cognition; replaceable/unavailable model
resource; social proposals without delivery; four synthetic perception ports;
local Store lease/epoch with transaction fence; restart/UNKNOWN recovery; CLI
health/foreground run/exact-owner stop. One existing C SubjectLoop throughout.

Default legacy schema remains v1 and ContinuityStore remains v7; explicit
runtime v8 adds four operational tables, no second Store or authority system.
No new dependency. SQLite >=3.51.3 safety floor unchanged. No production package,
R045 branch, plugin, trust anchor, receipt or live Store is changed.

See [runtime interfaces and usage](nana_continuous_runtime.md) and
[contract](ADR/ADR-DV1-001-continuous-runtime.md).

## Evidence

| Check | Actual result |
|---|---|
| Full regression | **888 PASS / 0 FAIL / 1 SKIP**, 84.87s console |
| Skip | E12 real dual-model semantics, NOT_RUN |
| C+Runtime targeted | 43 PASS /0 FAIL, 27.50s |
| New Runtime test cases | 11; existing C32 and other prior tests unchanged |
| Whole-system gates | **32/32 PASS** |
| 72h no-input | Zero new user events; one causal internal intention and candidate; zero model calls and social proposals; queue depth0 |
| 30d mixed life | Same identity; project1, reflection1; pending max2; four fixture model calls (3 SUCCEEDED, 1 TIMED_OUT); active queue max0 at sample points |
| Actual local process soak | 11.338s total; 100 samples; heartbeat progresses; FD growth0; peak sampled parent RSS30100KiB |
| Real local double start | Second process rejected; epoch increments after owner death |
| Graceful local stop | SIGTERM succeeds; final lease STOPPED; no tracked active worker |
| Four actual SIGKILL cuts | Before C, after C/before queue ACK, after model reservation, during model process |
| Crash recovery | Each has one C cycle, one intention, one candidate; same identity; integrity_check=ok |
| Unknown model work | Both reserved-call cuts retain UNKNOWN; no automatic model retry; resource child terminated/reaped |
| Privacy/recovery | Deleted queued source ignored; no body in discarded queue metadata; official backup/replay quarantined |
| Real models / external actions / private files | 0 /0 /0 |

The full XML is [full_regression.xml](nana_continuous_runtime_evidence/full_regression.xml).
Machine-readable gates and actual local measurements are
[runtime_system_results.json](nana_continuous_runtime_evidence/runtime_system_results.json).
Source/runtime/scan metadata is in the same evidence directory. The source
fingerprint manifest is `manifests/nana_continuous_runtime_candidate.json`;
it excludes itself, this delivery and Brain anchors to avoid self-reference.
Snapshot hashes prove file contents only, not real-host execution.

Full command: `.venv/bin/python -m pytest -q tests --junitxml=docs/nana_continuous_runtime_evidence/full_regression.xml`.
System command: `.venv/bin/python -m nana_core.presence.qualification --output .nana-experiment/runtime-qualified-final --with-process`.
Verified interpreter: CPython3.12.14 / SQLite3.53.1 / Pydantic2.13.4.
The historical old-SQLite client test additionally used a temporary launcher
to this environment's actual system CPython3.13.5 / SQLite3.46.1. It verifies
dependency isolation only, not AstrBot-host compatibility. No system package,
global Python, test expectation or SQLite gate was changed for this run.

## One structure, many behaviors

| Scenario | Source/history → C result |
|---|---|
| S1 relationship + curiosity | Unresolved fictional hint → EXPLORE; exact synthetic read → social proposal; checked reaction → existing Experience/Reflection/lesson; suspension changes future act |
| S2 duty | Actual source-backed Project blocker → CONTINUE_PROJECT |
| S3 capability gap | Two fictional missing-capability observations → SEEK_CAPABILITY candidate; Grant0 |
| S4 creativity | Independent outcomes adopt preference; dependent cue → CREATE |
| S5 relationship | Busy availability → STAY_SILENT |
| S6 norm conflict | Explicit sourced norm inhibits available opportunity → non-action/WATCH |
| S7 rest | Six actual pending concerns, no urgent duty → REST / RESTING |
| S8 self-development | Independently checked failures → REFLECT; activated lesson changes later method to locate_then_draft |
| S9 opinion | Recorded constraint contradicts user method → ALTERNATIVE / DISAGREE |
| S10 world | Supplied screen/file/presence/platform deltas → C attention without real sensing |

Distinct semantic behaviors observed: CONTINUE_PROJECT, CREATE, DISAGREE,
EXPLORE, REST, SEEK_CAPABILITY, SOCIALIZE, STAY_SILENT, WATCH. Reflection also
occurs as a sourced intermediate C decision. Activity/message count is not a
success target. A large period of silence is a valid result, not an outage.

## Fixes and intermediate failures

Recovery review found a second RuntimeLease could replace the guard on the same
Store handle; acquisition now rejects it. Restart time used only the lease
floor; now it includes committed history. Switching model resources could
clear provider backoff; it now restores persistent provider state. All have
regressions in existing new Runtime cases, not weakened prior assertions.

The first matrix aggregate counted only top-level intention kinds and omitted
S1 nested behavior; individual scenarios passed but that aggregate failed. It
now counts recorded semantic behaviors, with the same >=8 diversity criterion.
Initial process-health test confused a still-live parent process with an active
stopped runtime; reports now distinguish both and still check actual child exit.
An unavailable `/proc/.../task/.../children` diagnostic caused the first
during-model marker check to fail; it now uses the supervisor's owned Popen PID,
with the same real SIGKILL/orphan-reaping assertions.

During final removal of expected behavior hints from scenario inputs, a stale
creative-preference reference failed mixed-life setup. Mixed-life now seeds its
actual project/history and separate unresolved question; S4 retains actual
evidence-supported creative preference. The corrected full suite passes above.
An initial targeted command used a nonexistent tests/continuity path; no tests
ran; it was rerun against actual tests/continuous_self + tests/continuous_runtime.
The current temporary environment lacked an old client-test launcher; it was
recreated pointing to the actual system interpreter, with versions measured.

## Checkpoints and recovery

1. `e609c6e6bd373da07e8888fee68d2148ba391584` — roadmap/contract.
2. `4af5e454ed17493d7b8ed5b918c4830fe20e5f49` — lease/queue/scheduler/v8.
3. `71e9705c97f78ed76d5e5eecc273c2a9605c07c4` — coordinator/cognition/CLI.
4. `e326af03fb4701b34f0f2d93734317de56abb910` — C opportunities/social/learning/perception.
5. `85ae606aac259d0ee96994093009627e1b24581c` — system qualification/recovery fixes.
6. Final docs/scan/manifest/Brain commit (containing this report).

Every checkpoint was pushed and ls-remote verified on this development branch.
No main/R045 merge or push was performed. Existing untracked
`nana-r03-codex-10581aea.bundle` was preserved and excluded from commits.

## Limits and next boundary

- Local canonical Store fencing only. No network-partition failover, hostile
  privileged clone detection, NFS guarantee or distributed authority.
- Initial ordinal C interpretation and fixture model proposals; no claim of
  real general reasoning, natural conversation quality or subjective experience.
- The local soak is seconds, not 24h production endurance. Queue/pending
  measurements describe this workload, not arbitrary future workloads.
- Active work/context/model attempts are bounded; cold event/history retention
  and archive policy still need long-term engineering.
- Real ModelPort adapter, billing/reconciliation, network providers, sensing,
  E adopted-goal/action execution and live delegation remain outside scope.
- Official restore copies are intentionally quarantined; no automatic authority
  activation/downgrade. No production deployment is part of this delivery.

REAL_MEMORY_IMPORT_ENABLED=NO; real model calls0; real external actions0;
production changes0; secret/private-data reads0. Production review/proof pins
remain EMPTY; E12 NOT_RUN. All real AstrBot/bridge/dispatcher/one-shot claims
remain at their prior Brain status; this branch supplies no field evidence.

RECOMMENDED_NEXT_INTEGRATION_POINT: independent review of this offline candidate,
then separately authorized ModelPort or E/G integration against the same subject.
Do not automatically start any real device/production capability from this result.
