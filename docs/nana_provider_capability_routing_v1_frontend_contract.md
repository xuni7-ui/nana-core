# B10 Provider Settings Contract V1

No UI implementation. Future Settings → AI Providers contains Providers, Models, Capability Routing, Budgets, Privacy. Provider cards show name/base URL/protocol/secret status/enabled; model cards show provider/remote ID/operations/modalities/limits; each operation has Primary and ordered Fallback(s).

Application constructs `ProviderConfigurationAuthority`, `ProviderConfigService`, explicit `SecretResolver`, `RuntimeProviderFactory`, `ProviderSettingsService`, then supplies provider_settings to the existing SubjectApplication. Host config path is outside the Subject data/package. FrontendSession never receives these objects. Frontend policy independently grants VIEW_PROVIDER_SETTINGS and CONFIGURE_PROVIDERS; Primary User role is not configuration authority.

## ProviderProfile JSON

```json
{"provider_profile_id":"relay.example","display_name":"Example relay","protocol":"OPENAI_COMPATIBLE_CHAT","base_url":"https://api.example.com/v1","locality":"REMOTE","secret_ref":"relay.default","enabled":true,"permitted_privacy":["PUBLIC"],"default_timeout_ms":3000,"default_cost_ceiling":1000,"tags":[],"revision":1}
```

No credential value is accepted. Reserved protocols are not installed adapters. LOCAL takes no base URL or secret reference and uses application-registered ports. SYNTHETIC_LOOPBACK is explicit test-only policy, never an implicit HTTP exception for REMOTE.

## ModelProfile JSON

```json
{"model_profile_id":"model.text","provider_profile_id":"relay.example","remote_model_id":"example-text","model_version":"v1","operations":["COGNITION"],"input_modalities":["TEXT"],"output_modalities":["TEXT"],"context_limit":16384,"output_limit":2048,"tool_proposals":false,"latency_class":"UNKNOWN","cost_class":"UNKNOWN","enabled":true,"tags":[],"revision":1}
```

Same remote_model_id at another provider is legal; model_profile_id is unique. Supported operations reuse COGNITION, EMBED, VISION, IMAGE_GENERATE, STT, TTS, AUDIO_UNDERSTAND, AUDIO_GENERATE, VIDEO_UNDERSTAND.

## CapabilityRoute JSON

```json
{"operation":"COGNITION","primary_model_profile_id":"model.text","fallback_model_profile_ids":[],"enabled":true,"timeout_ceiling_ms":3000,"cost_ceiling":1000,"context_ceiling":16384,"output_ceiling":2048,"permitted_privacy":["PUBLIC"],"revision":1}
```

Route limits add ceilings; they never increase host runtime budgets or ContextPolicy. REMOTE SECRET is denied even if a route requests it. No fallback after any dispatch, UNKNOWN or invalid response. Exact qualification mode specifies both provider_profile_id and model_profile_id and has no fallback.

## Projection and mutations

`client.view('PROVIDER_SETTINGS')` returns existing FrontendProjection, whose data_json contains:

```json
{"schema_version":1,"revision":3,"providers":[{"provider_profile_id":"relay.example","display_name":"Example relay","protocol":"OPENAI_COMPATIBLE_CHAT","base_url":"https://api.example.com/v1","locality":"REMOTE","enabled":true,"permitted_privacy":["PUBLIC"],"default_timeout_ms":3000,"default_cost_ceiling":1000,"tags":[],"revision":1,"secret_state":"MISSING"}],"models":[],"routes":[],"storage_class":"HOST_LOCAL_NOT_SUBJECT_MEMORY","execution_authority":false}
```

secret_state is AVAILABLE, MISSING or UNCONFIGURED, never a credential or secret_ref. Models/routes use the DTOs above. Projections are not credentials/Grants and cannot dispatch actions.

`client.provider_command(ProviderCommand(...))` accepts a typed command and returns the updated projection. Command JSON shape example:

```json
{"operation":"SET_CAPABILITY_ROUTE","expected_revision":3,"route":{"operation":"COGNITION","primary_model_profile_id":"model.text","fallback_model_profile_ids":[]}}
```

Defaults are supplied by typed parsing. UPSERT_PROVIDER/provider, UPSERT_MODEL/model, SET_CAPABILITY_ROUTE/route each take one matching payload. REMOVE_PROVIDER, REMOVE_MODEL, REMOVE_CAPABILITY_ROUTE, ENABLE_PROVIDER, DISABLE_PROVIDER take target_id. All require expected_revision. Configuration controls profile/route revision increments; document revision advances exactly once.

If two clients read revision 3, A writes revision 4, B's write at 3 fails PROVIDER_CONFIG_REVISION_CONFLICT; B must reread, never silently overwrite. Caller cannot replace operator, resolver, Runtime policy, Grant, Manager or privacy authority through these DTOs. Unknown critical fields reject.

## Errors

Fixed CoreError codes distinguish PROVIDER_CONFIG_INVALID/UNAVAILABLE, PROVIDER_CONFIG_REVISION_CONFLICT, MODEL_PROFILE_IN_USE, PROVIDER_PROFILE_IN_USE, PROFILE_DISABLED, SECRET_UNAVAILABLE, OPERATION_UNSUPPORTED, MODALITY_UNSUPPORTED, PRIVACY_DENIED, BUDGET_DENIED, PRE_DISPATCH_UNAVAILABLE and ROUTE_CHANGED_BEFORE_DISPATCH. Existing CognitionSession preserves UNKNOWN versus FAILED with structured error_code; no fallback policy interprets either as permission to retry.

Delete order: reroute/remove route → remove referenced model → remove provider. Histories retain sanitized past provenance. Route updates only affect future calls, and conservatively stale prepared calls tied to the previous configuration revision. Configuration transfer is separate from B8; importing a Subject does not restore provider configuration or secrets.
