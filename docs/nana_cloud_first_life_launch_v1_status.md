# Cloud First-Life Launch V1

## CURRENT — CLOUD FIRST-LIFE LAUNCH V1 / DEVELOPMENT
[源码/远端实测2026-10-20] Base b06e1e72f63a481ba349c23043c4027f137b9876 本地/远端一致；
新分支dev/nana-core-cloud-first-life-launch-v1-codex。GLOBAL_STAGE H不变，继承CDL/RAE，不重做PASS。
Phase A先定位增长：post-handoff开发库DB约12.6MB；events约6.8MB，artifacts约1.68MB；
queue full-row replay audit是可解释增长，不能以删除audit/provenance/UNKNOWN/隐私journal降数字。
实现host-local size/rate guard + PASSIVE checkpoint + 分类型numeric profile；超限停止writer，不改原愿望；
host guard窗口跨重启保留，corrupt fail closed，不新增Store/SubjectLoop/schema。资格尚在进行。
环境当前ready但secret/variable/identity bindings为空；Phase B等待新的安全FD/Resolver与有限付费批准；
历史Provider UNKNOWN仍PARKED retry0/fallback0。Human review/production inventory/production切换仍未授权/未运行。
继续可独立的人工评审入口、单writer dev rehearsal与24h隔离staging准备；无真实社交/private data/production。
旧bundle untracked/untouched/not-input。下方CURRENT为历史保留。

First-Life checkpoint [源码/实测]：size/rate guard、restart latch、PASSIVE checkpoint、numeric storage view、
同Runtime私有chat client、immutable结构化human-declared review、实际3进程writer交接/回滚工具均已实现。
新focused6 passed2.54s；相关first-life/cloud25 passed16.64s（该次尚未加入最后client case）；
真人review NOT_RUN，测试评分不作为human证据，不自动升级readiness。下一步actual bounded soak与24h dev runner。

## CURRENT CHECKPOINT — FIRST-LIFE / TECHNICAL DEV QUALIFIED, EXTERNAL GATES PENDING
[实测2026-10-20] Base b06e1e72f63a481ba349c23043c4027f137b9876；GLOBAL_STAGE H。
Frozen executable645899b32220e66a702e75d59a279a3a9685693f；branch dev/nana-core-cloud-first-life-launch-v1-codex。
已实现/测试：host-local DB family/rate guard、跨重启STOP latch、PASSIVE checkpoint、只读numeric storage profile；
原Runtime私有chat client与不可变human-declared评分入口，测试评分不冒充真人评审。
Focused6 passed2.72s；最终full1274 passed/12 skipped/0 failed280.58s（11 live-screen+E12保持门）。
实际三顺序进程交接/新B8回滚epochs2→3→4、同identity、旧writer fence；不是实际production rehearsal。
90.1745秒有界运行42actions/14owned effects、SIGKILL恢复/backup-delete/B8迁移均通过；短run不是24h。
独立24h staging已真实启动，固定detached worktree645899b；根/workspace/nana-staging/first-life-24h-01；
progress.json为实时运维投影；目标86405秒，尚未完成时必须RUNNING_NOT_QUALIFIED，不升级24h或Beta。
managed dev host长期存续未attest；源码冻结，停止/失败不自动重启，不重复effects。
Provider新调用0；当前无新安全FD/Resolver/付费范围，历史one UNKNOWN parked retry0/fallback0；不使用旧聊天key。
Human naturalness/shared-life NOT_RUN；production inventory需新授权，cutover approval尚未到请求门；canary/72h NOT_RUN。
FIRST_LIFE_EXPERIENCE_READY=NOT_READY；CLOUD_DAILY_LIFE_BETA_READY=NO。
One original Subject/Store/Loop/Runtime owner；schema13/43表，新表0/依赖0；main/R045/production/private data不变。
下一入口：安全新provider绑定及有限付费批准；继续观察真实24h结果后另行收口，不能把后台启动称任务全完成。
报告/status/quickstart/production_preparation及小型证据见docs/nana_cloud_first_life_launch_v1_*。
下方CURRENT为保留历史检查点。

### Qualification fields at handoff checkpoint
BRANCH = dev/nana-core-cloud-first-life-launch-v1-codex
BASE = b06e1e72f63a481ba349c23043c4027f137b9876
EXECUTABLE_HEAD = 645899b32220e66a702e75d59a279a3a9685693f
HEAD / PARENT / REMOTE_EQUALS_LOCAL = read Git at handoff; no self-referential SHA embedded
DURABILITY = IMPLEMENTED / TESTED / BOUNDED_PROCESS_QUALIFIED; long-duration not yet qualified
DB_GROWTH = EXPLAINED_APPEND_ONLY_HISTORY; GUARDED_NOT_PRUNED
24H_STAGING = RUNNING_NOT_QUALIFIED
REAL_TEXT_PROVIDER = BLOCKED_NO_NEW_SAFE_SOURCE_AND_PAID_SCOPE
REAL_PROVIDER_CALLS = 0 NEW
REAL_PROVIDER_USAGE = NONE_NEW
REAL_PROVIDER_COST_STATUS = NONE_NEW_INCURRED; HISTORICAL_UNKNOWN_BILLING_UNKNOWN
HISTORICAL_UNKNOWN = PARKED_NO_RETRY_NO_FALLBACK
HUMAN_NATURALNESS = NOT_RUN
SHARED_LIFE_HUMAN_REVIEW = NOT_RUN
FIRST_LIFE_EXPERIENCE_READY = NOT_READY
PRODUCTION_INVENTORY = NOT_AUTHORIZED_NOT_RUN
CUTOVER_REHEARSAL = PASS_DEV_ACTUAL_PROCESSES_SYNTHETIC_LEGACY_ROLE
PRODUCTION_APPROVAL = NOT_REQUESTED_PREREQUISITES_UNMET
PRODUCTION_CANARY = NOT_RUN
72H_QUALIFICATION = NOT_RUN
QQ_SURFACE = DEV_SHADOW_ONLY
BILI_SURFACE = DEV_SHADOW_ONLY
REAL_SOCIAL_SENDS = 0
SINGLE_SUBJECT = PASS_PER_REFERENCE_LINEAGE
SINGLE_STORE = PASS_PER_REFERENCE_LINEAGE
SINGLE_RUNTIME = PASS_PER_REFERENCE_LINEAGE
SINGLE_WRITER = PASS_DEV_REHEARSAL
BACKUP_RESTORE = PASS_DEV
ROLLBACK = PASS_DEV_FRESH_B8_LINEAGE; PRODUCTION_NOT_RUN
UNKNOWN_NO_BLIND_RETRY = PRESERVED
CLOUD_DAILY_LIFE_BETA_READY = NO
MAIN_CHANGED = NO
R045_CHANGED = NO
PRODUCTION_CHANGED = NO
PRIVATE_DATA_USED = NO

Each synthetic fixture/reference Subject is independent and sequentially fenced; separate test stores do not constitute a second brain for the same authoritative instance. Human-review metadata is host-local and never auto-promotes these gates.

### Provider authorization update — credential binding still blocked
[用户显式授权 + 环境实测2026-10-20] 新资格目标DeepSeek / https://api.deepseek.com / deepseek-flash，
OpenAI-compatible，PUBLIC/PROJECT only，最多20真实调用、$1等值上限；PERSONAL/SECRET不授权。
用户声明Secret已在个人保险库，名称DEEPSEEK_API_KEY。环境实时observations_current=true/revision281，
secrets=[]、runtime_variables=[]：尚未绑定到当前任务。工具仅支持environment_status，无配置修改工具。
因此BLOCKED_NO_CURRENT_ENVIRONMENT_SECRET_BINDING；新真实调用0；模型/endpoint尚未live验证。
不搜索环境/历史key，不读个人保险库原文，不用明文文件；已请求用户通过环境配置绑定并审核。
绑定ready后仅从显式宿主安全源→内存pipe/FD→现有ExplicitFDResolver，沿原预算/Privacy/UNKNOWN合同。
历史TianToken UNKNOWN仍PARKED，禁止重放或fallback。此前“未获付费范围”在本时点被上述有限授权取代。

Current REAL_TEXT_PROVIDER = BLOCKED_NO_CURRENT_ENVIRONMENT_SECRET_BINDING; limited scope authorized, no live call.

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
