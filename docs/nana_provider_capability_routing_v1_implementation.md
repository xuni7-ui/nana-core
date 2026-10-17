# Provider Capability Routing V1

GLOBAL_STAGE = H. WORKSTREAM = PROVIDER_CAPABILITY_ROUTING_V1.
Scope: offline implementation / deterministic fixture and SYNTHETIC_LOOPBACK qualification only.
Base: `ba798b201ff2f7ba671a2cb9939d9692b59fd93f`.
Branch: `dev/nana-core-provider-capability-routing-v1-codex`.
Final commit is the commit containing this report; exact ancestry is available through Git (no self-referential commit hash).

## Implementation

`continuity/provider_config.py` owns a strict version-1 **host-local** JSON document, ProviderProfile, ModelProfile, CapabilityRoute, SecretResolver protocol, redacted credential handle, explicit controller and typed commands. This is application configuration, not a Subject Store. No environment/secret discovery exists. Configuration never creates Subject events.

`continuity/provider_routing.py` resolves existing operation identifiers into an immutable sanitized RouteSnapshot and runtime target. The factory reuses OpenAIJSONTransport/OpenAIMediaTransport for explicit OpenAI-compatible configuration, and Registry fixture ports for local operations. Application policy must explicitly allow remote execution and exact hosts; defaults deny. This work made zero external provider calls.

`continuity/providers.py` preserves the ephemeral Registry and legacy unique-model lookup. Explicit model profile IDs or provider-qualified keys distinguish identical remote model names. Ambiguous legacy names fail. MediaSession and EmbeddingCache remain the original implementations; routed sessions additionally enforce ceilings and route freshness, including retained session handles. Embedding route/revision/version changes invalidate the rebuildable index, not Memory.

`world_loop/cognition.py` continues to own reservation, context assembly, source checks, worker bounds, dispatch, strict proposal validation, recovery and UNKNOWN semantics. Optional route metadata is omitted from legacy request serialization, preserving legacy request hashes. A frozen routed request cannot be replayed through another target or stripped of its route. Route changes conservatively stale all prepared requests from the older configuration revision. Terminal UNKNOWN/FAILED remains terminal on restart. Journal adds sanitized routing observations only to routed calls. POSSIBLE_OR_ATTEMPTED deliberately does not claim the provider received an ambiguous request. Existing reply records retain allowlisted token usage, native IDs and raw HTTP digests.

`continuity/application.py` extends the existing SubjectApplication/FrontendSession with PROVIDER_SETTINGS and typed provider_command. Existing PROVIDERS view remains. The application supplies ProviderSettingsService and controller; the client receives neither configuration service nor resolver/Store/operator handles.

## Persistence and authority

No Subject migration: schema 13, 43 business tables, zero added tables/dependencies. Local config schema is independently versioned at 1. Private directory/file checks, O_NOFOLLOW, bounded strict JSON parsing, flock, document revision CAS, temp-file fsync, replace and directory fsync prevent partial defaults and silent overwrites. Corruption fails closed. A killed pre-replace writer can leave an ignored private temp file; it is never an alternate authoritative configuration. Two actual SIGKILL cases verify old/new committed revisions on reopen.

Provider/model removal rejects live dependencies. Update route first, remove model, then provider. Removing a runtime profile does not remove historical Cognition/Memory/WorldModel/Experience provenance.

Secrets only traverse explicit resolver → memory-only transport → Authorization. The resolver is trusted application code, not a model-provided plugin. ResolvedSecret repr/str are redacted and serialization denied. It is cleared after construction; the original transport necessarily holds a memory-only credential for requests. Settings views omit even secret_ref and only expose AVAILABLE/MISSING/UNCONFIGURED. Python introspection/root compromise is outside the client contract; it is not a Python object sandbox.

## Selection and effective policy

Resolver input is operation, modalities, privacy and bounded limits, never relationship/personality. Primary → bounded ordered fallback is considered only during resolve, before a session is dispatched. Disabled/missing/unsupported/missing-secret candidates produce typed dispatched=false reasons. Exact provider+model mode never falls back. No API wraps a dispatched call in a fallback retry. UNKNOWN, timeout and malformed reply never invoke another target; recovery never retries a terminal request.

Effective privacy is ContextPolicy ∩ provider ∩ route, with REMOTE SECRET always removed. Limits are minima of request/provider/route/trusted runtime policy/model limits. Existing CognitionSession reserves against the original Runtime resource budget, so route ceilings cannot create extra global quota. Cost ceilings are estimates/limits, not billing truth; actual cost remains unknown when not supplied. Media synchronous fixture timeout detection is retrospective; production remote media cognition uses existing bounded workers, not this fixture timeout as a remote cancellation guarantee.

Remote endpoint configuration requires HTTPS, safe canonical path/hostname, no userinfo/query/fragment/credential URL, literal IP/local host rejection, and application-owned exact host allowlist. Endpoint construction appends `/chat/completions`; NoRedirect and bounded existing transports remain. Full DNS-rebinding/network egress enforcement belongs to trusted host deployment policy; V1 does not claim it pins DNS addresses. Reserved future protocol names are configuration contracts and fail unavailable until explicitly implemented.

## Reproducible system scenarios

Run `.venv/bin/python -m pytest -q tests/provider_routing`.

- A: `test_multi_provider_life_restart_disable_remove_no_history_delete`: same Subject uses text A, vision B, embed C, disable B then pre-dispatch D, reopen config, enforce dependency order, remove D, preserve history.
- B: `test_after_dispatch_never_fallback_restart_no_retry`: UNKNOWN/timeout/malformed after dispatch, fallback calls zero, restart does not resend.
- C: `test_subjectpackage_excludes_host_config_and_same_subject_uses_new_host`: actual B8 transfer preserves identity/history, excludes endpoint/secret_ref/config, new host explicitly configures a new provider.
- D: `test_frontend_settings_cas_no_subject_mutation_or_authority`: settings mutations and projections through B10, stale revision rejected, restricted frontend commands rejected, no credential or authority exposure.
- Native loopback: `test_original_openai_transport_native_loopback_config_to_h1`: Text/Image/Video frames go through original OpenAI HTTP transports and H1 semantic contracts. Interpretation remains MODEL_DERIVATION; no Action, Grant or Subject decision is created by routing.
- All nine operations use existing fixture ports. Non-chat audio/ASR/TTS/generation are offline routing contracts, not vendor qualification.

See evidence JSON and test_summary.txt for exact executed results and file fingerprints.

## Boundaries and limitations

One Subject, one Store, one SubjectLoop; D WHEN / C WHAT-WHY unchanged. Provider settings do not change identity, Primary User, Manager, Grant, goals or feelings. Model output cannot mutate settings. No UI, discovery, real provider, H2, capture, Hands, social send, installation or production migration. Remote SECRET remains denied. Health is infrastructure, not personality.

H1 historical TianToken/qwen qualification remains PARTIAL_PROVIDER_QUALIFICATION; no historical evidence was rewritten or upgraded. E12 remains NOT_RUN. A future real capability vendor requires its own explicit qualification, credential resolver and application egress policy. Settings UI can consume this contract without becoming a second authority.
