# Nana Space V1 产品与验证状态

此表仅针对独立前端，不改变 Nana Core 的能力资格。当前为实施中检查点；最终实测由主实现会话更新，PENDING 不代表通过。

| 项目 | 当前状态 | 范围 |
| --- | --- | --- |
| UI_COMPLETE | PENDING | 10 个页面及交互实施后需桌面、窄屏与错误场景验收 |
| DEMO_WORKING | PENDING | Demo 场景、聊天、筛选及状态切换待实测 |
| CORE_ADAPTER_READY | PARTIAL | 已核对 Python/CLI 契约；Inspector JSON 映射/校验实施中；浏览器 Gateway 为 PLANNED |
| REAL_CORE_CONNECTED | NO | 没有真实 Core 会话、网关或生产连接 |
| MOBILE_QUALIFIED | PENDING_SIMULATION / PHYSICAL_NOT_RUN | Android 窄屏模拟待验；真实 Android 设备未测试 |
| AVATAR_SUPPORTED | STATIC_ASSETS_AVAILABLE / INTERFACE_PENDING | 用户原型静态 WebP 已提取；容器及 driver 接口实施中 |
| LIVE2D_CONNECTED | NO | 未提供或驱动真实 Live2D 模型 |
| PRODUCTION_DEPLOYED | NO | 本轮本地交付，不部署生产 |

## 可复现检查

在 `apps/nana-space` 中执行：

```bash
npm ci
npm test
npm run build
npm run test:e2e
npm run preview
```

浏览器测试应覆盖桌面与 Android 风格手机视口，实际截图检查应包括主页、聊天、长文本、记忆检索、目标、Inspector、设置及典型错误状态。模拟视口不能证明真实 Android 的软键盘、功耗、低内存、音视频和 OS 权限行为。

## 本次验证记录

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 独立依赖安装 | PENDING | 主会话执行后填写 |
| TypeScript / production build | PENDING | 主会话执行后填写 |
| Adapter / JSON 边界单元测试 | PENDING | 主会话执行后填写 |
| 桌面与手机浏览器交互 | PENDING | 主会话执行后填写 |
| 关键页面截图视觉审查 | PENDING | 主会话执行后填写 |
| 敏感内容与变更白名单 | PENDING | 提交前检查 |
| 独立分支 commit / push | PENDING | 最终交付时填写 commit |

本轮未运行 Core 全仓测试：前端没有修改 Core；现有 Core 测试数字只作为背景，不计作本轮通过。未读取私人数据库、调用付费模型、操作真实 QQ/B站或设备、修改生产、合并 main 或改动 Precision V2 工作区。

已知未完成范围：正式 Core 网关/认证、真实消息与事件流、设备动作、Core 权威设置、备份恢复执行、Live2D、真实语音/摄像头接入、PWA 离线首启、Android 实机资格、生产部署。这些入口必须清楚标明 PLANNED/UNAVAILABLE，不把本地 UI 操作描述为真实效果。
