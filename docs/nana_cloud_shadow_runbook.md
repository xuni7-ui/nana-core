# Nana 第一次真实云端只读 Shadow 操作手册

**本手册未执行。** 本次仅开发；生产调用/修改/私人记忆/secret值/外部消息均0。执行本手册必须取得姐姐新的明确授权：一次选定服务器的只读metadata核对、受控包复制/挂载、一个临时只读事件hook、一个非私人probe及固定短窗口。不得把本手册当现有生产许可。

最小首次目标不是批量私人记忆迁移：先证明同宿主一个事件→Evidence→同一Core Identity→Decision draft→SHADOW_BLOCKED→关闭hook→恢复纯legacy。Iris只导出**合成探针快照或另明确授权的小范围hash-only快照**，不输出正文/secret。若姐姐只授权无私人数据，选前者，不读真实私人DB。公网和真实模型不是首次接线必要条件；E12继续NOT_RUN。真实自然语言shadow决策仍使用明确fixture，不冒充语义验收。

## STEP 0 — 指纹、备份与边界冻结
- 本地已审核开发分支完整SHA、wheel sha256、源指纹及许可证边界；不从main自动更新、不触发CI部署。
- 操作者确认实际host/plugin路径、现有业务执行入口、可用热加载hook机制、同进程Python/SQLite兼容性；当前文档路径都是历史线索，不能硬编码生产路径。
- 如需读取真实DB备份，必须另明确批准范围。由现有受信备份机制产生**一致且无待合并WAL的冻结备份**；不要cp活跃.db冒充一致快照，不对live DB使用immutable；原DB/FAISS不被工具打开或修改。
- 留已有宿主hook/config指纹及恢复方式；Core自己的新shadow目录权限0700。无生产DB写、不改旧发送逻辑/owner/grants/model配置。

## STEP 1 — Metadata cloud preflight
由授权操作者使用host现有Python运行 `python -m nana_core.integration.preflight --path astrbot=<实际插件目录> --path iris=<实际Iris目录> --path shadow=<已批准shadow目录>`，只stat与包metadata，不读secret/config/chat/DB。
- Python<3.12、SQLite<3.51.3、Pydantic不兼容→BLOCKED，立即停止接线，**不自动安装/升级/重启宿主**。
- 未知插件runtime版本/container/hook/frozen snapshot→UNKNOWN；人工根据只读metadata补证，不能写成PASS。
- 无可确认同进程热加载hook→BLOCKED这次启用；不得擅自重启AstrBot解决。安装新依赖、宿主升级/重启必须另授权。

## STEP 2 — 放置审核过的 Core 包
只复制固定SHA的wheel/解包目录到批准的独立readonly包目录，使用已有兼容依赖，**不pip访问网络自动装依赖**。不覆盖AstrBot/Iris/B站源码，不启动第二完整Runtime/daemon。不安装永久服务、cron、systemd或docker。

## STEP 3 — 只读 Iris export
默认先用同schema的synthetic snapshot。未来若另授权真实小范围快照：`python -m nana_core.integration.exporter --snapshot <已批准冻结副本> --table memories --source-identity <opaque稳定来源id> --frozen --mode hash-only`。
- 固定表reader支持memories/nodes/edges；L1/profile/流水/index仅操作者提取的JSON envelope，不能把未知native wrapper当已支持。
- 100records/8MiB超限BLOCKED，不悄悄截断。保存manifest/count/hash/来源/时间/关系到本机批准目录，不上传Git。include/redact需明确的数据授权，hash-only低熵hash也可能被推测，不能称匿名化。
- 原synthetic-only IrisImporter未放开production scope；hash-only bundle经ShadowBridge.capture_export成为UNASSESSED证据，不把hash当原文事实或启用Strategy/Grant。

## STEP 4 — Observation Shadow
- 使用当前宿主**经过人工审查的临时observer hook**，只选一个指定platform/conversation/event，产生HostEvent显式sender/event/时间/rawref/reply/附件metadata；不调用消息发送、不下载附件。
- 建立单个Store新shadow DB，第一次记录Core identity_id，此后只恢复同DB。设置RuntimeIntegrationContext(mode=SHADOW,external_execute=False,production_budget_enabled=False)。不把Iris persona_id当Core身份。
- 同进程持有ShadowBridge+HostShadowSession。操作者显式conversation allowlist、expires_at_us（建议10分钟）、max_events=1；hook必须**先过滤scope再构造含正文HostEvent**。Session持久quota，重启不能借新实例多读事件。
- fixture ShadowDecision只用于工程链路，model_kind=fixture；不接受real_model文本标志替代账本。无ActionKernel/liveport，无授予生产Grant。临时hook的AstrBot register/unregister API须现场版本验证；仓库pure adapter不是已安装的AstrBot插件。

## STEP 5 — Memory reconciliation
核对选定bundle数量/类型/opaque source/hash/原时间/覆盖程度/重复和关系；hash-only不可测试正文记忆理解，UNKNOWN保留。原证据不删、不升级summary/ledger标志，不改Iris memory authority。未授权私人数据只对synthetic probe对账。

## STEP 6 — Decision shadow
对同一probe记录legacy观察输出（可用性UNKNOWN保留）与Core fixture draft，用reconcile产生本地JSON/md。比较interpretation/retrieval/evidence/goal/actioncap及input差异；**差异不等于优劣**。没有真实legacy/model输出则标fixture/UNKNOWN。调用execute应SHADOW_BLOCKED；actions/attempts/production预算/Grant/Strategy都应0。

## STEP 7 — 固定窗口观察
仅上述1个probe/10分钟，重复投递及关闭/重开Store确认identity/evidence/draft不重复。health只从已打开shadow Store读metadata。若adapter异常、未知时间、业务延迟或resource异常：停止hook，保留failure/UNKNOWN，不能重试外部动作或干扰旧业务。

## STEP 8 — 验收与一键回滚到纯legacy
保存本地验收：approved SHA、preflight、实际hook/host版本证据、source/count/time/hash、identity、重复数、draft、SHADOW_BLOCKED、现实副作用0、资源指标、UNKNOWN、关闭hook后的旧业务验证。

**回滚是卸载/注销该临时observer hook并关闭shadow Store**，保留独立shadow DB/证据，只取消包引用（不要删历史）；旧业务及Iris原DB从未换权，不需要反向迁移。配置默认enabled=false时不构造session，但已注册hook仍必须明确unregister，不以改环境变量假装卸载。保留一条人工可执行的现场unregister记录；无法证明可卸载则不启用。

## 下一阶段的单独授权边界
不默认执行execution/memory authority切换。必须另批准：旧所有发送/写入口epoch fencing、pending/UNKNOWN/irreversible核验、snapshot/Grant/Budget、handoff和rollback演习、有限Core write。E12真实模型、真实include私人与模型出网也分别核实既有端点/数据范围。不能以Shadow验收PASS绕过任何一项。
