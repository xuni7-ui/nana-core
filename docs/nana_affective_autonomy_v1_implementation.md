# L3-C-AFFECT-V1 implementation ledger

Base: 02e68d31d4d15beff141f19aebceb84d592f8a04 (parent f86c1f4).
Branch: dev/nana-core-affective-autonomy-v1-codex.
Consolidated ADR2 is unchanged. This is implementation, not another ADR.
No production, private input, real model or external effects are authorized.

## Implementation map / current checkpoint

- Existing SubjectLoop remains the only coordinator; v9 opts into additional
  semantic evaluation. Current v7/v8 interpretation is preserved.
- Existing Store/events/artifacts/records/privacy journal own persistence;
  v9 rebuilds two existing CHECK-constrained tables, adds lookup indexes, new
  tables0. Default ContinuityStore7 and Runtime8 unchanged.
- autonomy/contracts, evaluation, history, disclosure implement R1: normative
  disposition distinct from stance/lifecycle, erasable append-only disposition
  records, semantic disclosure and known-fact assertion eligibility.
- R2 Manager, R3 relationship/privacy, R4 requests/recurrence, R5 experience,
  system scenarios/recovery remain pending at this checkpoint.
- Evidence: first targeted9 PASS (new R1 + existing loop/runtime smoke). First
  read failed strict list-to-tuple validation; fixed JSON DTO rehydration without
  changing contract/assertions. This is not full qualification or READY.

Schema rollback: controlled pre-upgrade backup in quarantine, no lossy downgrade.
Real-memory ingress and production pins remain disabled/EMPTY. Old untracked
Git bundle is preserved and excluded from commits.

## L3-C-AFFECT-V1 M2 — negative-only governance / governed fixture realization
[实测·开发离线] R2 implemented: OperatorAuthority-bound controller, exact finite
negative constraints in existing events/artifacts, revision/revoke, post-Judgment
PASS/BLOCK/UNKNOWN, erasable outcome/disposition and filtered next-cycle view.
No Model/Memory/Subject authority path. Old blocked intentions do not revive.
Governed handoff uses existing ActionKernel checks and pre/post-transaction fence.
Only exact OfflineEffectPort on explicitv9 may exercise synthetic fixture actions;
no subclass/arbitrary CapabilityPort gets this exception, ordinary Shadow fences
remain. Fixture JSON is world data, not another subject DB/Store. No real effect.
Targeted22 PASS (R1/R2 + existing action/runtime boundary); latest R2 four PASS.
Full qualification/recovery matrix pending; not READY. No production changes.

## L3-C-AFFECT-V1 M3 — relationship and privacy axes
[实测·开发离线] R3 pure bounded RelationshipInfluenceView with seven facets,
domain trust/counterevidence and target-specific repair. Existing RelationshipView
retained; v9 personality/style/context use the same projector. Social expectation
comes from direct sourced norms/boundaries, not model assignment. Private social
meaning can cause self-restraint without becoming Manager authority. Hard context
privacy/task/destination/deletion/conflict checks preserved; secret canary excluded.
16 targeted PASS (new + prior projection/context); final four R1/R3 PASS after
normalized-link/time tie refinements. v9 adds only3 normalized relationship
columns on existing table; partial unreleased v9 checkpoints finalized additively.
No new tables/Store/loop; R4/R5/system qualification remain pending.

## L3-C-AFFECT-V1 M4 — positive requests and calendar opportunities
[实测·开发离线] R4 typed positive request → Subject ACCEPT/NEGOTIATE/DECLINE.
ACCEPT only offers existing CommitmentCandidate; trusted controller materializes
idempotently, no auto-adopt/Grant/send. Reuses CommitmentService/CAS and due
attention. Stdlib zoneinfo daily recurrence handles IANA zones, fold choice, gap
next-valid-minute, missed-window coalescing and persistent occurrence keys on
existing Scheduler. Calendar only emits SELF_WAKE checks, not user experiences.
Targeted8 PASS (new calendar/requests + prior scheduler/promises), latest2 PASS.
Queue metadata scrub extended for new structured personal fields; body remains
in erasable records only. v9 extends runtime_schedules CHECK, tables still39.
R5 experience and final scenarios/recovery remain pending, candidate not READY.

## L3-C-AFFECT-V1 M5 — disposition experience gate and checked learning
[实测·开发离线] R5 meaningful candidate gate selects consequence-backed, repeated
distinct or explicitly reflected dispositions. Raw veto/read/restart is not
automatically Experience. Typed independent verifier proves non-execution fact
without claiming reasoning correctness; later observed consequences supply a
separate assessment. Existing ExperienceService/Reflection/lesson trial/review
lifecycle supports NON_EXECUTION and a narrow consequence-review rule. Replaying
one candidate cannot create duplicate experience. Source erasure purges candidate/
proof/experience support while independent Manager source survives.
Targeted9 PASS (new experience + prior learning/privacy), final2 PASS. No new
tables: existing experiences CHECK extended and records opaque target lookup
column/index added; same Store/privacy/replay. Manager facts no longer become
automatic transitive normative dependencies in every future cycle.
Major full regression and final system qualification pending; NOT_READY yet.


## L3-C-AFFECT-V1 M6 — system and recovery qualification (OFFLINE)
[实测·开发离线] S1–S15 and two independent generic Subjects PASS; 60 virtual days
PASS with bounded pending/candidates/hot state, one veto history, no social/model
spam. Six actual tracked local SIGKILL/reopen cuts PASS, including UNKNOWN effect
verification without re-execution. Explicit v7→v9/v8→v9 preserves IDs/history,
foreign_key_check clean, managed backup/replay quarantine and erasure honored.
Production pins/real memory ingress unchanged. v9 adds0 business tables; default
C7 and D8 unchanged. Major full at f513dcc:900 passed/0 failed/1 skipped(E12).
Targeted C/D/new qualification:65 passed. Final full regression still pending.
Hardening: definition-only governance changes do not rewrite normative context;
resource classification is pinned to sourced cue and denied at realization;
post-check races persist veto without Action; filtered constraint view includes
revision/source/effective window. Hidden relationship counterevidence yields
PARTIAL/UNKNOWN coverage without loading its body. Source-erased disclosure is
unavailable. No real world/production/host/model/private input used.
