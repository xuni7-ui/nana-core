# 当前接入更新

已在 `87f73d2` 上实现隔离开发网关 `nana-space-live/v1`，复用原 owner IPC 与 Inspector。操作与限制见 [LIVE_INTEGRATION](LIVE_INTEGRATION.md)。下文为 V1 契约核对历史；其中通用生产 Gateway、认证和流式订阅仍为 PLANNED，不代表本次开发会话已具备生产资格。

# Nana Core 接入契约

本轮默认 Demo；只读 Inspector JSON 导入是离线快照检查。**未连接真实 Core，也未新增 HTTP 执行接口。** 本文区分现有 Python/CLI 契约与未来浏览器网关。

审查源码版本：`e1679b2010c2d49148c9b99b096b9947dfdba8ff`。Precision V2 完成后需重新核对版本，不能把本文映射当作其最终承诺。

## 当前真实存在

| 接口 | 真实形态 | 当前前端范围 |
| --- | --- | --- |
| `nana_core.life.inspector.inspect(home, scope=…, entity_id=…, privacy=…, limit=…)` | 本地 Python，只读有界 metadata | 接受其 schema 1 JSON 的导入；不访问 DB |
| `python -m nana_core.life.inspector` | 本地 CLI | 由已获授权的宿主操作员运行；浏览器不执行 |
| `client.view('PROVIDER_SETTINGS')` | B10 application projection | 已有契约，浏览器网关 PLANNED |
| `client.provider_command(ProviderCommand(...))` | owner 内 typed transition、revision/CAS | 本 App 不调用、不提供假保存 |
| `client.view('PERCEPTION_SETTINGS')` / `PERCEPTION_STATUS` | B10 sanitized projection | 已有契约，浏览器网关 PLANNED |
| `client.perception_command(SourceCommand(...))` / `request_capture(...)` | owner 内 typed transition、独立 policy | 本 App 不采集真实传感器 |
| Surface / Continuity 前端投影 | 既有 application facade 与单 owner ingress | 未来按正式访问边界接入 |

Provider 契约见 [原文](../../../docs/nana_provider_capability_routing_v1_frontend_contract.md)，Perception 见 [原文](../../../docs/nana_h2_perception_ingress_v1_frontend_contract.md)，受控屏幕扩展见 [原文](../../../docs/nana_h2_live_real_screen_v1_frontend_contract.md)。这些文档明确是应用服务契约，并不自动提供对浏览器开放的 REST、SSE 或 WebSocket 服务。

`continuity/application.py` 的 `FrontendSession` 是进程内 client。通用 `FrontendProjection` 为 `{kind, derived: true, data_json: string, execution_authority: false}`；view kinds 包括 SELF、CONTINUITY、RELATIONSHIP、PERSONALITY、LIVING_SELF、MEMORY_SUMMARY、GOALS_COMMITMENTS_PROJECTS、RUNTIME、PROVIDERS、PROVIDER_SETTINGS、PERCEPTION_SETTINGS、PERCEPTION_STATUS、LIVING_RUNTIME、LIVING_JOURNAL、RESOURCE_STATE、OPEN_AUTONOMY、WORLD_LOOP。CONTINUITY 仍受独立 tier 约束。存在 view kind 不代表该实例已装配相应能力。

已有 `life/owned_surface.py` 的随机 nonce loopback `/observe` 只接收输入；202 表示 volatile admission，不能作为通用状态读取、配置或执行 API。

## Inspector JSON

仅在自己拥有且已授权的**开发实例**中，操作员可使用已有 CLI：

```bash
PYTHONPATH=src python -m nana_core.life.inspector \
  --home /absolute/path/to/authorized-dev-home \
  --scope project-work \
  --entity primary-user > inspector.json
```

该命令从仓库根目录运行；若使用已安装便携包，可省略 `PYTHONPATH=src`。路径、scope 和 entity 必须匹配该实例的真实授权；示例不是生产读取许可。本次开发没有运行此命令读取用户 Subject。Inspector 需要私有 home、已有 schema 13 Store 和当前 privacy journal，异常时失败关闭；它不会初始化、修复或提升 writer。SQLite 只读协调可能存在 SHM read mark，不宣称逐字节无读标记。

核心字段为：

```json
{
  "schema_version": 1,
  "derived": true,
  "read_only": true,
  "identity_id": "existing-subject-id",
  "as_of_us": 0,
  "coverage": "BOUNDED_METADATA_ONLY",
  "governance_visibility": "LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE",
  "execution_authority": false,
  "sections": {},
  "resources": null
}
```

每个 section 条目只有 `category`、`reference`、`state`、`record_id`、`as_of_us`、`source_memory_ids`。后端还可能携带 `private_activity`、`self_view`、`advanced_life` 等扩展；Nana Space 导入按白名单映射并丢弃 `self_view`/`advanced_life`，不能把未映射对象任意展开成私人内容。文件上限 2 MiB。空 section 或缺失资源是有限覆盖/未知，不是“不存在活动”或“资源为零”。

导入需拒绝错误版本、错误只读/derived 标志、执行权声明、错误结构及不合规字段；限制文件/数组/字符串规模，给出明确错误。来源时间显示为快照时间，不伪装实时连接。`LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE` 尤其表示：本地运维可见不等于可以向任何收件者公开；应用部署者仍需正式访问控制。

Inspector 只输出 PUBLIC/PROJECT 有界 metadata、WHAT/WHY 状态码与 source refs。它不提供原始 thought、模型内部文本、治理正文、完整转录、Provider Secret、设备 token 或私人意图正文；前端不尝试从引用反向抓取这些内容。

## Provider 与感知设置的边界

Provider 投影使用 `schema_version: 1`、`revision`、providers/models/routes、`storage_class: HOST_LOCAL_NOT_SUBJECT_MEMORY`、`execution_authority: false`。只展示 `secret_state` 的 AVAILABLE/MISSING/UNCONFIGURED，不接收或保存凭据。配置变更要求独立 `CONFIGURE_PROVIDERS` 和 `expected_revision`；`PROVIDER_CONFIG_REVISION_CONFLICT` 时重新读取，不静默覆盖。

Perception 投影同样 schema 1/revision/CAS；省略 adapter/resource ref、OS handle、路径和原始媒体。VIEW、CONFIGURE、REQUEST_CAPTURE 是不同策略。`REQUESTED` 只表示请求进入原 D 的机会队列，不能显示为“已拍摄”。启用源、Primary User 身份、Manager PASS 或 WATCH 都不能单独授予传感器权限。

已资格的受控 X11 test window 不等于用户桌面、真实手机或物理显示器。技术采集、语义理解、世界信念、Concern 与 C 判断要保留不同来源与状态。

## 未来浏览器 Gateway：PLANNED CONTRACT

当前没有假定 `/api/*` 已存在，也不自动探测远端。未来网关由受信任宿主实现，需满足：

1. 认证会话与 FrontendPolicy 决定可见 scope/privacy；Primary User 关系身份不自动成为 Manager 或配置权限。
2. 只通过现有 application owner 读取投影、提交 typed transitions；浏览器无 SQL、Store 对象、resolver、raw handle 或 Debug 绕过路径。
3. 返回版本化 envelope，包含真实 identity、active lineage/owner 证据、as_of、revision、coverage、来源模式及各模块可用性；不以 UI 自造默认值填补事实。
4. 执行请求区分候选、主体采纳、授权、dispatch、receipt、独立 Verify 与任务质量。采用幂等关联；UNKNOWN 后只允许核验/等待，不自动重发或 fallback。
5. 事件订阅携带 cursor/revision，处理断线、缺口、来源删除和撤权；新快照取代过期投影，不从浏览器缓存恢复 Grant 或已撤回内容。
6. Provider 配置、设备授权、私人内容披露、备份恢复等各自经过正式边界；Secret 留在宿主，不能放入 `VITE_*` 或 bundle。

`nana-space/v1` 是展示适配版本，不是新 Core 权威格式。正式 Adapter 应将真实投影映射到 UI DTO，并显式返回 UNAVAILABLE/PARTIAL/UNKNOWN。有权限且后端支持的功能才显示 CONNECTED；只读接入不能让执行按钮变成已授权。

## 从 Demo 切换的验收步骤

- 固定 Precision 最终源码和契约版本，重新审查字段及错误码。
- 在隔离测试实例实现宿主网关和会话权限；核对 identity 与唯一 active lineage，不 init 新主体。
- 接上只读投影，验证缺失、过期、冲突、隐私删除、断线及重连；关闭 Demo 混入真实页面的路径。
- 再分别接入现有 typed transitions；独立测试 revision conflict、撤权、UNKNOWN、核验与恢复。
- 取得真实设备/平台及外部效果所需授权和资格后，逐项升级成熟度。保留只读模式。

完成这些步骤后才能更新 `REAL_CORE_CONNECTED`，不能因为导入了 JSON、写了 URL 或前端按钮可点击就升级。
