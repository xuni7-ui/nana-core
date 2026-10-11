# R04 One-Shot Message Shadow — development only

[实测/开发] Input bundle SHA256 `02fa103ad7769cbabcc8632f3981975c09f15108dc0b59610884511c8f755a76`, complete history verified. Sole base `89385e98118da81bae751311fb6149f048b772a8`.

Actual R03 components: `message_hook_adapter.py` extracts nine scalar metadata keys; `main.py` has dormant `on_decorating_result` callback. Support in `tools/nana_astrbot_shadow/{sanitize,observer,core_sink,proof,package}.py`. No early all-message observer. R03 source audit is `docs/nana_shadow_message_observer_audit_20261011.md`; D-044 loading and D-045 dual gates remain in force.

Baseline command: `/tmp/nana-bootstrap-build/compat-python-fixed -m pytest tests tests/nana_shadow -q`. Actual development CPython 3.12.14 / approved private SQLite 3.51.3 / Pydantic 2.13.5; **404 passed / 0 failed / 1 skipped**. Baseline logs/JUnit in `docs/nana_r04_evidence`. E12 NOT_RUN.

Implementation constraints: 55 approved Core files unchanged. Receipt state uses existing `core_meta` projections and append-only Store transaction events. No new SQL table or dependency. Single Store writer and FIFO observer worker serialize consumption; other process ownership conflicts fail closed. Atomic consume records both consumed receipt and event reservation BEFORE any Core Evidence write. Crash after consumption loses the observation opportunity rather than resurrecting permission; explicit read-back reconciliation only, never blind replay. MATCHED is a check inside the consumption transaction, not an independently reusable state.

Production review anchors remain empty, source pinned. Fixture trust has an incompatible persistent domain, not a CLI/env option. A development fixture cannot prove real dispatcher traversal or real binding. Real source pins require independently reviewed Nana evidence, future source review and human authorization.

Real AstrBot load NOT_RUN; dispatcher NOT_VERIFIED; one-shot real message NOT_RUN; host_binding UNVERIFIED; FIRST_REAL_ASTRBOT_SHADOW BLOCKED; E12 NOT_RUN. All real host/private memory/production secrets/messages/model operations by Codex zero.

## Baseline discrepancy (actual Git, not silently overwritten)
R04 changes **zero** files under `src/nana_core`, relative to sole R03 base. However the R03 repository itself differs from approved ddab source in **one pre-existing file**, `src/nana_core/integration/preflight.py`: historical Pydantic version acceptance changed. Therefore "all55 repository files byte-identical to ddab" is FALSE at supplied baseline. R04 does not repair/restore that file. Package builder continues sourcing the **55 approved bytes directly from ddab**, so packaged Core remains approved. No new Core SHA is claimed. This discrepancy does not require changing a Core invariant for R04; real host approval must distinguish source repository vs pinned package.

Evidence export sanitization: baseline JUnit parametrized test names included old synthetic credential-pattern attack strings. Those test node labels are redacted in the exported evidence; counts/assertions/outcomes unchanged. No actual credential was read. Stage scanner rejects such patterns before subsequent checkpoints.

Checkpoint text correction: R04-C6-C8 commit message said65targeted; actual JUnit/output is **62 passed**, superseding that clerical number. Initial collection and network-guard fixture errors remain recorded: restricting outbound connect/DNS preserves asyncio's local socketpair while forbidding external transport. No safety assertion was removed.

Trust boundary hardening: dormant packaged plugin rejects FixtureTrustStore adapters and empty production pins at binding time, not only consumption. Future factory must first verify an ARMED production receipt; consumption still rechecks trust/time/scope atomically. Plugin remains dormant; none of these operations ran on a real host.
