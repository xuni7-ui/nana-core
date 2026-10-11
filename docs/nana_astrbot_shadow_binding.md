# Real AstrBot Shadow Binding — Codex development track

Base: c3ada9b09faa8a2683f98d5c8bafec24779cfd71, fetched from the shared branch on 2026-10-11 UTC. Codex writes only dev/nana-core-v1-astrbot-shadow-bind-codex. Baseline full regression: 318 passed / 0 failed / 1 skipped (E12 NOT_RUN).

## C-M0 source audit and smallest gap

Reuse approved Core ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513 unchanged: Store.ingest/projection/event artifacts; integration.host_observation.AstrBotObservationAdapter; ShadowBridge; InitiativeHostGate; persistent cloud.shadow_runtime marker; ActionKernel rejection; migration Iris schema definitions. Existing tools/nana_host_shadow/observer.py is explicitly adapter-local and runtime.py reports UNVERIFIED. No existing code claims real dispatcher verification.

The HostEvent contract permits content/attachment/private IDs for separately authorized imports; it is too broad for this task's entrance. Add a support-only sanitizer and restricted glue, never pass arbitrary host objects to HostEvent. Add proof/dedup/lifecycle tooling; no new Core/table/identity system. tools/nana_host_shadow/metadata.py already offers frozen read-only schema inspection; add an exact query policy and locked schema comparison rather than a migration engine.

No real hook audit/symbol evidence is present at base in the shared branch. AstrBot-specific registration remains BLOCKED_API_EVIDENCE; an API-neutral registration contract can be tested independently. Incoming user reconnaissance is a design input, not locally captured host evidence. User reports FIRST_REAL_HOST_ENGINEERING_SHADOW=PASS; repository at base has not yet recorded that host receipt. FIRST_REAL_ASTRBOT_SHADOW and host_binding remain UNVERIFIED. Do not overwrite Nana's现场 records.

All new development fixtures are synthetic, no external delivery. Real host login/install/reload/JWT/private data access are forbidden on this track. Original project license remains pending; no third-party execution source copied.

## Shared audit update received during development
Nana shared commit 652a72fde12dcb4786491a6a0f73b06e8675fe1a was fetched during C-M6. Its docs/nana_shadow_astrbot_dispatcher_audit_20261011.md gives exact 4.28.0 filter aliases/registry/remove and lifecycle direct-await sites. Added support-only astrbot_shim.AstrBotLifecycleBinding, fixture-tested; it uses two exact private callback names in Nana's existing plugin module and never removes unrelated handlers. StarMetadata is ignored entirely, an operator-issued one-shot permit is mandatory, only sanitized synthetic metadata reaches Core. No SDK import or automatic plugin registration at module import. Nana's existing main.py can explicitly wire this shim after its host compatibility/load gates; Codex did not edit Nana's plugin/evidence.

A safe real dispatcher probe remains BLOCKED_NO_INTERNAL_PROBE. C cannot become A; B doesn't exist in audited EventType. Neutral RealAstrBotBinding continues to block message-stream registration; the new lifecycle-only shim is separately IMPLEMENTED/TESTED. Real callbacks have not been loaded or exercised by Codex.

Source-reported Iris status from Nana's docs/nana_shadow_iris_schema_20261011.md is SCHEMA_COMPATIBLE for11 shapes (actual L2/L3 structure, other types by source). It is Nana's recorded audit, not this inspector's host execution; live WAL parsing by this stricter frozen inspector remains refused. No private value was fetched by Codex.

Runbook conflict: Nana D-044/observer docs recommend one Dashboard reload for a new plugin, but the same source audit states reload(name) cannot load an unregistered directory. Codex will not claim that click suffices. An already-authorized full-load path must be verified by Nana; otherwise BLOCKED_AUTH_REQUIRED remains. No new token/restart workaround.
