# C-V2 Persistent Self — offline delivery

Branch: `dev/nana-core-continuous-self-codex`.
Start: `3330cbf5a68f5eb34b7f1643949d2493227734bf`.
Product source checkpoint: `8e7fe91b827bd0de6801ce2f0cb70ee0f6022da8`.
Final documentation/evidence commit is the Git descendant of that checkpoint.

## Three gates

1. Docs-only meta gate `123c6ed84c3485ca9336ec370dca9abc7e917196` committed and
   pushed before business implementation. Contract: ADR-CV2-001.
2. Execution checkpoints `ce6052ad9c2e3b0ce0114a062964f485e1c0bd2c`,
   `11e6942c3577f9b39fe1a418d331aa2b3df2d6e2`,
   `8e7fe91b827bd0de6801ce2f0cb70ee0f6022da8`, all pushed separately.
3. Ten-day life, two matched ablations, 60-day soak, actual process restart/model
   swap, and real SIGKILL transaction tests passed. Final full suite:
   **877 passed / 0 failed / 1 skipped**, 81.05s console (81.029s JUnit).
   32 continuity tests include 12 new cases; all prior tests unchanged.

Machine evidence: `nana_persistent_self_evidence/results.json`, `life.json`,
`full_regression.xml`, `security_scan.json`. Intermediate issues and fixes are
reported; no assertion was relaxed to make the simulation pass.

## What past experience changed

| World | Day6 without user input | Day9 Core method | Independent simulated result |
|---|---|---|---|
| Full history | EXPLORE + candidate goal | locate_then_draft | locator check PASS |
| Same seed, no exploration support signals | NO_ACTION | locate_then_draft | locator check PASS |
| Same seed, failure retained, lesson not applied | EXPLORE + candidate goal | draft | locator check FAIL |

The proposal itself, Core judgment and world outcome are separate report fields.
No model assertion of success certifies the result. Two direct counter-examples
change the adopted exploration preference to DISPUTED and drop its old optional
intention. A separate self-belief regression proves the same revisability without
canonical identity changes.

Fresh Python process rebuild + fixture ModelPort swap preserves exact identity,
state digest, LivingSelf/personality, memories, promises, projects and preferences.
SIGKILL inside the assertion/cycle transaction rolls back the decision, allowing
one safe resume; SIGKILL after commit returns the old result on replay. Both
reopen in new interpreters with one cycle/signal and no action/attempt/grant/budget.

60-day soak: maximum **2 live intentions / 2 live candidate goals**, maximum
**3171 bytes** combined LivingSelf/personality projection, independent support
count stays fixed despite repeated self-selected behavior. No reflection
recursion or social spam. Durable cold event/record history grows linearly.

## Engineering boundaries

* Development schema 6→7: 8 new tables, 35 total user tables. Default v1 unchanged.
* Existing parent CHECKs migrate transactionally with FK validation/restoration;
  populated-v6 migration and replay tested. Rollback is a pre-upgrade managed
  backup in quarantine; no destructive downgrade.
* No new dependencies. Runtime: Python3.12.14 / SQLite3.53.1 / Pydantic2.13.4.
  SQLite minimum3.51.3 remains unchanged.
* Existing Core continuity was deliberately extended under C-V2 authorization;
  this is NOT advertised as the frozen approved production Core package.
* Production source/tools/pins unchanged. Real memory ingress stays disabled.
  Production, main, R045, real data/secrets/model/action operations: none.
* Source/static privacy scan passed. No DB/WAL/runtime anchor or old Git bundle
  is included. One pre-existing untracked bundle is preserved in the worktree.

Fingerprint manifest: `manifests/nana_persistent_self_candidate.json` (105 files),
SHA256 `e594c45e2aadf904a78d1100ea97f9d5048c00a0cd71ceaa0a2bac6d8de5691b`.
The manifest excludes itself and mutable Brain/delivery notes. It fingerprints
these offline files; it is not a real-host attestation or production package.

## Ready, with explicit limits

`C_V2_PERSISTENT_SELF_OFFLINE_CANDIDATE = READY`.

Appraisal is an initial ordinal policy using source-annotated structured facets,
not qualified natural-language understanding. Relationship-driven interaction
stance is tested; learned spontaneous social outreach is not qualified. Reflection
only supports the existing verified locator rule. StandingDelegation/Wake are
contracts, not activated real authority or an always-on scheduler. No consciousness
claim. Source-root independence assumes trusted adapters and does not defend an
operator inventing distinct source occurrences. Existing deletion guarantees do
not cover unmanaged privileged clones or already exported/RAM copies.

Real-model semantic transfer/E12, real memory ingress, real host/D scheduler,
standing execution delegation, adopted E goals and G tools remain NOT_RUN or
not activated. Real AstrBot/B5-3 status is not inferred or upgraded by this work.
Stop here: no automatic production integration or additional capability rollout.
