# Living Release V4 — current integration gaps

Advanced Growth / GLOBAL_STAGE H. Frozen Master/63 criteria unchanged.
Base 77a09e2; V3/Real Living/Execution Context are ancestors, not rebuilt.

| Path | Observed gap | Implementation direction | Qualification |
|---|---|---|---|
| life/provider.py; live_api/bridge.py | Settings use a resolver-free projection, while readiness collapses missing route/credential/budget into generic provider state | Original runtime route/policy/budget metadata without model dispatch; preserve explicit resolver | Actual local BFF/Core, no paid calls |
| live_api/bridge.py send | Pre-dispatch failures may be recorded as UNKNOWN even when Core reports a definite rejection | Preserve original receipt state; distinguish observation dispatch from model dispatch | Missing route, privacy, budget; timeout no replay |
| live_api/__main__.py; Android native | Explicit FD secret binding exists; phone cannot configure a safe server binding | Reuse original resolver and fixed native interface; no JS/provider key storage | Synthetic credentials and revoked/role negative paths only |
| src/bili_agent/bili_video_read.py | Legacy reader imports a host-secret path and has its own model path; cannot load directly into ordinary Core | Separate explicit platform transport from original Memory/World/C opportunities; never import legacy credential loader | Offline transport integration first, actual account not authorized |
| deployment tools | Separate receive/stage/propose commands; CLI assumed; existing stage rejects repeat instead of recognizing same content | One operator-only entry, Unix Docker API fallback, exact integrity diagnostics, idempotent slot preparation | Actual independent Docker, no production switch |
| Android/Web | V3 is integrated, 302 pairing fix exists; media/key/role/deployment gaps remain | Preserve signed identity/Keystore and API v2 compatibility, expose real readiness | Build/signature/browser; real phone not accessed |

Host reports Subject 8acff4fb-2532-4a97-a4b7-e59e2ae2f797 and a live supervisor.
No remote binding is configured here; this is reported fact, not independent verification.
No real model/social/private-history/production operations are authorized by this document.
