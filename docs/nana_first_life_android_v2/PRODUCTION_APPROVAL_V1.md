# First-Life Android V2 · 单次云端接入审批包 V1

2026-10-26 · GLOBAL_STAGE H / Advanced Growth · DRAFT / NOT_APPROVED / NOT_EXECUTED

这是99b93d4已验收成果的后续交付。原SDK、隔离Docker、Core/Web/APK验收继承，不重跑；本文件不构成生产授权，不创建身份，不触碰旧服务。正式审批以本包的最终固定版本为准，宿主参数补齐后一次提交，不按代码小步骤反复询问。

## 推荐部署与当前事实

唯一推荐：独立Debian13非root Docker，UID/GID999；宿主`/srv/nana-core/{runtime,data,logs,backups}`分别映射容器`/opt/nana-core/`同名目录。runtime只读，data/logs/backups私有0700可写。512MiB、1.5CPU、64PIDs、cap_drop ALL、no-new-privileges、受限tmpfs和日志轮转；不挂docker.sock、宿主根、AstrBot、QQ、Iris目录或用户设备。Compose默认不启动。

复用原SDK归档SHA256 `1dbbcf46f6a16ab41deac96657a43a8fcecbba6ab7dea1d0113a84b2c8285b27`，不重编译、不搬到Ubuntu系统Python。Core源dbfb37e、Web和APK均复用已验收工件。已验收开发镜像ID `sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee`。若云端重新构建产生不同ID，只能声明新候选，核对实际工件/最终宿主挂载，不冒称与开发镜像字节相同。

宿主BFF仅`127.0.0.1:18765`→容器18766→原BFF loopback18765。推荐在既有Tailscale Serve上新增**独立HTTPS8443监听**转发到宿主18765，tailnet仅允许指定用户/手机；现有HTTPS根路由及6199保持原状。不得用容器内的127.0.0.1代替宿主，也不得开启Funnel或公网控制端口。

当前开发会话没有云端SSH/委托执行/VPN绑定，未连接真实宿主，也未在云端创建`/srv`。云端奈奈可以提供脱敏元数据及按最终批准的命令协作；不会将AstrBot容器内docker.sock/根挂载当作Codex已获宿主权限。当前无任何新Provider调用或凭据搜索。

## 一次审批前必须补齐的事实（不是重复环境验收）

由宿主操作者填入同一审批记录，只提供元数据，不交密码/密钥/私人正文：

- 实际安全执行通道及宿主标识；`/srv/nana-core`是否存在、挂载/剩余空间/所有者，若已有数据立即停止覆盖。
- 既有Tailscale Serve的脱敏配置摘要、真实tailnet HTTPS名称、8443是否空闲、指定手机访问策略；提供增加监听与删除该监听的精确差异，不动原根路由。
- 各旧writer的**实际启用配置键/版本/恢复命令**及Docker重启、插件热重载、定时任务等复活路径。不能仅根据插件名字猜关停命令。
- 操作者执行前保存的配置回滚快照与校验指纹（快照留宿主私有目录，不上传）；私人DB备份/读取/迁移不在当前准备授权中。
- 再确认宿主没有新增canonical Core，正式home不存在；若状态已变化停止genesis，按真实lineage核账。

这些实际值尚未提供，因此本包是可审查草案，不能称“生产部署已就绪”。缺值时只暂停对应步骤，不反复要求选Docker或路径。

## 建议一次确认的执行范围、影响与回滚

| 操作 | 审批后执行内容与影响 | 失败或撤回后的处理 |
|---|---|---|
| A 无主体宿主落地 | 从非敏感交接归档构建/导入固定镜像；新建空的/srv四目录；部署文件，不启动serve、不创建Subject | 保留诊断；仅移除本次新建的空目录/候选部署文件，不递归删除data/backups，不触碰已有内容 |
| B 私有HTTPS | 增加tailnet独立8443监听与指定客户端访问策略；不改6199或现有根路由 | 精确删除本次新增监听/策略差异，原服务配置不变；TLS/路由不符直接停止 |
| C 唯一genesis（尚未授权） | 明确绑定canonical-plan摘要，在不存在的正式home创建一次canonical identity，仅Legacy Source Link；不导入私人正文/继承旧UUID/创建执行Grant，暂不激活长期writer | 失败留下隔离证据，不重试创建、不覆盖、不删除已分配身份；停在人工核账门 |
| D 旧writer fence与激活（尚未授权） | 按已核对的精确清单停用旧决策/记忆/主动发送writer及复活路径；尽量保留AstrBot/NapCat传输入口，不重建旧容器；然后记录原Core激活事件并启动唯一新owner | 先停并fence新Core，确认owner失效、UNKNOWN/回执保留，再由操作者恢复旧配置；旧新不得同时激活。若实际必须重启QQ/AstrBot，当前范围禁止，停止并修订同一审批包后再决定 |
| E APK配对与有限App canary | 私有HTTPS登录，一次性配对手机；默认Reader+Conversation，Host管理单独显式角色。不开放手机控制，不自动接管QQ | 撤销该设备/会话，停用新增入口；保留同一Subject，退出canary不创建替代主体 |

C和D分别消耗现有Core要求的genesis/activation收据，但可来自**同一份最终人工审批**，分步绑定plan与实际生成的ID/lineage；不得在审批前伪造approved=true、UUID或fence成功。C若完成D未完成，主体保持未激活。

D阶段会暂停旧QQ自动决策、回复及主动行为；新Core的真实QQ投递仍不默认批准，因此可能出现QQ回复空窗。未经宿主精确变更确认，不承诺停顿时长；若要求旧QQ始终照常回复，则暂缓D，不能激活第二个正式writer。

旧writer至少包括astrbot.agent、iris.writer、livingmemory.writer、proactive.social、bili.act-pump、selfevolution.cron、legacy.command-control；平台消息只是观察，不产生管理权限。只在实际fence核验通过后激活新主体；否则不冒充唯一owner。

## 明确不并入默认审批的范围

真实私人Iris/聊天历史导入、QQ/B站实际发送、生产流量全量切换、日常长期付费模型额度、真实设备控制、bwrap提权均默认不批准。可在同一审批表勾选未来拟议范围，但在数据类别/保留删除/费用/回滚未明确前不执行，不因“批准部署”推导这些权限。

当前Provider调用为0。首次真实自然交流需要宿主显式FD/Resolver和单独写明的新有限次数/费用/隐私授权；不沿用历史Key。UNKNOWN无重试、无fallback。没有真实模型只能验证连接/源投影，不能称自然交流PASS。

## 切换前门与中止条件

正式配置必须绑定生产realm、实际ID/lineage、原Core完整性摘要、用户时区（建议Asia/Shanghai）和独立host配置，API/APK不得创建身份或直接改Store。SDK/端口/权限原结果不再重跑整套；只核对**新真实宿主**的挂载、私有HTTPS、单owner、启停和备份实际状态。

安全回执、日志轮转、磁盘阈值及UNKNOWN保持原约束。现有256回执容量是已披露staging限制：首次canary最多20个写操作（含管理操作）且不得自动清空回执；长期使用前必须完成可证明幂等的归档/扩容，不能靠删历史绕门。后台push、实机Keystore/通知、人类自然度及72h尚未资格，不将启动成功升级First-Life/Beta。

出现已有canonical、另一owner、源包/镜像不匹配、未知网络暴露、UID/挂载异常、旧writer未彻底fence、需要未批准服务重启、任何UNKNOWN效果或预算不明确时停止相关操作。只读核验和无副作用准备可继续。bwrap继续BLOCKED，其他原有正常能力保留。

## 给云端奈奈的当前交接边界

目前只交付非敏感运行时部署材料/哈希/API与APK。可以在既有`/AstrBot/data/_nana_core_handoff/`保管这些材料；**不得**在那里创建Store/身份/私人DB/生产备份。宿主实际操作等最终批准及安全通道，不依赖旧奈奈nohup/cron托管新Core。

审批完成后的证据至少记录：批准包指纹、操作者、宿主/镜像/挂载元数据、genesis及激活收据、fence及复活路径验证、单owner、私有HTTPS、停止/恢复、备份引用与所有UNKNOWN。只保留脱敏证据，不收集私人正文或密钥。
