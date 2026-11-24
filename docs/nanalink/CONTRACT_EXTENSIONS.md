# QQ official compatibility proposal

> 历史提案，保留用于追溯；私人平台来源、QQ 媒体候选和官方后端已有后续实现，不能把下文早期缺口当作当前状态。现役能力与限制见 [NanaLink 入口](README.md#现役平台能力与限制2026-11-24)。QQ 可信撤回到原 owner 删除闭包仍是待 A 接线的独立缺口。

[源码提案，2026-11-14] C先实现独立 `OfficialQQAdapter`、本地签名捕获侧车与 `OfficialQQHTTPTransport`，复用现有QQ工作流/Grant/Kernel。没有新的主体、记忆库、授权者或主观决策。供A/B合并审阅，不代表生产切换。

最小增量：原ReplyWindowBinding平台枚举增加 `qq.official`；QQChannelBinding增加默认onebot且旧序列化省略的backend；官方分支允许原生opaque peer/message ID，OneBot仍严格数字；原配置/surface/权限/事件入口按可信host配置区分后端。原C、D、Store表、Memory、Grant及旧OneBot动作数据不改。官方事件ID和会话ID以摘要适配原长度边界，保留原生来源，昵称不参与合并。

官方C2C/group没有已资格独立回读：ACK保留，但Verify=INCONCLUSIVE，原Kernel记录UNKNOWN并禁止自动重试。不拓宽原delivered-memory证明。删除官方连接配置、停用独立官方入口后可回退旧二进制；含official配置不得直接交给旧reader。用户明确授权的非破坏性增量在C分支实现，影响A/B契约的破坏性变更仍需另行确认。

依据：[AstrBot v4.28.0官方适配接口](https://github.com/AstrBotDevs/AstrBot/blob/v4.28.0/astrbot/core/platform/sources/qqofficial/qqofficial_platform_adapter.py)与[botpy REST routes](https://github.com/tencent-connect/botpy/blob/master/botpy/api.py)。AstrBot为AGPL-3.0，仅独立调用其公开事件接口；不复制其实现。平台能力、授权和实际账号行为须另验收。

## 待 A 协作的私人平台来源和媒体行动

当前原 MemoryService 只允许公开直接观察，私人长期保存限于显式同意的对话来源。订阅动态同时包含私人的关注关系，不能标成 PUBLIC，也不能伪装成用户对话。C 已保留独立适配草稿；建议增加受明确授权和撤回约束的私人平台观察来源，带账号、对象、来源引用和隐私，复用原 Memory/Subject 及现有撤回机制。此提案未改变现有来源契约。

QQ 非文本发送还需要原 C 能明确选择具体媒体和来源引用，并由原 Manager/Grant/Kernel 审批；仅由连接器根据文本猜选文件会绕开主体决策。建议在原 C 行动候选中增加可选、版本化的媒体引用，并对来源撤回与独立回读定义约束。当前实装只支持受治理的文字发送。

### 2026-11-15 A 基线复核与最小契约草案

A `383a51a` 的 `Provenance` / `MemoryService` 相对 `87c32b3` 无差异：非公开直接平台观察不满足 `PUBLIC_DEVELOPMENT_INGRESS_ONLY`，既有 `CONSENTED_INTERACTION` 仅接受列举的对话命名空间与类型。将订阅关系改标 PUBLIC 或冒充 USER_STATEMENT 都会破坏来源和隐私。C 的独立动态解析可先产生 PERSONAL 事件；进入长期记忆须 A 审阅以下增量：

- 可选、版本化的 `CONSENTED_PLATFORM_OBSERVATION` 来源：只允许已验证平台账号、绑定/范围、显式私人读取与保留同意引用、原始事件稳定引用及来源时间；不通过昵称合并身份，不授予动作权限。
- `MemoryService` 验证精确来源命名空间、同意引用和原 owner 绑定；创建原证据/记忆依赖而非新 Store。撤销同意或来源后，既有撤回/依赖闭包阻止后续引用与重采集；无同意时仅保留不含正文的短期传输元数据。
- 原主体通过已有 WORLD_EVENT 获得一次源支持的机会，可忽略、推迟或自行选择阅读；来源内容不得当成用户命令。需测试跨账号隔离、合规读取、撤回后不可重放及旧序列化兼容。

QQ 媒体：原 `RealizationTarget` 只表达 capability/operation/resource，不能表达由 C 选中的具体媒体。建议 A 在原候选中增加可选的受限媒体来源引用和绑定目标；C 的独立端口仅在原约束结果、行动目标、源仍有效、Grant 和原预算均匹配时执行；未支持独立回读仍保持 UNKNOWN。旧无媒体候选的序列化与行为必须保持一致。此为提案，不是已获得的媒体行动权限。
