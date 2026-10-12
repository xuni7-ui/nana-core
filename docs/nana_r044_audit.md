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

## C2: directory / unlink / readiness fence fixes

Original detached R042 baseline:543passed/0failed/1E12skip (actual privateSQLite
3.51.3). Production/main/PROJECT_BRAIN untouched. Directory replacement regression
fixed using original inode identity + retained directory FD. Socket bind and
sidecar read/write/cleanup are descriptor-relative; no symlink traversal. Atomic
publication and inode-aware detach-before-delete preserve unrelated replacements.
Client independently fences config directory/socket before and after connect;
constructor failures/close release its FD. Store journal now records IPC directory
identity; stale cleanup refuses directory copy/substitution. Wire module copies
remain byte-identical (protocol fields unchanged, implementation fingerprint new).

Also found/fixed MEDIUM startup publication race: client.json existed before
session.json. A crash at that instant made ownership cleanup unprovable. Preserved
failure then publish client capability LAST, after journal/socket/session proof.
The result-write fault injection now targets explicit sidecar write boundary
instead of old private_file helper; SAME cleanup assertions retained.

Evidence:43 existing/new bridge/fault/crash tests and46 filesystem/protocol tests
PASS. Short failure traces/redacted intentional-failure XML are published: pytest
verbose failure renderer can include synthetic test capability locals, unlike
production fixed diagnostics. Redacted all long test hex from the pre-fix
publication failure report; never deliver raw private fixture capability files.
Root/authorized-PID memory modification and raw whole-DB clone are not claimed
protected. Arbitrary DB filename race by a privileged same-UID filesystem writer
is not made atomic by unchanged Core SQLite VFS; IPC descriptor fence does not
invent that guarantee. Core remains unchanged.

## C3 pending supply-chain findings (tests preserved before fixes)

LOW: integrity enumeration ignores dangling symlink/FIFO extra entries.
HIGH (permission-drift condition): verification accepts group/world-writable
package code/manifest/root, permitting other local users to race verified imports.
Default delivered permissions were not writable; gate lacked explicit rejection.
LOW: Git review reader accepts mode120000 symlink blob if its bytes are canonical
JSON. No real authorization minted; human reviewed source boundary remains.
Six failing assertions preserved in supply-failures.xml; no success claim yet.

## C3: supply-chain fixes and concurrent ingress

Integrity gate now enumerates ALL immutable entries, rejects dangling symlinks,
FIFO/special objects, hardlinks and group/world-writable files/directories. Mutable
Shadow data is pruned (not scanned/read); symlinked data root still blocked. Both
stdlib pre-import r04_entry and imported package verifier enforce the policy.
Git review source must be mode100644 blob at exact full commit/path (not symlink
or executable JSON). Existing source review/operator trust boundaries unchanged;
no production seal/pin minted. Targeted package/onboarding:42pass.

UDS races:13pass including2/10/100/500 same/different events, consume/disarm FIFO
ordering, competing writer lease rejection, live read snapshots, pidfd/start-time
change and copied IPC directory rejection. Documented128-frame lifetime cap may
fail closed with0 ingress under500 flood; at most1 ALWAYS, no liveness claim under
DoS. Duplicate concatenated frames accept at most the first authorized framed
message then close; no second frame executes or creates ingress. No generic RPC.
Actual kernel PID reuse is NOT forced; injected start-time mismatch and original
actual foreign-process/SIGKILL tests exercise the comparison. Do not claim a
kernel PID-allocator stress result which was not run.

## C4: capability ownership / publication / readiness and crash qualification

LOW pre-existing cleanup finding: same-session client.json with altered hash key
was accepted for deletion. Preserved failure, then Store BOUND/CLOSED journal pins
only client_config_digest (no key/nonce), cleanup validates complete digest before
ANY deletion. Descriptor cleanup can recover matching detach tombstones; unknown
conflicts preserved/UNKNOWN_NEEDS_REVIEW. Pre-existing sessions missing new journal
fields intentionally BLOCKED, never guessed/rearmed.

MEDIUM R044-introduced-and-fixed finding: hardlink atomic publish briefly exposed
nlink2; a reader observing client.json could fail strict readiness. Preserved
failure, replaced with fixed Linux renameat2(NOREPLACE) (stdlib ctypes, no new
dependency/generic RPC). Unsupported platform fails closed; no unsafe fallback.

LOW pre-existing readiness diagnostic: preflight could report READY for expired
or VERIFY_ONLY reviewed/ARMED snapshot. Preserved counterfactual snapshot tests
(no production pin). Preflight explicitly checks UTC live window, production
trust domain and executable ONE_SHOT source seal; Production worker independently
rejects non-executable seal before reservation. Actual consume/arm already had
D-046/R042 hard gates; no consume permission bypass demonstrated.

Actual32 OS SIGKILL points: init/binding/receipt create/review/arm/session reserve/
bind/sidecar publish/frame/consume transaction/Evidence/Core complete/cleanup/
unlink/verify/close commits. Each uses another independent read-only process;
classification SAFE_RETRY / TERMINAL_CONSUMED / UNKNOWN_NEEDS_REVIEW / BLOCKED.
No auto rearm/retry; partial unpublished session is UNKNOWN, not permission to
unlink unverifiable objects. Source counts/identity/JSON/zero-action checks PASS.
25 time/trust tests PASS (UTC/skew/high-water/reopen/tamper, no production minting).

Soak on pre-C4 worker version:1000 fixture API-worker cycles,10000 rejected frames,
1000 create/disarm in20.696sec. FD4->4, thread1->1, RSS33808384->37785600 bytes,
0 owned sockets/caps/held leases/temp dirs. /proc/task/children unavailable: global
child observation UNKNOWN, not falsely0; this API soak spawns0 subprocess workers.
New actual-process lifecycle test and final-code repeat follow. Fixed bugs so far
have no demonstrated duplicate ingress or real reply; all product changes stay
outside approved Core and Brain09/10/11.
