# Real AstrBot Shadow Binding — Codex development track

Base: c3ada9b09faa8a2683f98d5c8bafec24779cfd71, fetched from the shared branch on 2026-10-11 UTC. Codex writes only dev/nana-core-v1-astrbot-shadow-bind-codex. Baseline full regression: 318 passed / 0 failed / 1 skipped (E12 NOT_RUN).

## C-M0 source audit and smallest gap

Reuse approved Core ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513 unchanged: Store.ingest/projection/event artifacts; integration.host_observation.AstrBotObservationAdapter; ShadowBridge; InitiativeHostGate; persistent cloud.shadow_runtime marker; ActionKernel rejection; migration Iris schema definitions. Existing tools/nana_host_shadow/observer.py is explicitly adapter-local and runtime.py reports UNVERIFIED. No existing code claims real dispatcher verification.

The HostEvent contract permits content/attachment/private IDs for separately authorized imports; it is too broad for this task's entrance. Add a support-only sanitizer and restricted glue, never pass arbitrary host objects to HostEvent. Add proof/dedup/lifecycle tooling; no new Core/table/identity system. tools/nana_host_shadow/metadata.py already offers frozen read-only schema inspection; add an exact query policy and locked schema comparison rather than a migration engine.

No real hook audit/symbol evidence is present at base in the shared branch. AstrBot-specific registration remains BLOCKED_API_EVIDENCE; an API-neutral registration contract can be tested independently. Incoming user reconnaissance is a design input, not locally captured host evidence. User reports FIRST_REAL_HOST_ENGINEERING_SHADOW=PASS; repository at base has not yet recorded that host receipt. FIRST_REAL_ASTRBOT_SHADOW and host_binding remain UNVERIFIED. Do not overwrite Nana's现场 records.

All new development fixtures are synthetic, no external delivery. Real host login/install/reload/JWT/private data access are forbidden on this track. Original project license remains pending; no third-party execution source copied.
