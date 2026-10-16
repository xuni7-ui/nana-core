# Eyes / Hands — FUTURE_STAGE，当前不接真实设备

## 已固定、实际读过的三个方向

| 项目 | 真实source机制 | 对Nana价值 | 必须拒绝的跨界 |
|---|---|---|---|
| OpenWatari | [src/jarvis/shared/protocol.py](https://github.com/max286674-cpu/OpenWatari-Jarvis/blob/b6a1924bc35daaf9520ac6e9fc8ee8c7ef7b4c10/src/jarvis/shared/protocol.py#L15) hello/device/session/transcript/stream/barge；remote_brain thin edge | local音频、central subject、device context、取消信号 | remote_brain:89断线后local independent agent fallback不可直接借；没有exclusive authority takeover证明 |
| Comma | [systems/connector/salix-connect/connection_session.go](https://github.com/AFK-surf/Comma/blob/ba4f55db1bf038a9246a9f71a7b5059cd91853f1/systems/connector/salix-connect/connection_session.go#L36) transport generation隔离；device access passive discovery+recheck；IFC receipt | session防串线、discovery≠permission、cancel/drain、observation vs configured readiness | AGPL代码不copy；Lean/TLA标签不是全栈安全证明；不引入其多语言运行体系 |
| OpenHands SDK/Canvas | [openhands-sdk/openhands/sdk/event/llm_convertible/action.py](https://github.com/OpenHands/software-agent-sdk/blob/12e967664c2353f4cb85dd27da04ade035ff078c/openhands-sdk/openhands/sdk/event/llm_convertible/action.py#L24) ActionEvent/toolcall与Observation；confirmation policies、remote conversation/eventlog | tools隔离、typed receipts、approvalUX、reconnect/audit | LLM risk score≠Grant；NeverConfirm不是合法许可；Canvas本地server可全文件访问，不能当沙箱 |

OpenHands当前root主要是Canvas，而canonical agent server在另repo `software-agent-sdk`，因此追加读后者有明确理由，不堆项目数量。
OpenWatari唯一public命中可能是fork，权威上游身份UNKNOWN；报告只针对实际fixed repo，不称官方安全认证。

## 未来统一接线

Cloud/PrimaryRuntime（唯一subject writer）→受认证的thin device port→device capability inventory / session epoch→source-backed Observation / Action receipt。
AstrBot/QQ、B站、Desktop、Android、Game、Browser、Camera均是edges，不是多个Nana。

- Inventory只描述available/observed capability，不发Grant；发现设备不能自动允许读取内容。
- observation带source/time/coverage/privacy/device identity；原对象先sanitizer，不把screen/prompt/rawcredentials塞Core。
- command绑定intention+Action+Grant+runtime epoch+device/session+idempotencykey，回传Attempt/Observation可核验；transport ACK不是实际effect。
- disconnect / late receipt：UNKNOWN+reconcile，不从另device盲重试；edge失联允许缓存有限observations，不能新造权威主体。
- perception policy按domain和owner过滤：便利read不等于private允许、playful关系不等于数据授权。
- kill switch对actual dispatch重检，保留wanted vs blocked历史；不要用隐藏失败伪装没有意图。

当前没有执行这些路径，没有安装插件、启动agent server、配置VPN/账号、读真实屏幕/文件/私人memory，真实E/G保持NOT_RUN。
