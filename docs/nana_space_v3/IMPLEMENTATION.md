# Nana Space V3 · Companion Experience & Control Center

GLOBAL_STAGE H / Advanced Growth, Platform/Surface + Shared Life + Governance
axes. Frontend-only continuation of First-Life Android V2. Developer role: CotEX.
Base a07e906fa59798c6bfc7a00c2281a924f979c55d was fetched and matched both local
and remote First-Life heads; isolated worktree/branch `dev/nana-space-v3-cotex`.
The deployment worktree, original qualified Docker image, canonical plan,
Master/Matrix/fixed 63 criteria and original untracked bundle are untouched.

## What actually changed

- V3 live surface: responsive companion home and little room, moonlight/morning
  mist/system themes, bottom navigation, accessible drawer, bounded sourced cards,
  local appearance controls and search. Existing character artwork is retained.
  Static room artwork is labelled display-only, never a real emotion or experience.
- Chat: finite in-memory turns, Markdown/code, safe links, no remote image loading,
  request/receipt states, single request, receipt-only UNKNOWN verification,
  composition-safe keyboard shortcut, scroll anchoring, visual-viewport keyboard
  sizing. Local attachment previews do not upload; voice does not open a microphone.
- Provider center: typed allowlist adaptation of original host-local config,
  actual configured provider/model/route cards, 11 clearly unqualified brand
  presets, 9 existing operations + RERANK/realtime multimodal expansion slots,
  provider/model/alias and ordered primary/fallback **memory-only drafts**.
  Secret state is projected; there is no Key input or secret resolution in React.
- Memory center: current scoped source-aware timeline, text/date/type/source
  filtering, provenance and assessment details. Current v2 lacks topic/relation
  indices; their controls say so. Notes/corrections/imports are only user-provided
  proposals, not Nana's lived events. Preview ≤256KiB/100 entries, duplicate
  detection limited to visible records and file contents. Existing Manager
  WITHDRAW is the only memory write actually wired.
- Real v2 role-gated device listing/pairing/revocation, Manager commands and host
  confirmations remain. Backup requests use the original Core safe point; B1
  cadence/PC delivery/restore are NOT_EXPOSED, never inferred from a local backup.
- Settings separate local appearance, unsent communication-preference draft and
  authoritative Core identity/motivation/relationship. No identity/persona override.
- Native: application ID and Keystore plugin unchanged; versionCode100→300,
  2.0.0→3.0.0. Android back handles the local drawer, WebView route history, then
  exits; this exposes no new native capability. Physical qualification is separate.

## Boundary fixes discovered in this UI work

The v2 JS client and finite native network operation map remain byte-for-byte
unchanged. UI orchestration now guards request incarnation, route version and
privacy/body generation. Slow old-page reads cannot populate a new page;
post-write refresh uses the actual current destination. Logout clears memory
immediately and prevents later host dispatch after an outstanding confirmation.
Lost/unauthorized requests clear bodies and offer codes. UNKNOWN keeps only its
original receipt ID; there is no retry or fallback. A late high-role pairing offer
cannot reappear beneath a changed low-role draft or after navigation/logout.
Memory adaptation also refuses any row outside v2's PUBLIC/PROJECT scope.

## Module / original contract mapping

| New UI | Actual original contract | Scope |
|---|---|---|
| Home / room | GET views/home, Inspector items | Sourced metadata; no invented mood/story |
| Chat | V2Client.message → original SurfaceSession/C | PROJECT input, actual receipt/provider_state |
| Memories | GET views/memories, MemoryService; command WITHDRAW | Manager/Privacy/source closure unchanged |
| Model center | views/settings.provider_settings → ProviderSettingsService | Read current config; edits are unsent drafts |
| Life / goals / world / growth | journal/goals/world/growth finite v2 views | Original activities/World/lessons/skills metadata |
| Inbox | journal view | Explicit source-record fallback, no fake inbox or push |
| Devices | views/devices + original devices/offers/revoke | Auth-service permission, not relationship authority |
| Runtime / backup | views/runtime + host confirmation/operation | Single configured owner/home, safe point backup |
| Settings | local preferences + Manager commands | Appearance is local; desire is not rewritten |

`sourcePage()` maps UI aliases to the original finite v2 pages. No new business
schema, API/native operation, ProviderRegistry, SubjectLoop, Store or Runtime is
introduced. Frontend UI routes are not Core execution permissions.

## Running and building

Node24 was used; package-lock pins dependencies. Prettier3.6.2/MIT is a new
**development-only** dependency; no new runtime dependency. `npm ci`, `npm test`,
`npm run build`, `npm run preview` build/serve the live V3 connection screen by
 default. Offline browsing is explicitly labelled and has no life data. Historical
V1 demo remains only via `dev:demo` / `build:demo`; it is not shipped as the default.

`npm run android:debug` builds the same live assets with Capacitor. Use JDK21,
SDK35, Gradle8.11.1. No server credential/configuration is required or embedded.
The existing debug certificate is reused; production signing remains operator-owned.
Install as an update, not by changing the package or clearing app data. Android
package installer/physical permission/upgrade checks remain to be observed by a
real phone user. There is no connected physical phone in this executor.

For the original owned Core browser qualification use the existing
`tools/nana_first_life_android_v2/dev_serve.py` with a fresh DEV-only directory,
qualified Python/SQLite and loopback TLS. The original `test:v2` tests a real
original Core subprocess. Its self-signed test certificate is accepted only by
the browser harness; Android/production TLS is never weakened.

`test:v3` is explicitly SYNTHETIC_HTTP_FIXTURE: broad UI and failure scenarios,
not a real provider/cloud or human naturalness qualification. Screenshots under
apps/nana-space/docs/previews/v3 contain labelled synthetic records.

## Integration and remaining work

See [STATUS](STATUS.md) and [BACKEND_INTEGRATION](BACKEND_INTEGRATION.md).
Deploying the new Web bundle or image is a later approved integration, not part
of this branch. Existing original image0d842676 has not been rebuilt or altered.
Cloud A/B, C prepare-only, D/E deferred and B1 actual PC receipts stay on the
original deployment route. bwrap remains BLOCKED; no direct-exec fallback or
broad autonomy restriction. First-Life NOT_READY, Beta NO, human NOT_RUN remain.
