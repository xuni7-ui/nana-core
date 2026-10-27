# 当前 V3 状态入口

请以 [V3 STATUS](../../../docs/nana_space_v3/STATUS.md) 与其 evidence 为准。
当前分支 dev/nana-space-v3-cotex，原 V2 部署分支不变；First-Life NOT_READY / Beta NO。
以下内容是保留的 V1 历史资格，不能当成本轮重新运行结果。

---

# Nana Space — V1 与真实开发 Core 接入状态

当前集成分支 dev/nana-space-core-integration-v1-codex，Core 固定 87f73d235d593a0d852bca409b0e73e0ef67cc5e / Precision revision31；原 V1 b403f60 / dev/nana-space-v1-codex 保留。所有本轮源码、记录与资源仅在 apps/nana-space。

| 项目 | 当前状态 | 范围 |
| --- | --- | --- |
| UI_COMPLETE | YES — V1 + 开发接入界面 | 十页 Demo 及独立 Core 视图；授权、身份、断线和 UNKNOWN 反馈 |
| DEMO_WORKING | YES | 原 V1 回归 80 PASS，不与 Core 数据混合 |
| CORE_ADAPTER_READY | DEVELOPMENT_WORKING / PRODUCTION_PARTIAL | 本机同源会话网关、原 owner IPC、Inspector V1、PROJECT 输入与回执；生产网关/认证/事件流未资格 |
| REAL_CORE_CONNECTED | QUALIFIED_OWNED_DEV_ONLY | 已实际连接原 Core 开发进程，非 fixture 回复冒充；不是生产奈奈，也不是持续在线部署 |
| MOBILE_QUALIFIED | SIMULATION_PASS / PHYSICAL_NOT_RUN | V1 五视口；Core 视图 desktop/android-style/320px/landscape 模拟；真实 Android OS 未测 |
| AVATAR_SUPPORTED | STATIC + DRIVER_INTERFACE | 静态图与本地预览；Core 视图不推测情绪 |
| LIVE2D_CONNECTED | NO | 无真实 Live2D 或口型/语音驱动 |
| PRODUCTION_DEPLOYED | NO | 仅开发实例、loopback、无生产或真实设备权限 |

## 本轮结果

- TypeScript / production build PASS。
- Vitest 16 PASS：原 12 项数据边界及 4 项 live 契约/身份/失联不重试/原始正文保留拒绝。
- Python 新网关与真实 owner 集成 4 PASS；加现存 Inspector/Surface 兼容用例共 12 PASS。真实进程、原消息元数据引用、一次 dispatch、SIGKILL 后同 Subject 恢复均检查；未运行 Core 全仓资格。
- V1 生产构建浏览器回归 80 PASS / 0 fail / 0 skip，见 validation/development-demo-regression.json。
- Core 浏览器 16 PASS / 0 fail / 0 skip：四视口 × 四组，登录/身份、十页来源一致、真实 Core 对话、断线清除、实际 dispatch 后回包丢失→只核验、错误 generation 拒绝且有可见反馈。最后执行结果见 validation/development-core-results.json。
- 已实际查看手机真实 Core 聊天、桌面 Inspector 截图，文件在 previews/live/。其中随机 ID 属于该次临时开发实例，不是生产实例 ID。

V1 的 validation/results.json 和原截图保留为历史依据；本次的新范围以 development-* 记录为准。测试 home 在仓库外由测试创建，临时 home/owner 结束后清理；不会把 DB、日志、会话 Cookie、口令或模型凭据提交入库。

## 数据可用性

Core 接入只展示正式有界 metadata：身份、lease 状态、目标/判断/经历/来源/学习等 section。未提供完整标题、正文或摘要的部分显式保持有限或 UNKNOWN，不拿 Demo 的观星、共同经历或情绪补齐。当前无 Provider，Core 的离线表达明确标注 NOT_RUN/OFFLINE_NO_PROVIDER。

用户 PROJECT 文本进入原 Core 后会产生真实开发主体输入元数据和判断记录，正文不启用长期保留。浏览器聊天仅当前页面有界内存，网关回执有界且不成为第二记忆权威。执行成功、真实模型自然度和长期共同生活资格均不由这次接通自动成立。

## 运行与复现

读 LIVE_INTEGRATION.md。完整仓库 + Python 3.12/Linux；网关仅 loopback，使用本机会话口令和预期 Subject ID。npm run dev/preview 不会自行启动 Core。开发 owner 与网关均显式启动，不接管生产 home。

```bash
npm ci
npm test
npm run build
python3 -m pytest gateway_tests -q
NANA_PYTHON=YOUR_VENV_PYTHON npm run test:live
npm run test:e2e
python3 scripts/verify-source.py
```

实际 Android 软键盘、功耗/低内存、真实音视频、语言模型、Provider 配置写入、设备/社交动作、生产认证部署、SSE 流与长期驻留均不在已通过范围。不创建第二 SubjectLoop/权威 Store，不重写冻结框架、PROJECT_BRAIN、主线或其他会话 staging。
