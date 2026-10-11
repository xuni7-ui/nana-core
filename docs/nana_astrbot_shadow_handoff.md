# Codex → Nana Real AstrBot Shadow handoff

Repository xuni7-ui/nana-core; Codex dev branch dev/nana-core-v1-astrbot-shadow-bind-codex. Creation base c3ada9b09faa8a2683f98d5c8bafec24779cfd71; Nana source input652a72fde12dcb4786491a6a0f73b06e8675fe1a. Approved Core ddabfc4e49221b45a9f9600dd2ab8cb7f66ec51355 files unchanged. No writes to Nana shared branch or main.

## Files to hand over

- tools/nana_astrbot_shadow/sanitize.py: strict metadata entrance and keyed scoped IDs.
- observer.py: async no-response callback, serial local Store worker, bounded deadline/busy drops and late-exception redaction.
- core_sink.py: original Store/HostObservationAdapter/ShadowBridge/GoalCandidate, persistent event+probe aliases; no new SQL tables.
- proof.py: structure + independent persistent evidence/candidate/draft linkage check. Real origin trust pins empty.
- astrbot_shim.py: exact4.28.0 lifecycle filter/registry adapter, source reference652a72f; ignores StarMetadata and requires one-shot private permit. Real SDK invocation NOT_RUN by Codex. Message/EventBus remains blocked.
- iris_schema.py: frozen metadata-only SQLite allowlist+authorizer; real live-WAL/privacy extraction disabled.
- docs/nana_astrbot_shadow_package/: pre/post/unload/rollback/operator checklists.

## Download and minimal local commands

Archive **nana-astrbot-shadow-observer-8e61c1e.tar.gz**, **3,300,736bytes**, SHA256 **77362306eddca16e12de5b08ee4748778caf4cf328e72bc9becea29f2c63355a**.
Remote bytes independently fetched/verified from private Git asset, download: https://github.com/xuni7-ui/nana-core/raw/6f7da397f2795f0a29720fdb7c85b0552b7dd15a/artifacts/astrbot-observer/nana-astrbot-shadow-observer-8e61c1e.tar.gz

Core fixedddab, support8e61c1e4c6d6f1f1923ac4d5a5dc9915b3c0a3b4, unchanged runtime hash95c7215bc78d43cae809e99fcc65c1572cd611c87ae273afb80138b61c01e6ec. Runtime is short-lived harness only; no private SQLite injection into an existing AstrBot process.

1. Verify archive checksum externally; unpack to a NEW independent directory.
2. ./observer.sh verify; ./observer.sh preflight.
3. Optional ENGINEERING_C_ONLY: ./observer.sh harness; repeat once; ./rollback.sh; ./observer.sh collect. This does not install/load a real plugin or prove AstrBot dispatch.
4. In Nana's development copy, wire the source-backed lifecycle shim into its existing observer entry instead of the prototype logger; do not register both. First verify actual host dependency/module drift and permitted no-restart full-load reachability. If Core unavailable, DROP, never alter host deps or spawn a permanent alternate Runtime.
5. Only after Nana's existing host authorization covers an actual reachable loader: register, arm one synthetic metadata probe, inspect registry/Core/dedup/barrier, unregister, inspect callback absence and host zero-drift/health. No private traffic/message pipeline/JWT access.

Current known blockers are BLOCKED_AUTH_REQUIRED (new plugin load) and BLOCKED_NO_INTERNAL_PROBE (safe dispatcher). A single Dashboard reload(name) does NOT establish new-directory load. Lifecycle C cannot close real dispatcher gate, even if registry binding works.

## Merge/cherry-pick without competing shared pushes

Nana should fetch this branch into its DEVELOPMENT clone, not production. Preferred: merge the Codex branch there, preserving every Nana现场 file and both append-only ledger tails. Only PROJECT_BRAIN/09_STATE,10_DECISIONS,11_CHANGELOG overlap; retain Nana original append blocks and append Codex development entries, never choose whole-file ours/theirs. Code is additive under tools/nana_astrbot_shadow; no approved Core or Nana plugin overwrite.

If cherry-picking instead, apply the following content commits oldest-first, followed by this FINAL docs receipt (HEAD resolved by git/ls-remote). Resolve any append-only ledger conflict with both blocks intact; then run full regression. No main merge/deploy.

```
3af965da2dba36b9235726bcd0191308b5c56274 C-M0: Baseline 318 passed, E12 skipped; source audit and API evidence gap recorded
47f50db59c301ec2d1fc0cc5e78cb2dee48f0402 C-M1: Metadata sanitizer and no-response observer contract; 13 targeted passed, collection failure retained
0ddbedfc3a804ee0a89fef66fb3f74e1a919ee71 C-M2: Persistent Store alias dedup and reviewed-origin binding proof; 13 targeted passed; unchanged approved Core
c5a0f32ccb3e427ed4feb7f476b21b3330149199 C-M3: Shadow barrier and bounded callback failure isolation; 9 targeted passed including actual SIGKILL gap recovery
d63f909531864831905866e0e156884dea702c92 C-M4: Source-gated AstrBot registration block and exact neutral registry lifecycle; 3 targeted passed, shared audit still absent
fc4e2172e361180334c4a9e12fc1ff76fb8494bb C-M5: Exact-query Iris schema inspector with authorizer and frozen-source comparison; 13 targeted passed, real compatibility UNKNOWN
ff407dc0b492662a2b76dd915e03e9b3658472d7 C-M6: Observer development kit builder, independent Core proof readback and operator rollback/runbook; 13 targeted passed, real shim blocked
686363e8487d7eadbe365ad709b9cefaee6ea90c C-M4-SOURCE: Nana audit652a72f absorbed by reference; source-backed 4.28 lifecycle shim and safe unload, 21 targeted passed; dispatcher still blocked
8e61c1e4c6d6f1f1923ac4d5a5dc9915b3c0a3b4 C-M7-HARDEN: Lifecycle shim and kit validated in two actual Python environments; fail-closed BaseException/deferred completion guards, 22 targeted passed
6f7da397f2795f0a29720fdb7c85b0552b7dd15a C-M7: Final full regression 372 passed one E12 skip; reviewed observer kit archive, approved55 unchanged and zero production actions

```

## Acceptance and unverified boundaries

Full final372passed/0failed/0errors/1skip(E12), source/runtime fail-closed guards22targeted; preserved original318tests. True SIGKILL(-9) observation-commit→decision gap recovers without duplicates. Current archive fresh unpack C-probe/restart/dedup/independent links/close/unload/tamper checks actual3.12.14 andUbuntu3.12.3PASS; only3.12.14 ran this latest full suite.

No-body guarantee, persistent dedup, Shadow barrier and failure isolation PASS in development. Actions/Attempts/Grants/production budgets0. Real model calls0/E12NOT_RUN; production/source changes, host calls, private memory reads, secret reads and external messages0. No new dependencies/Core SQL tables. Secret/private/artifact scan PASS.

Nana report652a72f says Iris11/11SCHEMA_COMPATIBLE, backed by source and real L2/L3 metadata inspection. Codex has not inspected any real Iris DB. Real AstrBot load/probe/unload/health/zero drift, host_binding, dispatcher traversal and model semantics MUST NOT be upgraded from these fixtures. Independently reviewed real receipt pins remain absent.
