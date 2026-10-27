# V3 integration handoff

Implementation source: `fde9074c30c81854fc1a8786433014079e28b94d`.
Base: `a07e906fa59798c6bfc7a00c2281a924f979c55d`.
Branch: `dev/nana-space-v3-cotex`. This is a parallel client extension; the original
First-Life deployment branch and original qualified image remain unchanged.

## Deliverables

- `artifacts/nana-space-v3/nana-space-3.0.0-debug.apk`
  - 4,790,932 bytes / 4.57 MiB.
  - SHA256 `02d85e568195d478de2b515ac45bf6278b3a399c262bf80841091ff30d8d0160`.
  - `life.nana.space.dev`, versionCode300, minSDK23/targetSDK35.
  - Original V2 debug certificate SHA256
    `b2fec5a02e6f32e69fb8ef8bce44391a6a4ba5ab8ce6dc7284cb57663016ec41`.
  - Signature v1/v2 PASS, exact prior certificate match. Intended in-place debug
    upgrade, not production signing. Actual user-phone install/upgrade NOT_RUN;
    do not uninstall/clear app data to disguise a failed upgrade.
- `artifacts/nana-space-v3/nana-space-3.0.0-web.zip`
  - 608,679 bytes, SHA256
    `60a15bb9e27e5288991666ce3e31adb037c1bc594ccc59998d6e287453917ca8`.
  - 41 actual dist files, identical to every APK packaged Web asset.
  - Two deterministic ZIP builds byte-identical; manifest and CRC verified.
- `apps/nana-space/docs/previews/v3/`: 32 desktop/mobile screenshots, explicitly
  labelled synthetic source records. The actual owned-Core screenshots are
  separately under evidence/actual-core-screens, not substituted for historical V2.
- Feature statuses: [STATUS](STATUS.md). Actual mapping: [IMPLEMENTATION](IMPLEMENTATION.md).
  Missing server edges: [BACKEND_INTEGRATION](BACKEND_INTEGRATION.md).

## Review / integration steps

1. Review the exact source commit. The code changes are limited to
   `apps/nana-space`; PROJECT_BRAIN/doc changes account for this branch's scope.
   Do not overwrite an advancing cloud branch's current-state block with ours.
2. `npm ci && npm test && npm run build` in apps/nana-space. `build` is live by
   default; the preserved old demonstration has a separate explicit build command.
3. Serve Web assets through the existing authenticated same-origin v2 BFF. Do not
   place the private control API on an unapproved public listener. Frontend aliases
   map back to the existing finite API/native page enum.
4. Replacing a cloud Web release/image requires the original deployment workflow
   and new artifact verification. This branch never rebuilt the qualified image or
   touched `/srv`, original services or formal identity. Do not claim the old
   image already contains V3.
5. Missing writes should bind the original Core service with explicit role,
   schema/CAS, policy intersection and dispatch receipts. Do not make React
   mutate ProviderRegistry/Memory/Store directly. No Key input in React is needed.
6. Phone user later verifies in-place upgrade, preserved pairing, private HTTPS,
   keyboard/back, permissions and foreground notification behavior. Background
   push and a live paid model are separate qualifications.

## Actual verification

- TypeScript + live Vite build PASS.
- Frontend Vitest **41 passed /0failed**,2.38s.
- V3 synthetic HTTP browser **36 passed /0failed /0skipped**,46.797s,
  desktop1440 +360/390/412,120%font/history/UNKNOWN/late-write/privacy/logout.
- Actual original owned Core browser **3 passed /0failed**,18.1s,
  desktop/390/320, same-subject ten pages, real offline original C response,
  secure cookie, refresh and logout. Not a paid model/human dialogue test.
- Existing related v2 Python **39 passed /0failed**,14.81s: real auth/pair/revoke,
  role/Origin/CSRF/idempotency/source/infrastructure boundaries. Initial isolated
  auth+HTTP subset11pass7.90s is part of the related scope, not additive credit.
- Native unit **1 passed /0failure /0error /0skip**; Android build/lint PASS,
  **0 errors /15 warnings** retained. Last incremental build30s; previous clean
  success1m5s. Original JAR metadata warnings remain; APKv2 verification succeeds.
- No fresh full Core suite was run; original Core business bytes/API/DTOs/plugin
  did not change. Historical1581/0/12 is not reused as a new test result.

Local Chromium cold first-contentful-paint was332ms at390px and272ms at1440px;
~794KB network transfer for entry+assets,358 DOM nodes,0 persistent backdrop-blurs.
One51ms startup long task at390px,none desktop. This is a single local test sample,
not a phone/network performance guarantee or measured speedup over V2.
No heavy particle engine, perpetual model loop, extra daemon or new runtime dep.

## Open gates stay open

Provider configuration writes/discovery/tests/secrets, returned live model/usage,
notes/corrections/imports, rich relationship/topic indices and actual B1 offsite
status need server support. UI drafts are visibly unsent and discarded on exit.
Physical install/upgrade, live cloud HTTPS and human naturalness remain NOT_RUN.
C genesis prepare-only and D/E deferred; no production/private/social/model spend.
bwrap stays BLOCKED; original autonomous goals/interests/learning and authorized
ports are not globally disabled. First-Life NOT_READY / Beta NO unchanged.
