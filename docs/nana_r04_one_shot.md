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

## Final development evidence
- R04 targeted **64 passed**; combined R03/prior/new full suite **468 passed /0failed /0errors /1skip(E12)** on actual CPython3.12.14/privateSQLite3.51.3/Pydantic2.13.5. All old tests retained. JUnit/logs `docs/nana_r04_evidence/release_full.*`.
- Actual SIGKILL(-9): before consume, inside transaction before COMMIT, immediately after commit, before Core Evidence, after Evidence/before local completion. Atomic result consumes0or1; post-commit cases retain uses1/completionUNKNOWN, no re-ingest. This does not claim an instrumented kill inside SQLite's internal fsync instruction. Existing full suite SIGKILL/WAL tests also preserved.
- 2/10/100 competing events queued to the exact single-writer FIFO topology: oneACCEPT, N-1ALREADY_CONSUMED. No in-memory list dedup; receipt/event fence in Store commits. Scope/type/source/time/malformed/expiry/skew/clockrollback/duplicate/reviewreuse/copiedreceipt/backupquarantine/metadatahostileobjects/exception/timeout/cancellation/lateexception/logger/store/core tamper covered.
- Final extracted-package verification runs **after source commit d025636c2682f84c36be12007f1a4058ffaf5b2e**: external/file hashes, all55 exact approved bytes, ABI/private runtime/preflight, fixture harness/reopen/replay/barrier/closure, CLI refusing fixture-domain arm, dry-run zero writes, executable tamper blocked **before execution**. Package validation JSON is development evidence, not real host proof.
- `nana-r04-one-shot-d025636c2682-delivery.tar.gz`: **3,325,152bytes**, SHA256 **91e5c29e2b50b52f9931d44331770cbc577c4bbda027f743fb6cb87154b6749b**. Source supportd025636…; Coreddab…; unchanged private runtime contentmap95c721… . Package contains no runtime DB/credential/private body; embedded plugin ZIP is dormant, no automatic installation or arm.

## Remaining boundary
Real pinsEMPTY deliberately blocks actual review/arm/loadbinding. Actual host support module wiring/dependency readiness and dispatcher/registry/unload proof are not fixture-derived. R04 source implements the authorized mechanism; it does not manufacture its production authorization. Do not edit trust pins merely to get PASS. Schema unchanged/no new dependency; source license remains owner decision, runtime third-party licenses preserved.

Recommended handoff: merge this independent R04 branch **in Nana's development copy based on R03**, preserve append-only Brain tails. Alternatively cherry-pick oldest-first all R03..R04 commits, then full approved-runtime regression. Never cherry-pick onto old10581/c3ada/652 baselines; never main merge or production commit.

### Final permit-type seal (supersedes previous468 release count)
Independent sanitizer gate additionally requires exact `ReceiptLedger` type, rejecting duck-typed forged ledger before consulting it. All runtime calls already used the real ledger; this closes an exposed permit-construction contract, not a Core change. New full suite **469passed/0failed/0errors/1E12skip**, including65R04 tests. Evidence sealed_full.xml/txt. Rebuild final package from this committed support; the d025 archive remains historical, not the final current-source release.

Final sealed archive supersedes d025 candidate: see `docs/nana_r04_evidence/package_final_build.json` and `package_validation.json` for exact **095a5fa…support** asset bytes/checksum. Sealed full JUnit469pass/1skip is authoritative; prior logs/counts remain historical. No further source changes after095a5fa. Real production statuses unchanged.

### CLI diagnostic final seal
Adversarial CLI review found argparse's default invalid-argument diagnostic echoes values. `_SafeParser` now blocks with a fixed code, never printing caller values. Existing negative --force/--trust-all assertion is strengthened to exact return2, not bypassed or removed. New private-canary invalid-argument cases ensure stdout/stderr contain no input. Latest full evidence cli_sealed_full.xml/txt supersedes earlier final counts: **470passed/0failed/0errors/1E12skip**, including66R04 cases. No further source changes required; final package must use this committed support.
