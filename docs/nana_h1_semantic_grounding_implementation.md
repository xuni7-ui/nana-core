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
