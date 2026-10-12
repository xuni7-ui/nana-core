# R044 Pre-Production Red Team / Recovery Qualification

Development-only branch, base a436333d3dceb30773860ff5a3168ca1acdf6682.
User explicitly keeps PROJECT_BRAIN/09/10/11 untouched this round; all new facts
are separate audit evidence, for later Nana/Sister adjudication. Approved Core
is not modified. Shipping production pins EMPTY, E12 NOT_RUN. No host/login/
Dashboard/private memory/real message/model/authority operation.

## C0: source audit / preserved failing regressions

Sources: original one_shot.py ledger/core_meta/event log; bridge_worker.py
single-writer observer; stdlib bridge_wire.py/plugin byte-identical protocol;
bridge_cli.py pidfd/start-time/boot/inode readback; onboarding.py immutable Git
review source / EMPTY sealed_trust.py; package.py pre-import integrity checks.

Initial failing development tests (recorded BEFORE fixes):
1. MEDIUM: result.json write failure in worker finally skips observer/Store/socket/
   client cleanup. Test asserts observer inactive, lock reacquirable and ephemerals
   gone; baseline fails observer.active. May leak local resources/capability until
   hard process exit; no permission multiplication or real reply shown.
2. MEDIUM: private IPC directory replaced after constructor, before serve.
   Baseline only retains path, accepts new same-permission directory and writes
   session/socket there. Test expects fixed inode directory fence, baseline does
   not raise. Receipt remains single-use; filesystem isolation fence incomplete.

Evidence: docs/nana_r044_evidence/initial-failures.xml (2 expected regression
failures, not successful qualification). Fixture inputs only. Each will retain
an assertion and get a separate fix/evidence record.

## Runtime preparation

Prior /tmp launchers were absent, approved package binaries remain. Restored a
short-lived development-only launcher using exact approved private binding:
CPython3.12.14 / SQLite3.51.3 / Pydantic2.13.5 / pytest9.1.1. This changes only
isolated DEVELOPMENT process imports, not AstrBot/system dependencies.
Native old-SQLite dependency-isolation helper uses installed CPython3.13.5 /
SQLite3.46.1 in this environment. It proves stdlib client import isolation under
old SQLite, NOT parity with real AstrBot Python3.12.14. Real host unavailable.
An initial launcher incorrectly used production -I/-S flags for pytest, causing
a test hard-deadline to terminate the test process; classified as launcher error,
not a product regression or successful baseline. Corrected helper preserves
ordinary pytest flags and isolated flags only on explicitly flagged children.
No system installs/new dependencies. Full baseline rerun is required.

## Mechanical invariants

Executable suite covers every state x review/arm/consume/disarm combination,
24 deterministic seeds x200 operation sequences, restart/copy/corrupted review,
terminal uses1/replay and fixed identity. Fixture class cannot authorize real
provenance; source maps remain distinct EMPTY maps. VERIFY_ONLY production gate
rejects; client AST rejects Core/privateSQLite/Pydantic imports. Broader resource,
protocol, filesystem, trust, recovery and package evidence follows checkpoints.

## Honest boundaries

Runtime protocol cannot authenticate a dishonest privileged source builder;
Git/hash pins reviewed bytes, not human approval. Whole-DB cloning by a privileged
actor outside approved quarantined backup/replay remains outside the guarantee.
No offline fixture result upgrades real binding/dispatcher/message/zero-drift.

## C1: report-write cleanup bug fixed

Fix: independent finally boundaries. Failed result/UNKNOWN/session evidence I/O
cannot skip observer close, original Store writer shutdown, owned socket/client
cleanup. No failed report is upgraded to PASS. The preserved result-write failure
regression now passes, and existing receipt invariants/engineering tests:71pass.
IPC directory replacement repro remains pending C2; qualification not yet PASS.
A new client AST test initially inspected unused legacy R04 lazy-binding imports;
corrected to inspect actual module-level/extractor client path, preserving the
prior subprocess forbidden-import guard. This was a test-scope error, not removal
of an executable client dependency check. Ordinary/isolated child flags and
absolute executable corrected in temporary development launcher; no Core edits.
