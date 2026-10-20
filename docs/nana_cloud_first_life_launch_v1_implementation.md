# Cloud First-Life Launch V1 — development checkpoint

Base b06e1e72f63a481ba349c23043c4027f137b9876, branch
`dev/nana-core-cloud-first-life-launch-v1-codex`. GLOBAL_STAGE remains H.
Existing RAE/CDL is inherited. This work does not repeat those implementations or
claim the complete Nana engineering goal is finished.

## Durability changes

The retained CDL reference database was inspected in read-only mode, not opened
as another writer. Its post-handoff main file is about12.6MB. SQLite dbstat shows
about6.8MB allocated to events,1.68MB to artifacts,0.62MB to record dependencies,
0.57MB to runtime queue, plus indexes. Large contributors are source-bound C
cycles and full-row replay audit for enqueue/check/finish, not an unexplained
WAL-only leak. The original2h process samples showed queue peak2/final0 and
pending peak5/final4; about651s onward DB-family growth was1.97MB.

Source/lineage, event audit, real outcomes/actions, UNKNOWN and deletion journal
remain permanent. Search terms and context/Journal are derived. Operational logs
may rotate; checkpointed WAL/free pages may be reused. Explicit verified archival
is a future lifecycle operation, not an excuse to drop history or create another
Subject authority. No audit rows, source payloads, privacy intents or IDs are
removed by this change. There is no new business table or schema migration.

`life/durability.py` supplies a bounded numeric projection and host-local guard.
The projection reports page/freelist allocation and latest4096 event-kind bytes,
not raw memories. The cheap runtime guard samples sizes on a bounded cadence,
issues PASSIVE checkpoint, and stops on a physical family cap or a post-startup
logical-growth limit. It does not invent a motive or change C's judgment.

Default host ceilings are256MiB state and32MiB/hour growth,60s review,600s grace
and600s measurement windows. Growth uses logical pages plus deletion anchor to
avoid treating WAL checkpoint oscillation as new history. Physical family size
still includes WAL/SHM and the real privacy anchor. The window and any STOP latch
persist in a private atomic host document across restart. A corrupt/future-clock
monitor fails closed, and the CLI evaluates it before accepting control/chat.
A latched stop is not cleared automatically. Health exposes the stop reason.
The monitor contains operational sizes/time/status only, never identity/memory
truth; B8 continues to transfer only its original three files.

## Real entry for later human review

`life chat` is an actual private socket client to an already running original
Runtime. It does not open a Store or instantiate another SubjectLoop. Explicit
PUBLIC/PROJECT privacy is required; the banner disallows secrets/private history.
Fresh event IDs, existing source correlation, bounded body, same-UID/lease PID
checks and no replay on UNKNOWN are preserved. Raw text remains volatile in the
original bounded dialogue context. The user's `/quit` stops only the client.

Without a separately authorized real model this is explicitly limited offline
interaction. It is not naturalness qualification. Provider fabrication, free
model output or a client command cannot adopt goals, create authority, change
Manager/Primary User or mark an effect successful.

`life review` accepts a strict human-declared structured rating with actual
Subject UUID, category, elapsed minutes, numerical ratings and boolean issues.
It accepts no transcript/comment/raw-text field, rejects wrong identity and
creates an immutable private host review file. It emits no Subject event and
cannot promote FirstLife/Beta. Automated DTO tests use synthetic declarations;
REAL_NATURAL_DIALOGUE_REVIEWED remains NOT_RUN until a user actually participates.
The command is an evidence entry, not a cryptographic detector of human authorship.

## Ownership transition and rollback

The runnable rehearsal starts three sequential actual CLI processes on a fresh
synthetic reference Subject: legacy-role, next Core owner, then rollback owner.
It rejects transfer while the old process is active; after graceful stop, B8
retires the source before destination activation. The retired source cannot
resume. Epochs advance2→3→4, one inbound synthetic shadow input is preserved,
identity/recent continuity remain, and there is no social send or inherited
execution Grant. Rollback transfers the current lineage to a fresh home; it does
not overwrite newer history with a stale snapshot.

This tests the mechanism in development. It does not establish actual AstrBot
production writer identity, inspect Iris, access QQ/Bili accounts or perform a
real service transition. Production inventory and cutover are separate gates.

## Isolation and ongoing residency

The supervisor reuses the original CDL actual-process runner and source-backed
Hands/F/G/I path. It makes operational progress snapshots; it is not another Nana
Runtime, scheduler, planner or store. The candidate build is pinned in a detached
worktree; explicit PYTHONPATH is inherited by its children and the supervisor
checks the actual imported Core location. Ordinary subsequent development cannot
silently alter the pinned residency source. The existing venv/dependencies are
reused without install.

The first90s combined run reproduced42 actions,14 owned effects, actual SIGKILL,
source deletion, backup and fresh-host same-identity transfer. It is explicitly
SHORT, not24h. A separate86405s isolated run is started from the hardened pinned
build. Its actual progress and final result are separate operational files; only
actual elapsed>=86400s, successful assertions and unchanged source can yield
PASS_24H_DEV. Interruption or an absent result stays PARTIAL. Final progress
separates old sampled runtime from a fresh terminal ownership observation.

The managed workspace is not attested as a permanent cloud server or production
volume. A /workspace directory alone does not prove persistence across environment
loss. The real hosting/backup choice still needs confirmation before production.
No provider or account runs in this isolated synthetic residency. It must not be
silently repurposed as a paid real-chat test or mistaken for live-provider quality.

## Gates and next action

Current environment has no ready safe provider credential binding. A new endpoint,
model, privacy, call/cost allowance and explicit FD/SecretResolver are requested;
no old key, environment secret search or previous UNKNOWN replay occurs.
Real provider calls0; prior one UNKNOWN stays parked, retry0/fallback0.

Human naturalness/shared-life review, actual production inventory, real QQ/Bili
inbound/outbound, service cutover, canary and72h are NOT_RUN. The real production
host/service/writer cannot be guessed from repository history. One concrete
production recommendation and the user's final approval come only after those
prerequisite facts are known. Do not interpret a dev rehearsal or structured
rating schema as approval to switch writers or send socially.

FirstLife and Beta remain NOT_READY. Evidence/result figures and current ongoing
staging checkpoint are in the status/evidence files. Main, R045, production,
legacy live systems and the old untracked bundle remain unchanged.

Final source qualification: frozen645899b; focused6 passed2.72s, full1274 passed/12 skipped/0 failed280.58s. Related first-life/cloud25 passed16.64s before last client case. Documentation final checkpoint does not alter executable files used by the ongoing detached-worktree residency. This is a PARTIAL handoff, not completed First-Life launch.

### Provider authorization update — credential binding still blocked
[用户显式授权 + 环境实测2026-10-20] 新资格目标DeepSeek / https://api.deepseek.com / deepseek-flash，
OpenAI-compatible，PUBLIC/PROJECT only，最多20真实调用、$1等值上限；PERSONAL/SECRET不授权。
用户声明Secret已在个人保险库，名称DEEPSEEK_API_KEY。环境实时observations_current=true/revision281，
secrets=[]、runtime_variables=[]：尚未绑定到当前任务。工具仅支持environment_status，无配置修改工具。
因此BLOCKED_NO_CURRENT_ENVIRONMENT_SECRET_BINDING；新真实调用0；模型/endpoint尚未live验证。
不搜索环境/历史key，不读个人保险库原文，不用明文文件；已请求用户通过环境配置绑定并审核。
绑定ready后仅从显式宿主安全源→内存pipe/FD→现有ExplicitFDResolver，沿原预算/Privacy/UNKNOWN合同。
历史TianToken UNKNOWN仍PARKED，禁止重放或fallback。此前“未获付费范围”在本时点被上述有限授权取代。
