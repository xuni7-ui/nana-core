# D2–D7 Living Autonomy V1 — development implementation log

Base: 4ad273f540bf8ac2988854b68a689685333e8c67 (local, not pushed).
Branch: dev/nana-core-d2d7-living-autonomy-v1-codex. No automatic push.

## Bounded integration result

Relational 67326d1 and this base share e26288e. C6/C7 reused all 21 source
changes; the remaining source delta is additions and explicit bootstrap/primary/
portability extensions, not lost Relational behavior. Prior Relational reports
are retained from 67326d1 as historical evidence, not this task's validation.
OSS research documents are retained from 9a9f8fe, DESIGN_ONLY unless listed below.
No external source code is copied; pattern implementations remain project code.

## Construction sequence

1. Existing Runtime gets a bounded thread-safe ingress mailbox and condition wait;
only its owning thread writes SQLite. Pausable background cognition and maintenance
safe points use the same queue and C SubjectLoop, never a second reply brain.
2. Explicit development schema11 extends existing jobs/record/call lifecycles. No
second DB. C owns source-backed plan-step appraisal; a trusted finite offline goal
policy can adopt C candidates. Existing governed realization/Kernel own all effects.
3. Source-versioned maintenance slices produce candidates; existing C admission,
ExperienceService/Reflection/Growth remain authority. Living Journal is a projection.
4. Resource reservations, recoverable work and B10 read projections close the loop.
5. One synthetic life/skill demonstration and focused tests, then final full suite.

Default v7/v8/v10 paths remain compatible. Living mode requires explicit11;
production migration, real data/models/sends/devices and real plugin installation
are NOT authorized. Portable subject state, rebuildable projections and machine
execution state must stay distinct. Manager remains post-Judgment negative-only.

Implementation and final evidence will be appended to this document.
