# 开发接入层补充

当前在原 V1 层次之外新增 gateway/（宿主 Python 标准库 HTTP、会话与固定 IPC 白名单）、src/data/live.ts（严格版本/身份/权限映射）、CoreApp（与 Demo 分离的真实投影/对话）。Gateway 不创建 Store/Runtime；开发启动器显式建立新隔离 home 并启动原 LifeApplication。新在线协议为 nana-space-live/v1，生产通用网关仍未资格。详见 [LIVE_INTEGRATION](LIVE_INTEGRATION.md)。

以下保留 V1 架构。

# Nana Space V1 架构

本目录是可独立安装、构建和静态托管的 Surface。Core 的权威状态、运行进程、数据库和凭据不属于浏览器工程。

## 技术选择

React 19、TypeScript 5.9、Vite 6 构成应用；React Markdown 呈现受限消息内容，Lucide 提供统一图标。Vitest 验证数据与交互边界，Playwright 检查桌面和手机视口。依赖锁随源码提交。

选择这些工具是为了类型化边界、直接的静态构建和成熟的组件生态。没有引入大型组件库、第二套 Agent 框架、浏览器数据库或后台自治进程。动画以 CSS 和有限媒体层为主，可减少动效。

## 分层

```text
App Shell / 路由与导航
  ├─ 生活主页、聊天、记忆、目标、手记
  ├─ 世界、成长、设备、运行状态、设置
  ├─ 设计组件 / 主题 / 本地偏好
  └─ Avatar / Media 展示层
           ↓ 展示所需的类型化数据
    Data & Event Adapter boundary
      ├─ DemoAdapter：固定演示场景和演示响应
      ├─ Inspector：schema 1 只读 JSON 导入
      └─ Planned Gateway：未来正式宿主接入
           ↓ 认证、授权、privacy、revision
    原 Nana Core 应用 owner / 正式投影
           ↓
    同一 Subject / Store / SubjectLoop / active lineage
```

`src/data/contracts.ts` 定义 Surface 契约 `nana-space/v1`、页面实体、成熟度、消息发送状态、演示场景及 Inspector metadata 类型。这些 UI DTO 不冒充 Core 原始 DTO。Core 版本变化通过适配层映射，页面不直接依赖 SQLite 表或 Python 内部对象。

## 数据和交互原则

1. **来源明确。** Demo 数据携带演示模式；导入 Inspector 显示其 identity、as_of、coverage 和只读语义。缺失、未知和空内容分别表达，不补成“真实在线”。
2. **异步可取消。** 加载、场景变化、发送与页面生命周期需处理延迟、取消和错误；过时请求不能覆盖新场景。演示发送只产生演示消息。
3. **状态分层。** `Maturity` 表示功能接入成熟度，不等于 Subject 意愿。目标的 `DECLINED`、权限的 `BLOCKED`、动作的 `UNKNOWN` 分别呈现。
4. **本地偏好有限。** 浏览器持久化仅服务主题、字号、动效及明确的 UI 偏好；数据缓存不是记忆权威、Grant 或恢复包。
5. **安全呈现。** 不执行消息中的 HTML、代码或设备命令。附件和头像是展示资源；图片或音视频可用不代表已有真实感知/语音模型。
6. **隐私删除传播。** 正式投影来源撤回后，清除对应派生展示，不使用本地旧快照复活正文或权限。手工导入快照应标为历史资料并可清除。

## 扩展边界

新功能先声明能力成熟度、投影版本、来源、缺失语义与访问策略，再注册模块。未来 events/SSE/WebSocket 是网关传输选择，不在浏览器再建 SubjectLoop；断线期间停止宣称实时性，重连后按 cursor/revision 重新核验。

Avatar driver 只消费允许展示的状态、明确的 UI 预览及语音播放进度。它可拥有 mount/update/dispose 和口型扩展点，但不能按时间、关键词或随机数生成奈奈的内在情绪。Live2D、摄像头、麦克风、设备动作和 UI 扩展安装均需各自的实际接线与资格。

本轮不注册 Service Worker，不承诺离线首启或完整离线 App。已加载的演示界面和本地偏好不等于 PWA 离线资格，更不等于 Core 连续运行。

## 响应式与验证

桌面使用导航与多面板布局；手机改用底部导航、触摸友好控件、独立滚动和安全区域。聊天输入应适应动态视口、长文本和软键盘。键盘焦点、对话框关闭、减少动效、错误与空状态属于验收范围。

实际执行结果与截图范围只记录在 [STATUS](STATUS.md)，不以构建成功替代视觉、手机实机或长期运行验证。
