# H1 semantic grounding — implementation log

Base dcaf30fe1581c5fff19ab302a83b4b56e69487a0, branch
`dev/nana-core-h1-semantic-grounding-v1-codex`. Stage E remains frozen offline.
No push is authorized for H1. Preserve the unrelated untracked R03 bundle.

## M1 — integrated contracts and grounding (development)

Existing schema13 /43 tables suffice: same cognitive_requests lifecycle,
RecordService payloads/dependencies, MemoryService erasure and WorldModel claims.
Default C7/D8 unchanged. No new schema/table/Store/SubjectLoop/Runtime/worker.
SemanticDescriptor is an ephemeral modality capability description attached to the
existing trusted transport construction; no new provider registry or live gate.
Actual authority remains with existing policy/Kernel/Manager/Grant.

MediaSemanticService packages bounded normalized PNG/PCM WAV/sampled PNG frames
from exact decoded bytes. Every part carries digest and source time span; request
checks these against committed technical pixel/PCM digests. OpenAIMediaTransport
renders multipart image/input_audio content using the same HTTP lifecycle. Ordinary
GOALS/PLAN/LEARN/SKILL requests remain unchanged. Provider credentials are explicit
construction only; managed environment reports no configured providers/secrets.

MEDIA role uses the original CognitionSession CALLING/UNKNOWN/deadline/epoch/world/
subject/source fences, output quotas, and deterministic request/response digests.
ContextAssembler's explicit source-only mode omits unrelated memory/relationship
blocks while preserving required-source/privacy/contradiction/token rules.
Source-only does not bypass a conflict or force a source into an insufficient budget.

Structured observations distinguish visual attributes/events/text, acoustics,
ASR transcripts and derived summaries. No speaker identity enum; no intent/command
adoption; MEDIA output cannot include interests/plans/code. Interpretation and ASR
remain MODEL_DERIVATION, never RAW_OBSERVATION. Confidence is provider-estimated,
not calibrated verification. Partial coverage and unsupported ASR stay explicit.

Accepted historical PROPOSED media can resume grounding after restart as beliefs,
not fresh cognition or execution permission. Grounding rechecks source support,
reply digest and request/provider correlation. Per-claim evidence keys and original
WorldModel ingestion give replay idempotency through intermediate crash cuts.
A new Ground binding must exactly match a previously grounded request.

The local harness processes actual pixels/PCM but is a deliberately narrow synthetic
oracle: dominant-color fields / periodic energy / sampled-field summary. It is not
an ASR, object-recognition or general semantic model. No live model is configured.
LIVE_SEMANTIC_PROVIDER=NOT_RUN; real image/audio/video semantic quality=SEMANTIC_NOT_RUN.

16 initial H1 tests PASS, including actual three-codec grounding, conflicts/direct
correction, filtered context, summary/source erasure, malformed/partial/timeout,
stale and forged origin/model/source/span/ASR/summary/code rejection. Later stages
will qualify system causality, actual SIGKILL and final regression/soaks.

## M2 — integrated priorities, recovery, audio linkage and life qualification

The same semantic input can produce EXPLORE / REST / WATCH / ASK through the
existing SubjectLoop and independently sourced situation cues. H never commits a
Judgment, goal, Grant, Manager rule or external action. Historical media proposals
resume as beliefs; CALLING/old PREPARED requests recover UNKNOWN without retries.
Five actual SIGKILL cuts cover decode, audio CALLING, video accepted proposal,
belief commit and C commit; exact review-event lineage is checked separately from
legitimate maintenance decisions. Portable transfer retains semantic beliefs and
identity, revokes Grants and reconstructs no provider/runtime/controller handles.

Separate video/audio ingress of the SAME source-container digest can be linked;
visual frame intervals and audio transcript/event lineage remain distinct. Video
with no decoded audio source explicitly requires separate audio ingress. Sparse
24-frame/8-sample test reports actual uncovered gaps; no full-video claim.
The ASR transcript test is a deliberately wrong synthetic contract response over a
tone, proving even command-looking transcripts remain model beliefs. It is NOT ASR
execution or speech accuracy evidence. Actual speech-recognition execution=NOT_RUN.

The two48h environment variants use one code path with different generated pixels,
tones, annotation-processing needs and attention options. The primary trace has a
failed annotation-formatting step, independently tested existing language learning,
C-approved replan and generated/repaired/reviewed skill use. The contrast uses a
different normalization workflow, REST instead of optional exploration, and a
TOKEN_ANALYSIS skill; it does not claim a failed-goal lesson where none occurred.
F/G/I are the existing services, not new media planners/learners/installers.
Only pure local synthetic Kernel actions execute. Exact known generated pixels,
not provider self-report, back the later direct visual correction.

The H1 harness now distinguishes primary observed sources from background context,
so an unrelated old observation cannot masquerade as a new opportunity. The request
pins primary_source_refs as a descriptive focus field, not authority. Regular E
harness behavior/worker implementation is unchanged. Idempotency-key/source binding,
source/request/response digests and canonical replay equality are checked. Unknown
billing stays null/UNKNOWN. Tests are included in the default pytest testpaths.

Full regression, final-source paired worlds, focused wall run and final evidence
are pending at this checkpoint. No new schema/Store/loop/worker or real provider.

Pre-freeze retained failure `test_media_context_routes_parts_not_untyped_source_body`
showed that source-only mode still forwarded source Memory.text. Repaired by
projecting only citation/epistemic metadata in media context; typed parts are the
only content channel. Existing normal ContextAssembler behavior is untouched.
Final targeted32 PASS, including two48h worlds, six recovery/portability checks,
five true SIGKILL cuts, provider/ASR/epistemic/privacy/deletion fences. Final whole
repository result and frozen-source wall/world runs follow this business anchor.

## Final delivery / source and status

**GLOBAL_STAGE_H1_REAL_SEMANTIC_GROUNDING = OFFLINE_CANDIDATE_READY.**
Base `dcaf30fe1581c5fff19ab302a83b4b56e69487a0`.
Source/test anchor `20758ecec2ef02efc3459985051cfbc3036b4697`.
Containing final documentation/evidence commit is HEAD_FINAL (read with git rev-parse
HEAD); no self-referential commit hash is invented in its own content. Three local
logical commits; no push. Main/R045/production unchanged; old bundle preserved.
Historical checkpoint fingerprints describe their collection snapshots; final
manifest describes current final source/evidence and excludes itself/09_STATE.

| Module | Responsibility / input / output / state |
|---|---|
| semantic_contracts | strict descriptor/parts/observation DTOs; explicit source, spans, uncertainty and supported ASR; no persisted authority |
| semantics | exact decoded source bytes→bounded parts→existing CognitionSession; PROPOSED→model-derived Memory/WorldBelief; no decision/executor |
| OpenAIMediaTransport | native image/WAV/sampled-frame wire adaptation, exact construction identity; existing HTTP quotas/timeout/UNKNOWN worker |
| ContextAssembler | optional media source-only metadata projection; all normal defaults and privacy/contradiction/token/source checks retained |
| semantic_harness | SYNTHETIC actual pixel/PCM oracle; source-focused proposal fixture, no real model/general recognition/ASR |
| semantic_demo | finite public environment inputs over existing Runtime/Subject/F/G/I; no scripted final Actions |
| existing world/concern/C | sourced belief/conflict→opportunity→sole final Judgment/intention/no-action |
| tests/h1_semantics | source/privacy/epistemic/restart/deletion/portability/5 real SIGKILL and paired48h qualification |

No schema migration or new table: explicit13/43 tables; old defaults7/8 remain.
Raw content is normalized PNG, WAV PCM, sampled96x64 PNGs; parts are capped98304
bytes (descriptor may lower it). Video audio is separately ingressed from exact
same container, never silently described as sampled-frame coverage. Summary-only
erasure leaves original technical source; original-source erasure removes supported
semantic/world/concern/plan context. Detached exports/raw privileged snapshots are
outside the managed privacy journal's revocation boundary.

Full: **1049 passed /0 failed /1 skipped(E12)**,147.227s JUnit/147.32s CLI.
H1: **32 passed**,23.726s. Five real SIGKILL cuts PASS; portable pending request
recovers UNKNOWN, stable beliefs retain MODEL_BELIEF, no execution handles restore.
Main48.0953h:3 goals/6 verified local synthetic Actions/4 Experiences/1 Lesson;
contrast48.1025h:2/4/2/0, with distinct beliefs, priorities, rest and learning needs.
F checked-lesson replan / G original9 stages / I original generated-test-review-use
all exercised, no duplicate implementations. H1 does not train semantic models.
Final-source wall301.344s:6 HTTP calls,14 beliefs,2 C cycles,0 Actions, FD4→4,
queue0, identity stable. Runtime/Scheduler/SubjectLoop/Kernel and provider worker
execute/recover unchanged; the final-source >=5min focused semantic mode applies.
Earlier exploratory/pre-freeze runs are not credited as final-source duration.

Real provider/ASR/OCR/object/scene accuracy/live capture NOT_RUN. Each modality's
real semantic quality remains SEMANTIC_NOT_RUN. Narrow harness outputs are useful
contract/causal/recovery evidence, not real model qualification. A deliberately
wrong transcript-shaped fixture proves it cannot acquire command authority; it is
not counted as ASR execution. No live devices, accounts, models or private data.
No unresolved core-invariant failure. Limits: finite8-frame/30s/byte-bounded media,
conservative stale/deletion policy, OpenAI-compatible wire shape without live API
qualification, no universal vendor adapters or native streaming. Next recommended
work is separately configured public live-provider quality/cost qualification;
do not automatically enter H2 capture or hands. See runbook and A–J reconciliation.
