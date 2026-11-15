# QQ official compatibility proposal

[源码提案，2026-11-14] C先实现独立 `OfficialQQAdapter`、本地签名捕获侧车与 `OfficialQQHTTPTransport`，复用现有QQ工作流/Grant/Kernel。没有新的主体、记忆库、授权者或主观决策。供A/B合并审阅，不代表生产切换。

最小增量：原ReplyWindowBinding平台枚举增加 `qq.official`；QQChannelBinding增加默认onebot且旧序列化省略的backend；官方分支允许原生opaque peer/message ID，OneBot仍严格数字；原配置/surface/权限/事件入口按可信host配置区分后端。原C、D、Store表、Memory、Grant及旧OneBot动作数据不改。官方事件ID和会话ID以摘要适配原长度边界，保留原生来源，昵称不参与合并。

官方C2C/group没有已资格独立回读：ACK保留，但Verify=INCONCLUSIVE，原Kernel记录UNKNOWN并禁止自动重试。不拓宽原delivered-memory证明。删除官方连接配置、停用独立官方入口后可回退旧二进制；含official配置不得直接交给旧reader。用户明确授权的非破坏性增量在C分支实现，影响A/B契约的破坏性变更仍需另行确认。

依据：[AstrBot v4.28.0官方适配接口](https://github.com/AstrBotDevs/AstrBot/blob/v4.28.0/astrbot/core/platform/sources/qqofficial/qqofficial_platform_adapter.py)与[botpy REST routes](https://github.com/tencent-connect/botpy/blob/master/botpy/api.py)。AstrBot为AGPL-3.0，仅独立调用其公开事件接口；不复制其实现。平台能力、授权和实际账号行为须另验收。

## 待 A 协作的私人平台来源和媒体行动

当前原 MemoryService 只允许公开直接观察，私人长期保存限于显式同意的对话来源。订阅动态同时包含私人的关注关系，不能标成 PUBLIC，也不能伪装成用户对话。C 已保留独立适配草稿；建议增加受明确授权和撤回约束的私人平台观察来源，带账号、对象、来源引用和隐私，复用原 Memory/Subject 及现有撤回机制。此提案未改变现有来源契约。

QQ 非文本发送还需要原 C 能明确选择具体媒体和来源引用，并由原 Manager/Grant/Kernel 审批；仅由连接器根据文本猜选文件会绕开主体决策。建议在原 C 行动候选中增加可选、版本化的媒体引用，并对来源撤回与独立回读定义约束。当前实装只支持受治理的文字发送。
