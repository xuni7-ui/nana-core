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
