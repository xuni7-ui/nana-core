# H1 developer / future operator runbook

This is an offline semantic-grounding candidate. It enables no capture, hands,
social account, deployment, installation or production migration. No push is part
of H1. The unrelated R03 bundle is not an input.

## Reproduce on the existing approved development runtime

```sh
.venv/bin/python -m pytest -q tests/h1_semantics
.venv/bin/python -m nana_core.presence.semantic_demo --directory /tmp/h1-fresh-main --output /tmp/h1-main.json --hours 48
.venv/bin/python -m nana_core.presence.semantic_demo --directory /tmp/h1-fresh-contrast --output /tmp/h1-contrast.json --hours 48 --variant 1
.venv/bin/python -m nana_core.presence.semantic_demo --directory /tmp/h1-fresh-wall --output /tmp/h1-wall.json --wall-seconds 300
.venv/bin/python -m pytest -q tests
```

Every directory must be fresh. The demo rejects reusing an existing Store. Do not
substitute a production Store. The fixtures generate public PNG/WAV/MP4 in local
sandbox scope; narrow SYNTHETIC oracle outputs are not real model qualification.
Five real SIGKILL cuts execute only child development processes. Test processes
must be allowed to use the existing ffmpeg/Pillow/bwrap installation; do not
install dependencies as an implicit recovery step.

## Application integration

1. Establish the existing single Runtime/lease and explicit schema13 development
   Store, ContextPolicy and exact transport. No new identity/store/runtime.
2. Ingest bounded known-public bytes through PerceptionService (or its flat,
   no-follow/no-hardlink public-root importer). Obtain source_memory_id.
3. Construct MediaSemanticService with the existing CognitionSession. `prepare`
   takes idempotency key, exact source memory ID and exact original bytes. It
   verifies normalized pixels/PCM/frame intervals and source/provider bounds.
4. `execute` uses existing PREPARED→CALLING→PROPOSED/UNKNOWN/FAILED/STALE/REJECTED.
   Never retry a CALLING/UNKNOWN/failed key. Stale/unknown is not empty success.
5. `ground` binds the accepted interpretation to a trusted entity/predicate. It
   returns semantic_memory_ids, belief_ids, provider/model/origin, coverage/gaps,
   ASR status and epistemic disclaimer. These are not commands or permissions.
6. Offer a semantic memory through existing WorldLoopWork.observe; C decides
   attention/intention/no-action. There is no callback that auto-adopts a goal.
7. Separate video/audio readings can be associated only with identical container
   digests and compatible duration. Do not claim sampled frames cover all video.
8. Delete via the existing authorized MemoryService/PrivacyJournal. Source delete
   invalidates downstream Memory/Record/world/context/concern/plan support. A
   summary-only delete leaves original technical observation intact. Never restore
   erased content from a detached report; portable restoration remains quarantined.

## Future live-provider qualification (NOT_RUN here)

No provider/credential was configured in this task's managed environment. Do not
search secrets or create credentials/accounts. If separately configured and
legitimately authorized later, trusted application construction may provide an
exact HTTPS endpoint/provider/model/credential and a SemanticDescriptor to
OpenAIMediaTransport. Pin supported modalities and ASR capability honestly.
Use PUBLIC generated samples only, finite cost reservation via CognitionBudget,
explicit source ContextPolicy, bounded calls and measured UNKNOWN billing.

Image is normalized PNG, audio normalized PCM WAV, video sampled PNG parts with
explicit intervals; OpenAI-compatible transport maps them to image_url/input_audio.
Native video uploads, live streaming and universal vendor compatibility are not
implemented. Reject unsupported modalities; do not switch provider/model or spend
additional resources automatically. No source path, Store, Grant or Subject handle
is sent to the provider. Source context is citation metadata, not arbitrary text.

Stop live qualification on wrong model/origin/digest/citation, source deletion,
privacy denial, timeout, partial output or unknown effect; retain UNKNOWN/FAIL
and review rather than blind retry. Real ASR, OCR/object accuracy and video scene
quality require their own independently labelled test sets. H1's tone fixture
that contains a deliberately false transcript proves contracts only.

## Recovery / rollback

Stop only the development runtime you started. Reopen the same development Store
under a fresh lease. Existing CognitionSession.recover quarantines CALLING and
old-owner PREPARED as UNKNOWN. It never recalls the provider automatically.
Accepted PROPOSED media may finish idempotent historical belief materialization
with current source checks; it does not restore an old execution authorization.
World/concern/C-cycle commits retain existing replay keys. Provider instances,
Grants and tool handles are trusted application construction, not portable memory.

No schema migration is required by H1. Roll back development source to the frozen
Stage E anchor in a separate checkout if needed; retain H1 model-derived records
as historical data. Do not rewrite/delete unknown work or reset the current branch.
Do not run production rollback commands from this runbook.
