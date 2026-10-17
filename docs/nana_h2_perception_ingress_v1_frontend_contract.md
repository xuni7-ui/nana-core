# B10 Perception Contract V1

Future Settings → Perception: Screen, Camera, Microphone, Files, Apps, Platform Media. This delivery provides typed application transitions, not a UI or device authority.

The host injects HostPerceptionResolver bindings, explicit host_allow policy, context policy and optional CapabilityRouter, then PerceptionSettingsService(coordinator, authority) into SubjectApplication (or Runtime.application). FrontendPolicy independently grants VIEW_PERCEPTION / CONFIGURE_PERCEPTION / REQUEST_CAPTURE. Commands run through the existing application owner; external adapters post metadata via Runtime.post(), not SQL. Primary User role is not sensor permission.

## Source profile configuration (host-local)

```json
{"source_profile_id":"screen.work","display_name":"Work screen","source_kind":"SCREEN","modality":"IMAGE","adapter_ref":"desktop.approved","resource_ref":"monitor.approved","scope":"world","entity_id":"observer","privacy_class":"PERSONAL","enabled":true,"capture_mode":"PERIODIC","base_interval_ms":30000,"min_interval_ms":5000,"max_interval_ms":3600000,"max_capture_bytes":1048576,"semantic_operations":["VISION"],"retention_policy":"MEMORY_ONLY_EPHEMERAL","priority_class":"BACKGROUND","revision":1}
```

adapter_ref/resource_ref are opaque existing host bindings. They are never arbitrary OS paths/executable names, and frontend view omits both. Source kind does not instantiate an adapter. Trusted descriptor privacy_floor cannot be lowered by this profile. Explicit host allow and Manager veto still apply.

## Read projections

`client.view('PERCEPTION_SETTINGS')` returns FrontendProjection.data_json:

```json
{"schema_version":1,"revision":5,"sources":[{"source_profile_id":"screen.work","display_name":"Work screen","source_kind":"SCREEN","modality":"IMAGE","scope":"world","entity_id":"observer","privacy_class":"PERSONAL","enabled":true,"capture_mode":"PERIODIC","base_interval_ms":30000,"min_interval_ms":5000,"max_interval_ms":3600000,"max_capture_bytes":1048576,"semantic_operations":["VISION"],"retention_policy":"MEMORY_ONLY_EPHEMERAL","priority_class":"BACKGROUND","revision":5,"resource_label":"screen source"}],"policy":{"max_captures_per_minute":30,"max_bytes_per_minute":16777216,"max_semantic_calls_per_minute":8,"background_percent":50,"pending_capacity":16,"debounce_us":2000000},"storage":"HOST_LOCAL_NOT_SUBJECT_MEMORY","capture_authority":false}
```

`PERCEPTION_STATUS` projects permitted sources only: source_profile_id, health (AVAILABLE/DEGRADED/UNAVAILABLE/DISABLED/UNKNOWN), last_capture_us, last_technical_observation reference, last_semantic_state, effective_interval_ms, sanitized last Manager block references, enabled count, pending count, coalesced/dropped counts. No pixels, audio, path, resource ref, handle or credential. Health is infrastructure, not emotion or permanent world absence. Config errors remain explicit errors, never an allow-all default. Historical Memory/WorldModel remains the original authority; this status is derived/rebuildable.

## Mutations

`client.perception_command(SourceCommand(...))` requires CONFIGURE_PERCEPTION.

```json
{"operation":"DISABLE_PERCEPTION_SOURCE","expected_revision":5,"target_id":"screen.work"}
```

Supported: UPSERT_PERCEPTION_SOURCE/profile; REMOVE_PERCEPTION_SOURCE, ENABLE_PERCEPTION_SOURCE, DISABLE_PERCEPTION_SOURCE/target_id; SET_CAPTURE_POLICY/policy. Exactly one matching payload. All use expected_revision. Successful result is the updated settings projection. Document revision increases once. Modified profile revision takes the new document revision, preventing old revision reuse after remove/recreate.

Two clients read5: A writes6; B's write at5 fails PERCEPTION_CONFIG_REVISION_CONFLICT. B must reread. Unknown fields/invalid intervals/modality/unknown binding fail closed. Configuration updates create no Memory/Goal/Emotion/Relationship/cycle. Enable is not permission; remove is not forget.

`client.request_capture(source_id='screen.work', request_id='ui.capture.1', expected_revision=6)` requires REQUEST_CAPTURE. Result:

```json
{"request_id":"ui.capture.1","state":"REQUESTED","config_revision":6}
```

This enqueues a bounded ordinary D observation opportunity. It does not immediately open a sensor, grant a capability, adopt a goal or send anything. The owner checks current source revision, scope/privacy/host policy, Manager veto, bounds and availability before bytes. An expired/denied request does not rewrite Subject intention. Only a truly new observation request can request a new capture; replay never retries UNKNOWN semantics.

## Event-driven ports

Trusted adapter keeps bounded raw media in volatile memory and posts `coordinator.notify_sample(source_id, opaque_sample_key, observed_at_us=...)`. Sample key is a short opaque token, not bytes/path. Returned existing Runtime ingress receipt is durable only after owner drains it. Owner pulls exact sample; source revision changes or restart loss yield explicit unavailable/stale/expired status. No standalone sensor loop or authority is created.

## Errors and boundaries

Typed errors include PERCEPTION_CONFIG_REVISION_CONFLICT, PROVIDER_CONFIG_INVALID (shared JSON primitive), SOURCE_UNAVAILABLE, SOURCE_DESCRIPTOR_MISMATCH, SOURCE_PRIVACY_FLOOR_DENIED, BLOCKED_BY_HOST, CAPTURE_MANAGER_BLOCKED, SOURCE_REVISION_STALE, PERCEPTION_PRIVACY_DENIED, CAPTURE_BUDGET_DENIED, SOURCE_MIN_INTERVAL, PERCEPTION_BACKPRESSURE and SOURCE_SAMPLE_EXPIRED. Per-operation semantics can be GROUNDED, UNKNOWN, FAILED/REJECTED, DENIED or deferred. The raw-byte lifetime is one bounded slice; a provider returning later or becoming available after bytes expire does not authorize reread or replay.

Frontend has no Store/operator/resolver/raw device handle. The Python service API is an application contract, not a sandbox against root/introspection. Config file/controller remain host-owned and outside B8 SubjectPackage. Real camera/mic/screen capture, user voice authentication, production streaming, device controls and Hands remain NOT_RUN/disabled.
