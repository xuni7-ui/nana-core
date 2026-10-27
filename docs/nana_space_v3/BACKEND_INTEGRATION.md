# Nana Space V3 · minimal Core/BFF integration

[源码核查] Frontend enhancement based on First-Life branch `a07e906`.
This document describes existing interfaces and **proposed, unimplemented**
extensions. It grants no cloud activation, Provider budget, private import,
genesis, social delivery or skill execution permission. Master/fixed 63 unchanged.

## Existing V2 contract retained

V3 calls `V2Client` and the same fixed native `NanaHost` operation map. No arbitrary
URL/native HTTP passthrough, new Subject, Store, authority object or model brain.

| UI | Existing source | Actual available behavior |
|---|---|---|
| Space / room | `GET views/home` | `items` for activities, concerns, needs, interests, relationship, goals; metadata, not invented life stories |
| Chat | `POST messages`, `GET receipts/{id}` | original SurfaceSession → C; PROJECT/PUBLIC text ≤2048; wording is a reply candidate, not external delivery |
| Memory | `GET views/memories` | at most 32 currently active, scoped records; source id and uncertainty retained |
| Withdrawal | `POST commands`, operation `WITHDRAW` | Manager role; scoped original memory withdrawal, source closure and privacy watermark |
| Goals / journal / world / growth | corresponding `views/{page}` | original Inspector records; no direct goal adoption, emotion rewrite or skill install |
| Model center | `GET views/settings` → `provider_settings` | original `ProviderSettingsService.projection()`; read-only through V2 BFF |
| Devices | `GET devices`, `POST devices/offers`, `DELETE devices/{id}` | explicit Host Admin, role-subset, one-time name-bound pairing and revocation |
| Runtime | `GET bootstrap`, `GET views/runtime` | original bound Subject/lineage, host readiness, resources, owner and UNKNOWN metadata |
| Runtime controls | `POST commands` / `POST host/confirmations` + `POST host/operations` | Manager controls and separate Host Admin lifecycle; operation/revision/release-bound confirmation |
| Backup | Host operation `BACKUP` | original consistent safe point; **local quarantined review copy only**, not B1 offsite DR |
| Notifications | native permission + foreground notification; `GET notifications` | no background push provider; permission does not prove delivery |

All views use `nana-space-live/v2` envelopes: subject/lineage/realm, owner epoch,
run/session generation, revision, timestamp, coverage, privacy scope, source refs,
capabilities and `execution_authority=false`. `NO_DATA`, `STALE`, `UNAVAILABLE`
and `UNKNOWN` must remain distinct. Reader access and current binding are checked
server-side. A stopped Core is not a new Subject.

Memory records currently contain only `memory_id`, `memory_type`,
`epistemic_kind`, `assessment`, `privacy_class`, `source_evidence_id`,
`created_at_us`, `text`. Missing topics, relationship labels or numeric confidence
must not be synthesized. Generic Inspector records include `section`,
`reference`, `state`, `category`, `source_memory_ids`; they are not full prose
experiences. Host runtime metrics are observations, not personality or feelings.

Provider profiles exclude `secret_ref` from the projection and expose
`secret_state`. The current `life/provider.py::provider_status` constructs its
factory without a resolver; this state is not independent live credential or
model qualification. Provider presets are documentation/UI affordances, not
evidence that Anthropic/Gemini/local protocols already work.

## Client invariants for every extension

- Web: same origin, Secure/HttpOnly/SameSite=Strict session cookie; memory-only
  CSRF, strict Origin/Host, no CORS and `no-store`. Never put login, pairing,
  Provider secrets or long-lived tokens in storage, URLs, logs or UI exports.
- Native: preserve `life.nana.space` + debug `.dev`, Keystore-encrypted refresh
  binding, memory-only access; standard Android TLS/host checks, no redirect or
  custom trust bypass. JS receives no refresh/access secret.
- Writes retain client request/idempotency ids, expected revision, run generation
  and owner epoch. UNKNOWN is verify-only; no automatic resend, route fallback,
  notification replay or request resurrection after restart.
- Discard late responses after logout/revocation, wrong identity/realm or route
  change. Clear rendered bodies, previews and transient drafts when privacy
  watermark/run changes or connection scope becomes invalid. Refreshing metadata
  does not authorize caching withdrawn text.
- New UI pages map to existing finite view names. Do not extend native paths by
  accepting arbitrary endpoints. New write support requires typed DTO/schema,
  native allowlist and server authorization tests together.
- Existing receipt ledger has a 256-entry staging limit; no silent eviction or
  claim that V3 alone qualifies unlimited daily production use.

## Proposed minimal extensions — not endpoints available in this release

The server must advertise each capability before enabling its UI action. Keep
existing V2 fields stable and add explicit versioned DTOs/allowlist entries;
do not send extra fields through current strict `MessageRequest`.

### Provider configuration and model routing

Add a typed `providers.command` application operation for an explicitly authorized
host configuration controller. Reader or Primary User relationship alone is not
configuration authority. Reuse `ProviderSettingsService.command`,
`ProviderCommand`, `ProviderConfigService` atomic revision/CAS and existing
`RuntimeProviderFactory`/Router. Request needs both transport/write revision and
`expected_configuration_revision`; response returns the sanitized new projection
and its actual configuration revision, not just a toast.

Supported commands already exist internally: UPSERT_PROVIDER, REMOVE_PROVIDER,
UPSERT_MODEL, REMOVE_MODEL, SET_CAPABILITY_ROUTE, REMOVE_CAPABILITY_ROUTE,
ENABLE_PROVIDER, DISABLE_PROVIDER. Preserve dependency errors, duplicate checks,
REMOTE SECRET denial, HTTPS endpoint validation, runtime/context/privacy/budget
intersection and no fallback after dispatch/UNKNOWN. Deleting a profile only
changes future routing; historical provenance survives.

Core operation IDs remain COGNITION, EMBED, VISION, IMAGE_GENERATE, STT, TTS,
AUDIO_UNDERSTAND, AUDIO_GENERATE, VIDEO_UNDERSTAND. TEXT/REASONING labels map to
COGNITION. RERANK/realtime MULTIMODAL are extension placeholders until independently
implemented, not new accepted Core enums. Embedding route/version/dimension changes
must yield rebuild-required and leave Memory truth intact.

Secrets are bound by a trusted host/explicit SecretResolver service outside this
React form. A future binding operation returns only opaque reference and
AVAILABLE/MISSING/UNCONFIGURED; plaintext never returns to JS. Do not invent a
React password field as a substitute for a safe host binding.

Discovery and paid model tests must be separate explicit operations with endpoint
allowlist, model/capability, request reservation, cost/call ceiling, timeout and
qualification identity. No auto-discovery registration or call on page load. An
exact-model chat selector additionally needs an authorized typed model selection
contract and returned route snapshot. Until then chat uses current automatic
route; changing a local selector must not imply the server actually switched.

### Memory notes, correction and imports

Add separate sourced `memory.note`, `memory.correction` and bounded
`memory.import.preview/commit` application transitions through original memory,
evidence, privacy and lineage contracts. Notes are USER_PROVIDED claims, not Nana
personal experience. Correction creates traceable support/counterevidence and
does not erase the original event. Use explicit privacy/scope and expected
revision; verify source ownership and current lifecycle before dispatch.

Import preview should return hash-only dedup/conflicts, known format/version,
record counts and required authorization. Commit must bind the exact preview
digest, declared classes/retention and separately approved private import. No
frontend raw DB upload, current Store download or automatic Iris migration.
Until this exists V3 drafts and selected-file previews are memory-only and clearly
unsubmitted. A local preview is not an import or migration progress receipt.

### B1 backup status

Expose an authenticated read-only `backup.status` projection from existing Core
safe-point receipts and host B1 operator receipts. Minimum fields: snapshot id,
creation time, source lineage/release, local consistency state, encryption state,
PC delivery receipt time/hash, restore-check result/time, blocking reason and
independently qualified scope. Do not expose host paths, keys, private bodies or
backup download credentials. An unbound PC is `LOCAL_ONLY_NOT_DR` or
`PC_NOT_BOUND`; lack of telemetry is `STATUS_NOT_EXPOSED`.

Scheduling/request APIs, if later added, call original consistent backup first,
then approved encryption/send workflow. PC offline or transfer UNKNOWN cannot
become completed. Restore stays a distinct high-privilege offline workflow with
privacy reconciliation, lineage validation, old-owner fencing and approval.
The browser never zips a live database or boots an imported Subject.

### Multimodal and future surfaces

Current `messages` is text only. Add bounded attachment intents with media
type/size/digest/privacy/source, explicit supported capability, cost reservation
and existing H1 strict MODEL_DERIVATION path. No FileReader/data URL payload added
to current messages, no camera/microphone capture on entry, no system speech
service invoked as a hidden external provider. Permission and capability are
separate. Live2D/avatar skins affect rendering, not Core emotional truth.

For human-facing summaries/small-room prose, extend original Inspector with
source-bound readable labels/time and explicit certainty; keep current refs.
Do not generate a second frontend life/relationship database to fill sparse data.

## Verification entry points

From `apps/nana-space`: `npm run build`, `npm test`, V3 browser suite plus original
`playwright.v2.config.ts` against a newly isolated development Core/BFF only.
Original test expects Subject ID/session login, ten live pages, actual original C
topic boundary, secure cookie, reload-cleared turns and logout. Keep
`tests/v2-client.test.ts` late-response/identity/privacy/authority guards. Test
new routes at 360/390/412 and desktop, keyboard/back/weak network/UNKNOWN without
private or paid content. Screenshots of fixture data must be labeled synthetic;
development Core screenshots are not proof of real cloud connection.

Available local Android toolchain at audit time: JDK21
`/workspace/nana-android-toolchain/jdk/jdk-21.0.13+9`, Gradle8.11.1 under
`gradle-dist`, Android SDK35 under `sdk`, existing `gradle-cache` and
checksum-pinned `android/gradle/verification-metadata.xml`. Reuse offline caches
and previous debug signing identity through standard Gradle selection without
printing or reading key material. Bump versionCode above100 while preserving
applicationId; verify APK signer fingerprint matches prior debug APK. Browser
tests do not replace phone installation/Keystore/notification qualification.

This review changed documentation only. No production/cloud service, Docker
image, API implementation, credential or authoritative Subject was modified.
