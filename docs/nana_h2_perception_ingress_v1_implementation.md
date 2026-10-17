# H2 Perception Ingress & Sensor Runtime V1

GLOBAL_STAGE = H. WORKSTREAM = H2_PERCEPTION_INGRESS_SENSOR_RUNTIME_V1.
Scope: OFFLINE / SYNTHETIC sensors and generated public files. No live device/provider/Hands.
Base `a4abd5ce230848ae6667e5e5362964636e3ead08`; branch `dev/nana-core-h2-perception-ingress-v1-codex`.
Frozen source qualification commit: `798cc33` (full SHA in evidence). Final delivery commit contains this report/evidence; no business source change follows the qualified source.

## Implemented structure

`continuity/sensors/contracts.py`: strict source profiles, observation requests, captured-media metadata and explicit HostPerceptionResolver. Source kinds are descriptions, never permissions. Capture bytes are excluded from DTO serialization/repr. Only application-injected ports exist; no class-path loading, command sensors or discovery. Descriptor privacy_floor is trusted host classification; a frontend profile cannot lower it.

`config.py`: independent host JSON configuration schema1, inheriting original ProviderConfigService private atomic persistence primitives. Existing Provider config API remains compatible. Exact document revision CAS, strict schema/unknown-field rejection, private files, O_NOFOLLOW, bounded reads, flock, temp fsync/replace/directory fsync. Profile revisions use the monotonically increasing document revision at each profile mutation, including removal/recreation. An old WATCH/capture revision cannot alias a new device binding. Config corruption or dangling/unavailable bindings fail closed. Configuration mutations create no Subject memories/events/cycles.

`adapters.py`: application-pinned FILE_IMPORT and synthetic screen/camera/microphone/general media ports. File access walks root components using directory descriptors/O_NOFOLLOW; regular single-link bounded file checks precede reads. No model/frontend-supplied file path. Generated PNG/WAV/MP4 qualification really decodes bytes. File descriptor reading is isolated in the port and then feeds **original PerceptionService.ingest**; calling ingest_file inside a port would violate the port's no-Store contract. The original public ingest_file remains compatible.

`coordinator.py`: owner-thread resolve → classify/allow/budget → capture/verify → original local codec ingress → optional existing CapabilityRouter/H1 semantics. It does not form motives/goals, infer importance or decide C behavior. It uses existing Runtime health operational metadata, existing events for durable reservation/dedupe, existing deletable records/memories for observation truth. No added Store, table, scheduler, worker loop or brain.

`presence/runtime.py`: an optional perception hook participates in original step/Scheduler/queue ownership. A capture opportunity is intercepted before ordinary C cognition; it never acts as an implicit user instruction. Foreground user events retain queue precedence. Six explicit safe points drain incoming events and check preemption. Pending ticks coalesce both across missed time and while an older tick remains queued. One active schedule/one pending periodic opportunity per source; bounded mailbox, pending requests and serial capture. No observation daemon or thread-while-true exists.

`application.py`: application-owned PERCEPTION_SETTINGS/PERCEPTION_STATUS and typed config/capture transitions extend existing B10. No UI. Runtime.application accepts application-provided settings services; frontends never receive resolver/controller/device handles.

## H1 reuse and ephemeral media

PerceptionService gains MediaSourceDescriptor while preserving PublicMediaSource. Technical decode persists only metadata/statistics/digests, with original Evidence → Memory → WorldModel dependencies. PERSONAL/SECRET images decode in memory; exact mono16k PCM WAV uses an in-memory path. Private VIDEO fails closed until a memory-only decoder is supplied; public generated video uses existing sandboxed ffmpeg/ffprobe and sampled frames.

The original CognitionSession now optionally reserves against the full temporary media payload while persisting digest-only MediaPart metadata (`data_b64=null`). Validated byte attachments exist only in the current session/request, outside serialization. Original OpenAIMediaTransport and fixture proposer consume the attachment. Native HTTP loopback verifies the wire path. Legacy H1 full-envelope calls remain compatible. This task does not rewrite historical H1 records or pretend old full-envelope experiments used ephemeral storage.

Prepared ephemeral requests without their attachment cannot dispatch after restart. CALLING remains UNKNOWN on interruption; no retry/fallback. Accepted responses can be grounded from their source-bound sanitized metadata without rereading media. If the original exact profile is unavailable, recovery parks rather than silently substituting another provider. Missing provider/expired bytes never invalidate an already verified technical capture.

## Lifecycle and causality

Capture identity binds source/profile revision, source event identity, event time, sequence and byte digest. Request keys and capture IDs are separate: a repeated request is terminal/replayed; repeated exact capture under another request reuses the observation; equal bytes at another event time create another observation. Short exact-digest debounce may skip semantics but retains the new technical/time observation. Debounce is also scoped to routing revision; a changed model is not silently represented by an older result.

Event time is the sample time, observed time is host receipt, known_at is Memory.ingested_time_us / derived record creation. Technical and semantic facts preserve these distinctions. Predicates include capture identity and operation, so array ordinals never identify observations across captures.

REQUESTED → CAPTURING → CAPTURED → DECODED → GROUNDED, with separate per-operation PROPOSED/UNKNOWN/FAILED/deferred states. Host/Manager/privacy/source errors do not rewrite an earlier desire. When bytes are lost at a safe point, metadata explicitly records SOURCE_SAMPLE_EXPIRED or SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED. A later fresh capture is a new event. No media cache is used for delayed semantic retries.

Event-driven producers retain one bounded volatile sample and call notify_sample(), which posts only source/revision/sample-key metadata through existing Runtime.post(). Runtime owner pulls that exact pending sample. A missing volatile sample is expired; no fabricated recovery. Periodic capture uses the existing Scheduler. A sourced WATCH cycle may temporarily lower interval within host min/base bounds; it must cite the exact source revision. H2 cannot invent curiosity or WATCH.

Manager veto is read from the existing authenticated negative-only governance snapshot. It may target a source or canonical host binding digest (`synthetic://perception/resource/<digest(adapter_ref,resource_ref)>`); the latter covers profile aliases. PASS does not provide a Grant/permission. Host allow policy defaults to deny, remains independent, and resource/controller configuration is not relationship authority. Governance metadata never becomes a model's instruction to want something.

## Privacy, deletion, portability

Raw media never enters new H2 Subject records, events, queue entries or archives. PERSONAL/SECRET raw bytes are not written to disk by H2. Semantic interpretations are MODEL_DERIVATION, never raw observation, Grant, user command or verified scene meaning. Screen text and synthetic transcripts remain cited content. Strict MEDIA validation rejects goal/code/authority-shaped proposals.

Disable/remove stops future reads and cancels source timers, while observation provenance remains. Explicit Memory forget invalidates technical/semantic descendants, World beliefs and concerns through existing dependencies. A deleted stable source cannot be replayed; later genuinely new captures retain distinct identities. Frontend projections avoid deleted support.

Host source profiles, resource refs/paths/handles and health are not portable Subject identity. B8 excludes config files and strips transient runtime.health including H2 operational state. Actual export/import preserves the same Subject/history, and the new host explicitly constructs new sources. Backup/lease takeover preserves original Core recovery rules; no capture or semantic authorization is automatically renewed.

## Resource and recovery qualification

Host minute ceilings bound capture count, conservative byte reservation, background share and semantic attempts. Existing CognitionSession retains original D6 model budget/cost/byte reservations. Unknown cost is not zero billing. One capture runs at a time on the original owner; real adapters must honor their request deadline. V1 yields at declared safe points; it makes no hard real-time cancellation guarantee inside an arbitrary host capture callback or codec subprocess.

Six **actual local SIGKILL** cases cover BEFORE_SOURCE_OPEN, AFTER_CAPTURE_BEFORE_INGEST, AFTER_TECHNICAL_INGEST, BEFORE_SEMANTIC_DISPATCH, AFTER_SEMANTIC_RESPONSE, BEFORE_CONCERN. New processes take over only after lease expiry. Captures/model calls do not repeat; accepted grounding and original WorldLoop jobs are idempotent. Source data deleted before replay stays deleted.

The 24-hour virtual run mixes screen/camera/microphone, WATCH, user pressure, source toggles and provider outages. The >=180-second wall run uses an actual monotonic clock, existing Runtime/Scheduler and only synthetic sensor bytes. FD/thread/RSS/queue/identity measurements are in soak.json. It is not a live screen/camera/mic qualification.

Reproduce:

```sh
.venv/bin/python -m pytest -q tests/h2_perception
.venv/bin/python -m tests.h2_perception.process_worker wall /tmp/h2-own-fixture --seconds 180 --output /tmp/h2-wall.json
.venv/bin/python -m pytest -q tests
```

## Verification and limits

Exact focused/full/group results and qualified source fingerprints are recorded in evidence. A preliminary full run failed because `/tmp/nana-bootstrap-build/compat-python-old` was absent. Only this temporary launcher was restored to actual `/usr/bin/python3` (Python3.13.5, actual SQLite3.46.1), and the original isolation test passed. No version spoof, test deletion, R045 source or production change. The failure and environment distinction remain recorded; this does not qualify a production Python/SQLite combination.

No Subject schema migration: version13,43 tables; new business tables0/dependencies0. H1-LIVE historical PARTIAL_PROVIDER_QUALIFICATION remains unchanged. E12 NOT_RUN. Actual OS capture, arbitrary private media/video decoder support, speaker-authenticated voice commands, live ASR, live providers, continuous production deployment, UI and Hands are not implemented/qualified by this delivery.
