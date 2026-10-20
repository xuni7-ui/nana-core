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

## CURRENT — FIRST-LIFE / DEEPSEEK FIRST LIVE REQUEST / PARTIAL
[实测2026-10-20] 当前开发分支dev/nana-core-cloud-first-life-launch-v1-codex；GLOBAL_STAGE H。
用户本轮显式提供新凭据并要求执行，走关闭echo的进程stdin→内存pipe→原ExplicitFDResolver；非保险库绑定成功。
凭据不入argv/env/config/evidence/Store，resolver已清理、临时调用进程结束；资格home/result exact scan0。
DeepSeek https://api.deepseek.com / requested+returned deepseek-flash；新真实调用1，HTTP200，3688.587ms，
usage5790 input/565 output/6355 total；严格解析、CognitionSession PROPOSED、原C WATCH/SOCIAL_INTERACTION。
未创建Actions/Grants/Goals；retry0/fallback0；历史TianToken UNKNOWN仍PARKED，不重放。
首batch硬限1次，RENDER被PROVIDER_HOURLY_BUDGET挡住：语义传输成功不等于自然对话通过。
真实费用UNKNOWN，公开文档当前未取得可核对适用费率；扩大调用暂停在cost-bound门（总授权20次/$1）。
REAL_TEXT_PROVIDER=PARTIAL_TRANSPORT_INTERPRET_PASS；human naturalness/shared-life NOT_RUN；FIRST_LIFE/BETA不升级。
修复“已配置provider却因render预算阻断显示未配置”的误导fallback，保留原测量结果，targeted12 passed8.01s。
24h staging独立固定645899b持续运行，已实际恢复epoch2→3，仍RUNNING_NOT_QUALIFIED；不接本次凭据。
生产盘点/切换/canary/72h仍NOT_RUN，main/R045/production/private data/real social不变。
下方CURRENT为保留历史；前述“新调用0/当前完全无凭据”的事实由此本轮显式输入与实测更新，不改历史UNKNOWN。

[实测 post-live final] provider-budget/dialogue targeted12 passed8.01s；最终full1274 passed/12 skipped/0 failed286.16s。
DeepSeek资格home无transport重新打开：同identity、同1条PROPOSED记录，无自动发送/重放、新调用0。
24h dev growth guard真实window600.914192s，logical growth167936bytes（约0.96MiB/hour观测速率），
低于32MiB/hour configured fence，状态OBSERVING；未裁剪history。仅有界窗口，不冒充24h。
新Provider总调用1，usage已知、actual billing/cost UNKNOWN，等待可核对费率；真人自然度/Shared-Life NOT_RUN。
Source/staging与live/fix证据分别登记；新Source修复不覆盖固定645899b驻留进程。

## CURRENT — FIRST-LIFE / DEEPSEEK FUNCTIONAL TEXT QUALIFIED / HUMAN REVIEW PENDING
[实测2026-10-20] 同一主线/分支，GLOBAL_STAGE H。累计17次DeepSeek / deepseek-flash；独立request IDs17，
无automatic retry/fallback/UNKNOWN；旧TianToken UNKNOWN PARKED，不重放。14 PROPOSED、1 REJECTED、2 FAILED保留。
真实功能场景：natural(v3)、source-grounded/correction(v4)、disagreement wording/unknown(v5)、shared(v6)
均INTERPRET+RENDER；拒绝topic与重启后仍关闭均0模型调用。原C judgment逐项保留，不把模型“不同意”措辞伪装Core DISAGREE。
Shared引用的是实际开发资格HTTP200及源码观察，不是私人共同历史/production经历，不能冒充真人Shared-Life评审。
累计保守reservation850000 nominal USD micro/$0.85，上限1000000/$1；累计calls硬限20，余3；
小时/日20，仅资格home CAS；跨重启/跨日期累计限制复用原cognitive_requests，失败/拒绝/UNKNOWN不退款。
实际billing UNKNOWN，16/17次可见usage总计80350 input/12320 output（非完整总量），provider-side硬扣费cap未attest。
修复对话wire schema角色范围与无关$defs，不弱化Core authority/schema gate；保留partial finish_reason/model/usage观测。
可选host profile chat_thinking_mode=DISABLED（官方公开文档已核实；默认PROVIDER_DEFAULT不变），
资格context16384/output2048/timeout15000ms继续与Model/Route/Runtime求交；生产默认8192/1024不变。
私有IPC评审入口已实际启动，same reference identity b5864db1-ecfe-4278-9bc2-76db0e096311、PID59982，
/workspace/nana-staging/first-life-deepseek-01/life；最多7200秒，当前余3calls通常仅1完整轮；不持久化真人对话原文。
Human naturalness/Shared-Life review NOT_RUN；FIRST_LIFE_EXPERIENCE_READY=NOT_READY，BETA_READY=NO。
24h staging根/workspace/nana-staging/first-life-24h-01固定645899b独立继续，约1h时ACTIVE/epoch3/q0/RSS44708KiB，
该进程provider calls0，未重启/污染，不冒充24h PASS。生产inventory/cutover/canary/72h仍NOT_RUN。
One original C/Store/Runtime owner per reference lineage；schema13/43表，新表0/新依赖0；main/R045/production/private/social不变。
下方CURRENT是保留历史；DeepSeek新functional qualification不把历史H1 TianToken/Qwen PARTIAL改成FULL。

[实测 continuation final checkpoint] focused70 passed13.81s；最终full1279 passed/12 skipped/0 failed294.18s。
当前凭据exact-match审计：1520个受控文件约49.7MB+git diff，matches0/oversized skip0，包含tracked/evidence/资格home+logs；
不搜索历史凭据、不读取旧bundle，不声称审计平台工具日志或所有宿主存储。当前人工入口凭据仅在有界进程内存持有，
不是“所有进程已清空”；早期资格进程已退出，新入口停止后Resolver clear，无自动credential恢复。
剩余3次模型调用通常仅1完整轮；未收到真人消息/评审则Human NOT_RUN，不把开发者候选检查当Human通过。
主线继续门是当前私有开发入口人工体验；24h真实驻留另行等待结果，不提前production inventory/cutover。

## CURRENT — FIRST-LIFE / HUMAN REVIEW CONTEXT REPAIR (OFFLINE)
[源码/离线实测2026-10-20] 上次真人样本不具备正式自然度评审条件：入口未装载当前主线状态，
且明确项目状态询问被误分类。问题归属评审链路，不归因为用户表达或DeepSeek自然语言能力。
原样本与原判断不改写；该样本从正式评审样本排除，不给语言质量分或真人PASS。
复用原ContextAssembler：显式host-local binding只读取09_STATE顶部typed当前状态header，
源前缀最多12288bytes/JSON最多8192bytes，scope/privacy先于读取，revision/as_of/hash有来源；
不扫描整个Brain、不读取开发日志、不新增Memory/Store/SubjectLoop。工程状态标明外部事实，不能称个人经历。
明确PROJECT_STATUS询问要求该block入选原token预算；缺失、过期、删除、损坏或回复期间变更fail closed。
原INTERPRET+SubjectLoop+RENDER接入同一projection；中性接收元数据不预判UNCLEAR，模型不能覆盖明确询问。
原topic拒绝、Privacy/Manager/Grant/预算边界保持；本轮真实调用0，累计DeepSeek19、名义reservation950000。
余1次冻结不用，未扩预算；真实账单仍UNKNOWN。历史TianToken UNKNOWN PARKED，retry0/fallback0。
现有评审home仅host config CAS绑定状态源，未开启Runtime、未写Subject状态，预算仍20/1000000。
三项修复门仅为OFFLINE/FIXTURE PASS；Human Naturalness/Shared-Life正式评审NOT_RUN。
FIRST_LIFE_EXPERIENCE_READY=NOT_READY；Beta不升级；24h staging固定645899b独立继续，未重启或污染。
证据human_review_context_repair.json/current_state_host_binding.json；最终回归结果见context_repair_test_summary.txt。

[实测 review-context修复最终回归] 新增21项纳入focused54 passed19.12s；显式tests/全仓库1300 passed/12 skipped/0 failed326.97s。默认legacy testpaths另588 passed/1 skipped125.37s，不冒充全仓库。
HUMAN_REVIEW_CONTEXT_CURRENT_STATE=PASS；PROJECT_STATUS_INTENT_CLASSIFICATION=PASS；NO_SECOND_MEMORY_AUTHORITY=PASS（OFFLINE/FIXTURE）。
本轮新真实调用0，原累计19、余1冻结、budget未提高；准备请求最多4次/新增保守reservation上限0.20USD的重新评审授权，尚未获批也未执行。
真人自然度正式评审NOT_RUN，历史样本因评审链路缺口排除；FIRST_LIFE/BETA不升级。主线修复起点47d77cb3d0fee503564dcf701a444bba8286c9c3；最终commit由Git读取，避免自指。
