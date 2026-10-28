# S2 长期保持度 · 并入 First-Life

这是现有First-Life的部署/体验验收项，属于S2 Advanced Growth及集成资格补证据。
不修改固定63criteria或现有Foundation资格；不新增记忆真相库。原37e6948交付镜像/
APK/封条仍有效，本补充是宿主验收工具，不重建已交付发行包，不自动部署。

## 必须分开的四项

| 项目 | 有效证据 | 不足以证明 |
|---|---|---|
| 已保存 | 原MemoryService提交后的memory/evidence/事件ID、持久化与来源有效性 | 聊天屏幕上曾出现、模型说“我记住了” |
| 已检索 | 本次原ContextAssembler候选与最终context的source memory IDs；分别记录候选命中与最终入选 | 数据库行存在、手工强塞required_memory_ids |
| 准确回忆 | 实际回复与有效来源核对：事件、参与者、先后及不确定性正确；真人复核语境 | 检索命中、离线字符串读取、模型自评分 |
| 无法回忆 | 实际问答未回忆/错忆，区分未保留、源撤回、隐私拒绝、候选未命中、context未选中及生成错误；原因不明记UNKNOWN | 未开展测试不能记失败；来源已撤回不应强行恢复 |

重要共同经历应在**原有同意保留路径**产生真实来源，检查是否形成持久Memory/
Experience/Person-Self关联，以及以后是否影响表达或行为。不能为验收编造经历，
也不能把普通临时聊天自动全部升级长期记忆。模型生成故事不算生活史。

## 宿主容量采样

以原owner UID及其同一容器命名空间运行。工具只请求原control.sock的storage视图，
复用原durability.profile和StorageGuard窗口/配置；身份/lineage只读取原metadata。
不打开第二写者，不调用模型、不查询记忆正文、不checkpoint/清理，不在Subject库
记日志。输出仅数字和身份绑定，为0600新建宿主证据文件，不能作为新记忆输入。

将补充工具放到已验证的非敏感交接路径，用**容器中合格私有Python**运行：

```sh
/opt/nana-core/runtime/core-releases/3665d39fe0aeff9831721d4bfd1bfba0b8386a2b/.venv/bin/python \
  -I -B /approved-handoff/memory_retention.py \
  --core-root /opt/nana-core/runtime/core-releases/3665d39fe0aeff9831721d4bfd1bfba0b8386a2b \
  --home <已有正式home> --output <宿主私有证据目录>/sample-01.json
```

路径尖括号由既有受控宿主配置提供，不创建identity或凭据。后续同一命令加
`--previous <证据目录>/sample-01.json`，输出新sample-02.json。runtime未运行、
owner/权限不符、损坏窗口、跨identity/lineage或时间倒退均停止，不降级为绕锁读写。
数字文件也不要公开上传；本仓库只提交合成DEV证据。

记录logical DB、物理DB/WAL/SHM、可复用页、privacy anchor、剩余磁盘、原guard状态/
门槛，以及两次**真实UTC采样**的净增长/小时。WAL checkpoint可使物理占用下降，
不能据此判断记忆删除；短时增长率不能外推一年保持度。本项不覆盖日志、备份和
媒体目录的全部宿主占用；它们继续纳入既有运维容量核账。

StorageGuard原硬上限/增长上限、跨重启停止锁存、损坏fail closed及不自动删历史
的机制继续有效。接近容量时沿原管理/备份流程处置，不自动丢弃共同经历。

## 随既定体验开展，不另建长期任务

- T0：只选少量用户同意保留的真实共同经历，记录不含正文的事件/记忆引用；核已保存。
- 同次对话：在不提供答案的普通问题中核检索与真实回复；没有新付费授权不调用模型。
- 既定安全重启后：同identity/lineage核存储、检索和回复；不为测试额外重启生产。
- 次日、约一周及以后自然回来时：记录实际UTC间隔、是否给提示、期间干扰量和来源
  生命周期，按同样四项核验。预约窗口不是已完成时长；虚拟时钟不是实际经过。
- 纠错/撤回场景：旧说法不应继续当事实；合法隐私拒绝与遗忘分别记录。重要经历
  仅“保存但检索不到”必须作为真实体验问题继续定位，不能被存储PASS掩盖。

最小记录字段：case_id、真实/合成来源等级、identity/lineage、source/memory IDs、
实际保存/提问UTC、重启owner epoch、间隔、保存/候选/最终context是否存在、回忆
结论（NOT_RUN/ACCURATE/PARTIAL/UNABLE/INCORRECT）、原因/UNKNOWN、人工复核状态。
默认只留非敏感元数据，不保存用户问句、答案、预期事实正文或可逆内容哈希。

当前没有真实宿主访问、正式共同经历或真人跨日回访，真实长期陪伴=NOT_RUN。
本轮离线/受控重启测试只能证明对应机制，不升级First-Life/Beta。
