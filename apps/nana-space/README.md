# Nana Space V1

> 源码独立保存在 `dev/nana-space-v1-codex`。获取方式、开发历史与交接边界见 [HANDOFF](docs/HANDOFF.md)，实际验收范围见 [STATUS](docs/STATUS.md)。

奈奈的数字生活空间：以生活主页、交流、共同记忆和探索为中心的独立前端。深蓝与紫色玻璃界面、柔粉点缀、桌面多栏和手机底部导航延续用户原型的气质。

本应用默认使用明确标记的 **DEMO** 数据。它没有连接生产奈奈，不创建 Subject、权威记忆、SubjectLoop 或设备权限。当前实际完成与验证状态见 [STATUS](docs/STATUS.md)。

## 启动

推荐 Node.js 22 LTS 和 npm。在仓库中执行：

```bash
cd apps/nana-space
npm install
npm run dev
```

打开终端打印的本地地址，通常为 `http://localhost:5173`。在同一局域网的 Android Chrome 中访问开发机地址与对应端口；远程工作环境需要其正式端口转发能力，远程 loopback 地址不能直接当手机预览地址。

```bash
npm run build
npm run preview
npm test
npm run test:e2e
```

`build` 先检查 TypeScript，再生成 `dist/`；`preview` 仅预览构建产物。首次在自己的机器运行浏览器测试时，按 Playwright 提示安装所需浏览器，例如 `npx playwright install chromium`。安装可复现依赖时可用 `npm ci`。浏览器测试会先构建并启动 production preview；优先使用 `NANA_BROWSER_PATH` 指定的浏览器，其次使用系统 Chromium，最后使用 Playwright 安装的 Chromium。

## 可以体验什么

- **空间**：奈奈的活动、关注、分享、最近经历与继续交流入口。
- **聊天**：Markdown、代码、附件展示、演示流式文本、发送状态、错误与重试。
- **共同记忆**：主题检索、来源、可信度、纠正和撤回；不向真实 Core 写入记忆。
- **目标与计划**：自主、用户和共同目标，依赖、暂停、阻塞、拒绝、未知与核验结果。
- **生活手记、世界探索、成长**：筛选后的活动、冲突证据、研究与技能测试/复用状态。
- **设备、运行状态、设置**：能力限制、普通视图与 Inspector、本地外观偏好和未来 Core 配置边界。

页面中的场景切换覆盖日常、离线、权限阻塞、来源冲突、重启、长期安静、部分投影缺失、模型不可用、慢速和加载错误。场景是固定的演示情境，不推导真实生活史。演示交互不会操纵真实设备或账户。

## 外观与角色

设置中的主题、字号、缩放、动效、提示展示和角色显示属于此浏览器的本地偏好。它们不修改奈奈的性格、情绪、长期记忆、Core 通知策略或 Manager 配置。

内置角色来自用户上传原型中的静态差分，已转为 WebP。角色图层与未来 driver 接口分离；静态图、布局与媒体容器支持不等于 Live2D 驱动完成。合法模型仍需资源格式、运行库、生命周期和授权接线。资源来源与替换方式见 [ASSETS](docs/ASSETS.md)。

## 真实数据与未来接入

目前可导入正式 Inspector 生成的只读 JSON，检查契约并展示有界 metadata。导入是一个历史快照，不代表实时连接，不授予接收者读取主体私人内容的权限。不要上传私人数据库、原始聊天、凭据或设备令牌。

`DemoAdapter` 与应用展示结构分离。正式接入需要受信任宿主网关、认证、版本化投影、同一 Subject 身份核验，以及已有应用 owner 的权限门；当前不会自动请求任何假设的未来 API。

- [架构与模块](docs/ARCHITECTURE.md)
- [真实契约、只读导入与 Core 接入](docs/CORE_INTEGRATION.md)
- [冻结框架及当前工程状态对齐](docs/FRAMEWORK_ALIGNMENT.md)
- [验证、预览和产品状态](docs/STATUS.md)

本轮只测试前端及其数据边界。未修改 Core、运行其生产实例、读取私人数据库或重复 Core 全仓资格。
