# R04 One-Shot Message Shadow — development only

[实测/开发] Input bundle SHA256 `02fa103ad7769cbabcc8632f3981975c09f15108dc0b59610884511c8f755a76`, complete history verified. Sole base `89385e98118da81bae751311fb6149f048b772a8`.

Actual R03 components: `message_hook_adapter.py` extracts nine scalar metadata keys; `main.py` has dormant `on_decorating_result` callback. Support in `tools/nana_astrbot_shadow/{sanitize,observer,core_sink,proof,package}.py`. No early all-message observer. R03 source audit is `docs/nana_shadow_message_observer_audit_20261011.md`; D-044 loading and D-045 dual gates remain in force.

Baseline command: `/tmp/nana-bootstrap-build/compat-python-fixed -m pytest tests tests/nana_shadow -q`. Actual development CPython 3.12.14 / approved private SQLite 3.51.3 / Pydantic 2.13.5; **404 passed / 0 failed / 1 skipped**. Baseline logs/JUnit in `docs/nana_r04_evidence`. E12 NOT_RUN.

Implementation constraints: 55 approved Core files unchanged. Receipt state uses existing `core_meta` projections and append-only Store transaction events. No new SQL table or dependency. Single Store writer and FIFO observer worker serialize consumption; other process ownership conflicts fail closed. Atomic consume records both consumed receipt and event reservation BEFORE any Core Evidence write. Crash after consumption loses the observation opportunity rather than resurrecting permission; explicit read-back reconciliation only, never blind replay. MATCHED is a check inside the consumption transaction, not an independently reusable state.

Production review anchors remain empty, source pinned. Fixture trust has an incompatible persistent domain, not a CLI/env option. A development fixture cannot prove real dispatcher traversal or real binding. Real source pins require independently reviewed Nana evidence, future source review and human authorization.

Real AstrBot load NOT_RUN; dispatcher NOT_VERIFIED; one-shot real message NOT_RUN; host_binding UNVERIFIED; FIRST_REAL_ASTRBOT_SHADOW BLOCKED; E12 NOT_RUN. All real host/private memory/production secrets/messages/model operations by Codex zero.
