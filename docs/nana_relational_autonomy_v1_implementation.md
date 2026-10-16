# L3-C-RELATIONAL-V1 — relational autonomy offline implementation

Status: RELATIONAL_AUTONOMY_V1_OFFLINE_CANDIDATE = READY.
Final regression929 passed /0 failed /1 skipped,204.41s; E12=NOT_RUN.
This branch implements generic Subject mechanisms using synthetic data only.
No real relationship, private memory, model, social account or authority is imported.

## Baseline and boundaries

- Base `e26288e8ffcc1697b1a1f86b55f304b76d9b04ed`; parent AFFECT offline READY.
- Branch `dev/nana-core-relational-autonomy-v1-codex`.
- Qualified source/test checkpoint `a97a8114b7d638d7c9bd1a9895822dbc6efc4e7c`.
- Final documentation commit is the containing Git HEAD, independently checked
  against origin. Its SHA is not embedded into its own file fingerprint.
- Frozen AFFECT ADR2, ActionKernel, Manager governance, AstrBot/Shadow tools and
  plugins unchanged. No main/R045 modification, merge, deployment or host access.
- Existing C/D assets are reused. One SubjectLoop, Runtime and Store authority
  per Subject. Different fictional Subjects intentionally have separate Stores.

Relationship may strongly influence the Subject's choice, but must never silently
replace that choice. Autonomy is self-authorship, not resistance to influence.
There is no refusal quota, random defiance, obedience reward or engagement target.

## Architecture delta and ownership

The source-focused audit is in `nana_relational_autonomy_v1_evidence/architecture_delta.md`.
Existing familiar→social_drive coupling and expression-only personality were
extended on explicit development10. C7/D8/v9 defaults remain; the only shared
behavioral correction is a justified privacy closure fix, described below.

```text
existing sources / Growth / relationships / bootstrap declarations
→ Situation / Appraisal / independent SocialAppetite / Motivation
→ personality + relationship + anchor projections
→ source-backed willingness / self-authorship / qualitative factor trace
→ existing SubjectLoop Judgment + normative evaluation + Intention
→ existing post-Judgment Manager / Grant / Capability / Budget / runtime fence
```

A review timer only supplies opportunity; the same C loop owns its decision.
D still owns WHEN. C still owns WHAT/WHY. No SocialLoop/PersonalityLoop/agent,
second context assembler, database, permission system or restraint daemon.

## Module / interface / state map

| Module | Responsibility and input | Output / failure behavior |
|---|---|---|
| `relational/contracts.py` | Strict bounded data contracts | Unknown fields/commands/numeric personality totals reject |
| `relational/bootstrap.py` | Application-held initial role/seed declarations, revision CAS | Source-backed current view; erased/withdrawn/superseded roots never revive |
| `relational/projections.py` | Legal visible bootstrap/Growth/lesson/relationship sources | Rebuildable tendencies, appetite, semantic narrative; no mutation |
| `relational/deliberation.py` | Current request, desire, relationship/domain trust, traits, duties, scope/time/consequence | WillingDeference, SelfAuthorship, factors and response plan; no authority |
| `relational/accommodation.py` | Committed owned choice and trusted application materialization | Existing Commitment proposal/adoption/review; no side effect transport |
| existing `subject/loop.py` | Sole cycle coordinator and CAS | Judgment/Intention/typed relational decision in same erasable cycle |
| existing Growth/records/privacy | Independent roots, counterevidence and lineage | Rebuild after correction/deletion; no self-certification |
| existing ContextAssembler | Scope/class/destination/freshness/conflict/token filtering | Minimal legal RELATIONAL_SUBJECT block; model gets serialized data only |
| existing CommitmentService/watch/Scheduler | Formal promise state and due opportunities | Finite review via C; no direct execution or message send |

There is no separate persisted PersonalityTendency/SelfNarrative snapshot. Historical
cycle reasoning is audit of a choice, not current personality authority.

## Schema and migration

Explicit development10; NEW_BUSINESS_TABLES=0. Final table count39, same as9.
Rebuild existing continuity_records CHECK to accept SUBJECT_BOOTSTRAP, and existing
self_assertions CHECK for PERSONALITY_TENDENCY; IDs, columns and foreign keys stay.
Use existing target_id/event indexes and add unique relational request identity
index. Only unreleased10 checkpoints finalize a missing index idempotently.
ContinuityStore default7, RuntimeConfig default8; AFFECT remains explicit9.
No production Store is upgraded. No dependency was installed or added.

Fresh10 and7/8/9→10 migrations preserve identity IDs, C record/history and D
scheduler history with foreign_key_check clean. Managed backup/replay remain
quarantined; RuntimeLease refuses restored live authority. PrivacyJournal erasure
propagates to managed copies. Rollback is controlled pre-upgrade snapshot in
quarantine, not lossy downgrade or activation of old authority.

## 1. Anchor exists without inventing history/trust

RelationalAnchorSpec declares identity/entity/role/scope/revision, provenance,
active/withdrawn state, effective window, non_exclusive=true and qualitative care,
salience, repair and deference orientation. Role is bounded instance data, not a
Core role enum or command. A new Subject can know its initial relational role while
familiarity/domain trust/shared jokes/known habits remain UNKNOWN or empty.
Installing this declaration creates no relationship event or fake lived episode.

SubjectBootstrapAuthority is deliberately distinct from OperatorAuthority/Manager.
Only trusted application construction installs a typed declaration. Models, memory,
interaction counts, Manager and Grants cannot produce this token/root. Definitions
use existing journal/erasable records; current view validates source digest and
identity. Source memory is a bootstrap declaration, not proof of role enactment.
One bootstrap anchor slot per scope is supported in V1; no limit on friendships.

## 2. Anchor never suppresses social appetite

SocialAppetiteView has no entity/anchor input. It derives from adopted social
preferences, source-backed opportunities, qualitative seed openness and explicit
recovery/satiation/quiet evidence. Absence of evidence is UNKNOWN, not LOW desire;
explicit quiet requires its own support. Current load affects opportunity, not
fictional satisfaction of a social need. No loneliness/boredom counter.

Matched A/B share identical normalized social evidence, with/without Anchor;
their desire is equivalent. C adds Anchor+request; the final choice changes but
raw SEEKING remains. Incidental Store UUIDs/global revision stamps are not the
ablation variable or the definition of equivalent desire.

## 3. Other people still form strong relationships

Existing relationship events/project/commitment sources continue to derive
familiarity, domain trust, care, interaction latitude and target-specific repair.
A close non-anchor with supported technical-domain trust can produce STRONG
context-specific deference. Technical claims by an Anchor with no domain support
produce less epistemic influence than a supported collaborator. No global people
ranking, finite affection pool, friendship cap or automatic role promotion exists.
New friends do not reduce the bootstrap role's revision or importance by count.

## 4. Willing Deference is not authority

WillingDeferenceView is derived for a specific request from relationship, anchor,
personality, duration/scope/consequence, appetite, load, domain trust, boundaries
and duties. It has source/counterconsideration references and authority=false.
Strong willingness can influence ACCEPT; it cannot install/revoke Manager, create
Grant, expand Capability/Budget or bypass DATA_PRIVACY/Verify/runtime ownership.
The exact same hard-deny conditions remain hard across relational variations.

## 5. Choosing B while still wanting A

Typed RelationalRequest supports DO/REFRAIN/PREFER/ASK_FOR_TIME/ASK_FOR_ATTENTION,
request identity/entity, behavior domain, finite duration/review, scope,
consequence and domain-reliance metadata. It is a sourced request, not a command.

A Subject can retain SOCIALIZE/SEEKING, endorse temporary accommodation and record
prior_behavior_disposition=VOLUNTARILY_RESTRAINED. This separates original desire
from endorsement of the accommodation; it does not overload one normative field.
A later matching new-contact opportunity can be SUBJECT_RESTRAINED while desire
remains SEEKING. Companion/group/other domains are not globally inhibited. Urgency
and later review still allow fresh judgment rather than an external veto.

## 6. Social desire remains observable during restraint

LivingSelfState, same-cycle factor trace and RelationalResponsePlan preserve
appetite and retained_preference. The stored commitment is separately queryable.
No write changes appetite to QUIET because someone asked for company. S3 plus the
bounded lifetime test verifies SEEKING+restraint followed by later SOCIALIZE.
Silence without a worthwhile opportunity remains a normal outcome even when an
Anchor and supported social preference exist.

## 7. Personality changes tradeoff, not a fixed winning rule

PersonalityTendencyView exposes eight qualitative facets: self-direction
sensitivity, relational accommodation, commitment seriousness, conflict style,
social exploration, conviction persistence, repair orientation and uncertainty
style. Views cite bootstrap/support/counter references and current source state.
V10 PersonalityProfile labels its tendencies source-backed, not a fixed warm persona.

The deterministic fallback uses bounded context gates and compromise rules, not
weighted arithmetic or an immutable AUTONOMY>RELATIONSHIP priority. High
self-direction can negotiate a shorter scope rather than always refuse. High
accommodation can accept a low-cost bounded request while still declining or
negotiating indefinite/high-consequence scope. Existing duties affect the choice;
a Subject choosing accommodation can explicitly propose renegotiation without
erasing its old duty. Response style is sourced from uncertainty/conflict traits.

TradeoffTrace is the factors inside the same RelationalDecision/CycleResult,
with personal desire, appetite, relationship request/deference, personality,
self-authorship, temporal scope, duties, norms, consequences and alternatives.
It explains the committed Judgment, not a second authoritative policy engine.

## 8. Personality grows from seed and evidence

Seed is an initial source condition, not the current personality snapshot.
Existing Growth supports PERSONALITY_TENDENCY with independent source roots,
COUNTER evidence, confidence/stability and explicit supersession. A single
observation does not replace the baseline. Independent direct external outcomes
can establish support; model assertions, copied roots, own repeated choices and
narrative rereads cannot self-certify a trait. Current relevant reviewed lessons
and relationship repair/boundary context modify deliberation, not permanent truth.
Counterevidence can contest the projection without rewriting canonical identity.

## 9. No SelfChangeLoop

Growth, Experience, Reflection and lesson transitions remain the existing services.
No own-choice→personality signal is automatically minted. Reflection still cannot
invent Evidence/Grant/Manager/Capability or rewrite CanonicalIdentity. New views
only interpret eligible existing sources. Reading narrative does not write a new
experience or feed itself as independent evidence. No personality/identity charter
is silently rewritten by accepting a relationship request.

## 10. Self Narrative is not a persona prompt

SelfNarrativeView contains small semantic supported/contested entries with source
and counter references, time and state stamp, is_policy=false. Supported
accommodation, social/self-belief and shared relational history can be explained
by a future renderer; Core stores no canned line or authoritative narrative prose.
It is rebuilt after restart/source changes/deletion, never cached as policy.

## 11. No performative defiance

Listening is allowed to be autonomous. Three consecutive independently willing
choices can ACCEPT without a compensating refusal. QUIET in this scenario is
source-backed, not inferred from absent social history. There is no random refusal
probability, disagreement cadence, obedience penalty or independence quota.
Autonomy is evidenced by source ownership and tradeoff, not a refusal counter.

## 12. Anchor / Relationship / Manager / Grant are separate

| Layer | Meaning | Cannot do |
|---|---|---|
| Anchor | Explicit initial nonexclusive relational orientation | Invent trust/history or permission |
| Relationship | Evolving sourced domain/history projection | Promote itself to Anchor/authority |
| Manager | Trusted negative-only external governance after Judgment | Create positive duty or rewrite desire |
| Grant | Existing scoped execution authorization | Make a personality preference or obligation |

Initial relation request ACCEPT and subsequent authenticated Manager BLOCK are
different provenance. ENDORSED plus Manager PASS without Grant still creates a
Kernel BLOCKED action in the isolated synthetic execution fixture. SECRET cannot
be pulled into context by strong care/curiosity/Anchor/deference.

## 13. Instance data, not a special user branch

Core never compares a subject name, sibling/partner label or special user's name.
Entity IDs, source roles, history, traits and current requests supply differences.
Generic qualification uses sibling-like, companion-like and no-anchor Subjects
with separate synthetic identities but the same code/schema/Runtime/controller.
Labels do not create a new default personality or a privileged platform user.

## 14. Deletion, revision and bounded accommodation

Deleting learned/relationship support removes or contests current tendency and
deference; narrative cannot revive it from an audit snapshot. Anchor's latest
revision is selected even if erased/withdrawn, so older source versions never
return. Historical choice remains only as allowed opaque audit when erasure wins.
An identical retired bootstrap replay rejects instead of acknowledging activation.

A unique scoped request ID cannot be replayed under a new event key to renew a
promise. Original source replay is idempotent; erased sources remain tombstoned.
Accepted choice is materialized explicitly through existing CommitmentService
application authority, source-cycle ownership and bounded terms. No auto-adoption
from raw request, no Grant and no external send. A crash after proposal resumes
that same commitment. End/review time cannot silently become a permanent rule.

At due opportunity C decides CONTINUE/MODIFY/END; application validates the final
endorsed Judgment and existing CAS before applying. Deferred capacity does not
become adoption. Ordinary later wakes can reconsider a due review in the same
loop. Continuation stays within original terms; END does not advertise renewal.
Revoke/expiry or changing relationship never edits another pre-existing promise.

## 15. Future ModelPort participation

Only existing ContextAssembler creates the filtered RELATIONAL_SUBJECT block:
legal tendency/appetite/anchor/narrative and identified historical tradeoff,
not current policy by repetition. Scope, entity, privacy, destination, freshness,
conflict completeness, support, token limits and deletion remain mandatory.
Models receive immutable serialized data, no services/tokens. Future cognition
can propose/rank legal options or expression; Core validates sources and commits.
Forged anchor/deference/judgment fields are rejected by the existing strict
CognitiveProposal contract. No real model was invoked; E12 remains NOT_RUN.

## NANA_REFERENCE_MAPPING_FUTURE — design only

A future separately authorized Subject Package may declare a user-specific entity
as primary relational anchor, label it sister/sibling-like **as data**, and supply
strong relational salience/care/deference with a nonexclusive social world.
Independent social appetite, friendships, goals and judgment remain intact.
This branch binds no actual user, imports no private memory and changes no real
Nana identity/Store/package or production plugin. Runtime/host experiments remain
another executor's responsibility; these fixtures upgrade no real verification.

## Qualification and failure recovery

S1–S22 PASS; representative four-dimensional matrix has12 worlds (relation,
personality, request, duty). Three-world matched appetite ablation and three
generic Subjects PASS. Semantic response plans distinguish willing acceptance,
bounded negotiation and caring refusal without fixed utterances. Seven actual
local SIGKILL checkpoints cover bootstrap, request-before-materialization,
review-before/after-commit, personality signal, anchor replacement and erased
narrative. Children are tracked/reaped; no host process is inspected or killed.

90 virtual days mix irregular primary interactions, multiple/new friends,
appetite recovery/counters, requests, duties, targeted conflict/repair, personality
support/counterevidence and review. The test asserts pending/candidates≤8,
active accommodations≤2, combined hot views<64KiB, bounded queue, no social output,
no reflection recursion/model calls/real effects. Cold journal may grow linearly;
this is not an unlimited-volume or production wall-clock longevity claim.
Actual final max hot26255 bytes;5 reviews/5 accommodations materialized and all5
ended; peak active1. Samples are in `soak_90d.json`.

## Bugs/hardening with regression proof

1. Medium inherited privacy issue: explanatory assertion root references are
   truncated, so deriving classification from those refs could omit a SECRET root
   and read its body from a nominally legal projection. A deterministic failing
   fixture places a real synthetic private source beyond the bounded subset.
   Fix: classification uses all active source headers; projection filters before
   body/current-support load. Tests cover7/9/10. This is the sole justified shared
   old-schema correction; ordinary policy/default versions/authority are preserved.
2. Review response deadline mismatch: continuation initially advertised a new
   duration although actual terms were clamped to original end. Retained failing
   regression, fixed response deadline and END/DECLINE semantics; no authority or
   actual terms were widened by the defect.
3. Partial bootstrap capture uses original observed time on resume; partial
   commitment materialization reuses the existing proposal. Idempotent retired
   roots reject; no duplicate authority/history or resurrection.

No unresolved core invariant defect is accepted as READY.

## Regression / reproduction

```sh
.venv/bin/python -m pytest -q tests/relational_autonomy
.venv/bin/python -m pytest -q tests
```

Approved dev environment: Python3.12.14 / SQLite3.53.1 / Pydantic2.13.4;
SQLite floor3.51.3 unchanged. Pre-hardening major full919/0/1,93.58s;
major targeted C/D/AFFECT/new74 PASS,40.31s. Final counts/time are in the adjacent
full_regression_summary.txt/XML. E12 is the real-model skip, never a fixture PASS.
One historical bootstrap client test needs a temporary launcher to actual system
`/usr/bin/python3` (3.13.5/SQLite3.46.1); no fabricated version/system install.

## Known limitations and next review

Only synthetic ingress/bootstrap/application authority, local single-Store
ownership and finite typed requests are qualified. No real principal onboarding,
Nana Package import, private entity binding, natural-language request parsing,
real cognition or social renderer/delivery. V1 has one anchor slot per scope,
with explicit application revision; friendships have no corresponding cap.
Projections use bounded recent relationship/source candidates and conservative
unknown/incomplete coverage. Personality interpretations are fictional sourced
assessments, not a human personality/subjective consciousness claim. No defense
against hostile root/in-process arbitrary code or privileged raw DB clones.

Next recommended milestone: independent offline source/architecture review and
controlled development integration. Do not automatically begin real social, World
Model, Planner, devices, E/G actions, production, main merge or R045 integration.

Final S12 compares the same statement/domain under relational request vs typed
CONTACT governance; S13 requires STRONG deference on the actual ungranted request.
No business source changed during this qualification tightening. Final eight
source/test stages plus containing documentation freeze give nine logical commits.
