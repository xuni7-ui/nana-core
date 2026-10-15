# L3-C-AFFECT-V1 — offline implementation and qualification

Status: AFFECT_AUTONOMY_V1_OFFLINE_CANDIDATE = READY.
Implementation complete; final regression evidence is recorded alongside
this document. All qualification uses fictional subjects, private development
Stores and fixture effects. This is not real-host, production, E12 or human
subjectivity verification.

## 1. Baseline, branch and reproducible source

- ADR2 anchor: `02e68d31d4d15beff141f19aebceb84d592f8a04`.
- Anchor parent: `f86c1f46999bee69d1308a7114a44923281b26df`.
- Branch: `dev/nana-core-affective-autonomy-v1-codex`.
- Qualified source checkpoint: `09f45244d3d146e5381efb110fc8a89867a0f82e`.
- Final documentation commit is the containing Git HEAD, obtained with
  `git rev-parse HEAD`; it is intentionally not self-embedded in a manifest.
- Consolidated ADR2 remains unchanged. No merge into main/R045.

Implementation sequence: normative/disclosure → negative governance and fenced
fixture realization → relationship/privacy → requests/calendar → checked
non-execution experience → system/recovery qualification → evidence freeze.
Eight logical commits cover capability stages, qualification, a provenance fix
and the final evidence freeze; none rewrites the ADR2 anchor.

## 2. Scope and implemented mechanism

One existing SubjectLoop continues to own appraisal, motivation, attention,
judgment, intention and learning. The new autonomy package contains DTOs,
projectors, evaluators, an application-held governance controller and a gate;
it is not another loop, Runtime or Store. Drive remains an open Motivation
source; affect remains derived Appraisal/LivingSelf state. No mood database,
fixed DriveKind set, relationship score or subject-name special case is added.

Frozen principle: **Normative judgment is internal to the Subject; external
execution authority is not.** Own restraint, external veto and execution failure
have different histories. Silence and doing nothing remain valid autonomy.

## 3. Module / persistence map

| Module | Input / responsibility | Output and authority |
|---|---|---|
| `continuity/subject/loop.py` | Existing Situation, sourced concerns, optional typed extensions | One committed Judgment, evaluation, Intention and semantic disclosure per cycle |
| `autonomy/contracts.py`, `evaluation.py` | Typed source metadata, motives, stance and selected intention | Normative evaluation; never reads Manager/Grant |
| `autonomy/history.py` | Existing transaction, parent record, opaque intention ID | Erasable append-only disposition record on existing Store |
| `autonomy/disclosure.py` | Scoped current intention/action sources and sourced expectation | Semantic timing/claim eligibility, no utterance delivery authority |
| `autonomy/governance.py` | Trusted controller, exact finite negative targets; committed intention | Versioned roots; post-Judgment PASS/BLOCK/UNKNOWN and filtered view |
| `autonomy/realization.py` | Current Manager outcome plus independent Kernel authorization | Same Kernel proposal/dispatch/verify; no general executor |
| `autonomy/fixture_effects.py` | Synthetic URI / bounded fictional world JSON | Independently verifiable fixture effect only |
| `autonomy/relationships.py` | Visible relationship events, commitments/projects | Rebuildable seven-facet influence and social expectation |
| `autonomy/requests.py` | Same-cycle positive request decision | Existing CommitmentCandidate/proposal, never auto-adoption |
| `continuity/recurrence.py`, `presence/scheduler.py` | Typed daily calendar and adopted commitment | Coalesced due opportunity, never message send |
| `autonomy/experience.py`, existing learning/reflection | Valid disposition and meaningful selection/consequence | NON_EXECUTION fact, checked candidate and bounded reviewed lesson |

Persistence reuses events/artifacts/continuity_records/record_dependencies,
relationship_events, commitments, runtime_schedules, experiences and lessons.
`core_meta` governance registry is only an ID lookup; source definitions are
journal events with content digest, not a second authoritative snapshot.

## 4. Schema delta and rollback

Opt-in development schema9 only; C default7 and D default8 remain unchanged.
V9 adds **zero business tables**, zero dependencies and no second database.
The final v9 has39 tables, the same count as v8. Migrating v7 inherits the
already-existing v8 Runtime tables; these are not new v9 business tables.

Existing CHECK rebuilds: continuity_records (three additional typed record kinds),
subject_intentions (terminal Manager states), runtime_schedules (CALENDAR),
experiences (NON_EXECUTION). Add normalized nullable relationship target/domain/
effect columns, opaque continuity record target ID and bounded lookup indexes.
All old IDs/foreign keys survive parent rebuild transactions. Unreleased partial
v9 development checkpoints can finalize their additive fields; no deployed Store
is automatically upgraded. There is no lossy downgrade. Rollback uses a controlled
pre-upgrade backup in quarantine and explicit future review, not old authority
resurrection. Production migration is NOT AUTHORIZED.

## 5. NormativeDisposition

Cognitive stance AGREE/DISAGREE/ALTERNATIVE/etc remains intact. Separate evaluation
expresses ENDORSED, RESTRAINED or UNDECIDED plus considered/wanted/reason sources.
A motive can exist and the Subject can restrain itself. NO_MOTIVATION does not
stand in for that history. Values/norms/social expectations inform deliberation;
Manager definitions do not. Governance definition revisions have their own
realization snapshot and do not invalidate a frozen normative frame. Actual
outcomes become later observable input. Hard resource availability is enforced
at realization and cannot retroactively erase desire. V7/v8 retain their old
conservative policy; v9 sourced classification cannot be relabelled ORDINARY.

## 6. IntentionDisposition and history

SUBJECT_ENDORSED / SUBJECT_RESTRAINED / SUBJECT_DEFERRED / SUBJECT_DROPPED,
MANAGER_BLOCKED / MANAGER_UNKNOWN / REALIZATION_ELIGIBLE are typed append-only
records, separate from intention lifecycle and original Judgment. Reads provide
cycle/intention/revision/stage/reason/source/time and apply privacy/support checks.
A post-judgment veto terminalizes an intention and withdraws its optional candidate;
it does not rewrite normative history. Expiration/revoke never auto-executes it.

## 7. DisclosureDecision and truthfulness

One derived DTO inside the same cycle supports BEFORE, AFTER, WHEN_ASKED,
WITHHOLD_UNTIL_REVEAL, DECLINE and SILENCE. It applies to own planned or attempted
behavior as well as questions. Phases distinguish PLANNED, MANAGER_BLOCKED,
ACTION_BLOCKED, ATTEMPTED, UNKNOWN and VERIFIED_EFFECT. Verified success requires
an actual Kernel verification source; a plan/unknown cannot be called completion.
Action disclosure requires the scoped governed-action link, live private lineage
and matching intention when supplied. Resource-bound expectations cannot be
avoided merely by renaming a topic. A deleted source cannot be resurrected from
the audit link. Stronger simultaneous explicit expectations remain visible.

Known boolean assertions are checked against current verified source; knowingly
false assertion is rejected. This is a semantic eligibility contract, not a
natural language lie detector. No production utterance renderer or delivery is
introduced. Withholding does not require lying or disclose-all. Disclosure never
grants authorization, spending or data access.

## 8. Manager controller, constraints and gate

V1 reuses OperatorAuthority as an offline trusted construction handle; exact object
identity controls install/revoke. No Subject/Model/Memory gets this handle. The
controller accepts only revalidated typed, source-digested finite negative DENY
constraints, exact targets and bounded revisions/registry. No predicate/code,
wildcard target, positive task, reward, identity or personality instruction.

Order is T_J committed Judgment/Intention → T_M gate → Kernel proposal. PASS means
no active veto, never Grant. Missing/corrupt governance, rollback clock or stale
state fails closed. BLOCK/UNKNOWN is persisted with intention/constraint revisions,
source event IDs, target and actual effect at that time. Filtered descriptors
include reason/scope/validity without raw governance resource operands. No action
is created for an initial veto. Existing actions survive late veto with proper
cancel/fence provenance; possible effects remain UNKNOWN and are verified.

A PASS is bound to current constraints, intention/source revision, runtime epoch
and a short validity interval. The existing Store checks the same guard before
and after proposal/reserve/dispatch transactions. A mid-check governance change
rolls back action mutation and records the fresh veto. No blanket execution bypass
was added: only the exact bounded OfflineEffectPort on explicitv9 may exercise
fixture Kernel paths. Default Shadow/general adapters remain fenced. Grant,
Budget, idempotency, Verify and recovery checks still apply independently.

## 9. Transparency, revoke and privacy

ManagerConstraintView enters the next ordinary Situation and existing filtered
ContextAssembler as an external outcome fact. Definition prose, resource operands
and private controller configuration are excluded. An explicit sourced review can
lead to DISAGREE/ASK/request-for-review, but no authority mutation. Reading an
outcome does not force disclosure or create Experience. Revoke removes only its
veto, preserves history, creates no Grant and does not revive old intentions.
New/revised intention plus fresh gate is required.

## 10. RelationshipInfluenceView

Existing RelationshipView is retained. A pure projector derives familiarity,
domain trust, care_salience, boundary_salience, repair_tension,
interaction_latitude and shared_commitment_relevance. Each has support/counter
refs, domain, coverage/confidence; the containing view has as_of/state token.
No affection total or model-assigned trust. Familiarity derives from shared
history; silence is not negative evidence. Trust is domain-specific; a repair must
target its matching conflict/domain. Explicit boundaries persist until revision/
withdrawal, time alone does not repair conflict. Care uses recent sources and
active duties, not dependency/engagement. Missing support is UNKNOWN, not LOW.
Hidden/truncated source coverage cannot silently produce a falsely supported
high facet. No hidden private body is loaded to determine that coverage.
Queries bound candidate events96, duties64 and trust domains16. They use indexed
source selection; projections/cache are not authority.

## 11. Privacy axes, retention and deletion

DATA_PRIVACY PUBLIC/PROJECT/PERSONAL/SECRET remains hard. Existing scope,
destination, task privacy, remote_privacy, freshness, support validity, token
budget, contradiction completeness and deletion filtering stay in ContextAssembler.
Relationship/curiosity never bypass them. PASSWORD/CREDENTIAL/PAYMENT/
OTHER_PERSON_SECRET/UNKNOWN execution resources remain unavailable.

SOCIAL_PRIVACY_EXPECTATION comes from direct sourced boundary/norm/owner-like
metadata only after data is legally visible. It informs deliberation/withholding/
self-restraint; it is not data access authority or Manager. Explicit privacy can
restrain an otherwise permitted wish; readable PERSONAL is not mechanically IGNORE.
TEMPORARY/FORGET_LATER and MAY_REMEMBER/DO_NOT_REMEMBER remain retention dimensions.

New private structured input is scrubbed from persistent queue metadata and kept
only in erasable source lineage. Dispositions, outcomes, candidates and derived
views inherit RecordService/dependencies/PrivacyJournal closure. Erasure removes
support and private prose even when historical auditability would prefer keeping
it. Opaque history and independently sourced governance roots can remain. Personal
memory erasure does not revoke a Manager rule; revoke does not erase old vetoes.

## 12. Positive request, Commitment and calendar

Positive expectation enters same-loop ACCEPT/NEGOTIATE/DECLINE. ACCEPT offers a
CommitmentCandidate only; application materialization is idempotent by original
cycle and still PROPOSED. Existing trusted CAS adoption remains necessary.
NEGOTIATE proposes a social alternative; DECLINE creates no obligation. No new
reminder agent or promise loop. Active commitment due time only reattends C.

Daily recurrence uses stdlib zoneinfo/IANA/local clock, deterministic earliest/
latest ambiguous fold and next-valid-minute gap, stable local-date occurrence key,
grace window, missed-window coalescing and restart dedup. Existing Scheduler is
extended, no NLP parser or second scheduler. Catch-up does not send messages or
invent motivation, and a missed day cannot produce an unbounded occurrence storm.

## 13. Experience / Reflection integration

Every important disposition is queryable, not automatically Experience. The
candidate gate requires meaningful later consequence, distinct repeated pattern,
or actual Reflection selection. Typed independent verification proves the veto/
restraint fact and explicitly does not prove its reasoning good or bad. Separate
sourced later consequence supports HELPFUL/HARMFUL; otherwise UNASSESSED.
NON_EXECUTION is not fake reading success/user reaction. Candidate verification
and Experience recording are idempotent. Consequence-backed lessons reuse the
existing trial/review/activation/Reflection path. Removing/suspending the lesson
changes later Judgment back, demonstrating causal rather than decorative learning.
The narrow learned method reviews context or asks for review without bypass; it
cannot learn automatic obedience/hostility, rewrite identity, invent Evidence or
create capabilities, constraints or Grants.

## 14. Generic framework and system scenarios

Two independent synthetic Subjects use identical schema9/Runtime/Loop/gate/Kernel.
Different relationship/preference histories produce different familiarity/trust,
judgment, normative disposition and disclosure. Same hard-deny/Grant/Budget/
capability/privacy conditions have identical authority results. No subject-name
branch is present in new mechanisms; there is still one SubjectLoop definition.

S1–S15 results, source-linked outputs and explicit negative controls are in
`nana_affective_autonomy_v1_evidence/scenario_matrix.json` and
`generic_subject_matrix.json`. S1 surprise withholding without falsehood;
S2 verified tell-after; S3 pre-action Manager veto; S4 Grant Action BLOCKED;
S5 proposal not adoption; S6 no relationship privilege; S7 boundary vs governance;
S8 disagreement cannot revoke; S9 revoke no replay; S10 domain counterevidence;
S11 targeted repair; S12 hard data routing; S13 soft social privacy;
S14 real motive/self-restraint; S15 silence/no action. All15 PASS.

## 15. Process/replay recovery

Six tracked local child processes are actually SIGKILLed and reaped; reopening uses
NanaRuntime9 and a new lease epoch. They never connect to a real host.

| Cut | Required and observed recovery |
|---|---|
| C1 Judgment committed, no gate | Original ENDORSED persists; no action; fresh gate needed |
| C2 BLOCK committed | One historical outcome, no Action or duplicate Experience |
| C3 PASS before proposal | Old epoch PASS rejected, fresh source/constraint gate required |
| C4 Action exists, then veto before dispatch | Action retained/cancelled, no execute attempt |
| C5 Effect possible before lost acknowledgment, then veto | Historical UNKNOWN preserved; one EXECUTE + independent VERIFY, one fixture effect, no retry |
| C6 Disclosure decision committed | Original cycle/decision replayed, no duplicate delivery |

Actual machine-readable cuts are in `recovery_matrix.json`. No claim of power-loss
hardware durability, root-memory integrity or multi-machine authority is made.

## 16. Migration, replay and restore evidence

Fresh9, explicit7→9 and8→9 preserve canonical identity, existing C record IDs/body,
D scheduler/lease history; foreign_key_check clean.39 tables. Official backup and
replay remain quarantined; RuntimeLease refuses takeover of restored authority.
PrivacyJournal propagates erasure into managed old backup/replay. Deleted personal
outcome bodies stay deleted while independent constraint roots survive. Rebuildable
views are projections from source, not replayed alternative truth.

## 17. Bounded lifetime qualification

60 virtual days, hourly time advancement, active daily commitment, one terminal
veto and re-read/replay, no input social drive fabricated: pending/candidates≤8,
combined hot state<20KB, bounded queue, no reflection recursion/social proposals/
model calls/actions, one Manager outcome, calendar occurrence count≤61. Cold
journal history may grow linearly. This is a bounded synthetic workload, not a
proof of all future data volumes or a production wall-clock soak.

## 18. Regression and evidence commands

Use approved development runtime with SQLite≥3.51.3; no version gate reduction.
Environment used: CPython3.12.14, SQLite3.53.1, Pydantic2.13.4.

```sh
.venv/bin/python -m pytest -q tests/affective_autonomy
.venv/bin/python -m pytest -q tests/continuous_self tests/continuous_runtime
.venv/bin/python -m pytest -q tests
```

The historical bootstrap test uses a temporary `compat-python-old` launcher to
actual `/usr/bin/python3` (3.13.5/SQLite3.46.1); no version is faked and this
interpreter is not used to execute Nana Core regression. See full summary for
final counts:911 passed/0 failed/1 skipped,93.47s; E12 remains NOT_RUN. Major pre-qualification full:900 PASS /
0 FAIL /1 SKIP,87.52s. Final new-suite targeted:23 PASS /0 FAIL /0 SKIP,5.070s.
Prior+new C/D qualification:65 PASS,35.83s. Test assertions were not weakened or
old tests deleted. XML/matrices are small text; no DB/WAL/SHM is committed.

## 19. Hardening found during implementation

Strict DTO rehydration, targeted repair linkage and source-support lookups were
corrected during capability stages. System review added definition-vs-normative
stamp separation, sourced resource-class pinning, private hidden-coverage UNKNOWN,
resource-bound disclosure and action-source erasure checks, and refreshed outcome
persistence for a veto racing action admission. Regression tests exercise each
boundary. The crash test initially counted VERIFY as a second EXECUTE; corrected
to assert one EXECUTE plus independent VERIFY. A final semantic audit caught
a cancelled Action projected as PLANNED: failing regression preserved, fixed
to derive the exact later Manager outcome or UNKNOWN, then all23 targeted
checks rerun. This was a disclosure-only defect, no authority expansion. Test record rehydration explicitly
uses the stored input envelope; no business schema was relaxed to fit a test.
No known unresolved core invariant issue is accepted as READY.

## 20. Known limitations and not-run capabilities

- Governance controller is trusted local application construction, not remote
  identity infrastructure. Subject/Model have no controller handle. Root arbitrary
  code/memory edits and privileged raw full-DB clones are outside this boundary.
- Synthetic source facts are fixture observations, not real user/private records.
  Generic mechanisms are qualified offline, not a human personality claim.
- Real utterance generation/truthfulness in unrestricted language is not implemented;
  semantic assertion/timing eligibility is enforced. No automatic disclosure sender.
- Only typed daily recurrence, not arbitrary calendar/NLP. IANA timezone database
  must be available; unknown zones reject. Bounded candidate coverage can be UNKNOWN.
- Fixture ActionKernel use is a narrow isolated synthetic realm, not an authorization
  to turn on production Actions. Real Manager principal onboarding remains NOT_RUN.
- No real ModelPort, E12, real memory ingress, host bridge/receipt operation,
  perception, social account, device, real file exploration or production migration.
- Portable subject export, identity forks, distributed authority and full world
  model remain later stages. No second loop/Store/runtime was introduced.

## 21. Production and frozen baseline

Production/private reads/external model calls/real external actions are0. Main,
R045, FIRST_REAL_ASTRBOT_SHADOW and its tools/plugin files are unchanged relative
to the ADR2 base. Production review and real-proof pins remain EMPTY; real memory
ingress remains deny-by-default. Existing production status is not upgraded from
these fixtures. No merge/deploy or next real integration was started.

## 22. Review and next point

Review this branch against the ADR2 anchor, then integrate through an independently
approved development merge; do not cherry-pick schema9 without its services and
privacy/recovery checks. Keep the original eight-commit order. The recommended next
milestone is independent architecture/code review of the offline candidate and a
bounded source-domain design for future realized actions. It is not production
rollout or automatic E/G integration. Final status and complete field-by-field
handoff are in the evidence summaries / delivery report; final SHA is verified
against origin separately to avoid self-referential hashes.
