# Nana Space V1 产品与验证状态

本表仅针对独立前端，不改变 Nana Core 的能力资格。当前交付是可独立运行的 Demo 应用及只读快照观察窗；真实在线 Core 接入仍为后续工作。

| 项目 | 状态 | 准确范围 |
| --- | --- | --- |
| UI_COMPLETE | YES — V1 独立前端范围 | 十页、搜索/筛选、主题/缩放、状态与错误语义、桌面及手机布局 |
| DEMO_WORKING | YES | 全部 Demo 场景；聊天流式、附件元数据、失败重试与 UNKNOWN |
| CORE_ADAPTER_READY | PARTIAL | 已有 Inspector V1 JSON 白名单导入及边界测试；在线 Gateway 仅规划与版本校验，未实现 transport/auth |
| REAL_CORE_CONNECTED | NO | 没有真实 Core 会话、网关、消息流或生产连接 |
| MOBILE_QUALIFIED | SIMULATION_PASS / PHYSICAL_NOT_RUN | Chromium 移动视口与触摸模拟通过；没有真实 Android OS / Chrome 设备资格 |
| AVATAR_SUPPORTED | YES — STATIC + DRIVER INTERFACE | 九张静态差分、本地图片预览、显示开关与 display-only driver 类型；不推测内在情绪 |
| LIVE2D_CONNECTED | NO | 未提供或驱动真实 Live2D 模型，口型与真实语音未接入 |
| PRODUCTION_DEPLOYED | NO | 仅本地运行、可静态托管产物及独立源码分支 |

## 可复现检查

在 apps/nana-space 中运行：

```bash
npm ci
npm test
npm run build
npm run test:e2e
npm run preview
python3 scripts/verify-source.py
```

Playwright 会构建生产资源，启动 4173 preview，再以单 worker 运行 16 组交互 × 5 个视口。可通过 NANA_BROWSER_PATH 指定 Chromium；无系统 Chromium 时使用 Playwright 安装的浏览器。

## 实测结果

- 干净目录锁文件安装、TypeScript 与 production build、12 项 Vitest 单元测试通过。
- 最终生产构建：80 项 Playwright PASS，0 failed / 0 skipped / 0 retries；实际结果、时长、版本和受测文件 SHA256 见 [validation/results.json](validation/results.json)。
- 视口：desktop 1440×1000；android-style 390×844；small-phone 320×740；tablet 768×1024；landscape 844×390。
- 覆盖十页路由、无横向溢出、记忆搜索/纠正/撤回、目标暂停/恢复与意愿/权限区分、证据分歧、设备限制、Markdown/流式、8000 字、附件预览与 URL 释放、失败重试、UNKNOWN 不重发、场景取消、快照版本/权限/身份拒绝和清除后迟到导入。
- 覆盖键盘焦点、Tab/ESC、主题与本地偏好恢复、减少动画、120% 缩放；浅色标题对背景的对比度至少 4.5:1。局域网 HTTP 缺少 randomUUID 的能力情形通过模拟验证，不冒充手机实测。
- 已实际查看桌面主页、聊天、手机聊天、桌面和手机浅色 120% 截图；关键预览随源码保存在 previews/。全页截图中的固定底栏出现在截取时的视口底部，不代表页面中部存在另一条导航。

历史问题如实保留：最初桌面 6/9 PASS、默认 npm test 误收 Playwright；收尾已修复。视觉审查发现浅色标题对比不足后中断一次中途矩阵，修复并重跑；另独立复现缺少 randomUUID 时发送失败后修复。当前表仅以最后完整 80 项结果作为通过依据。

## 交付与边界

分支 dev/nana-space-v1-codex；所有新增/变更仅位于 apps/nana-space/。初始可恢复检查点 b4cda18；最终提交 SHA 从 Git/分支获取，避免在自身内容内自指。只使用非强制 push，未合并 main 或 Precision 分支。

按用户最新隔离要求，变更记录与指纹留在本目录 docs 和 Git，不占用 PROJECT_BRAIN 的主线状态或账本。敏感内容模式扫描、源码白名单与依赖许可证核对在提交前完成；SOURCE_MANIFEST.json 排除自身，指纹只证明文件，不证明运行态。

Android 实机软键盘、低端设备功耗/内存/长期驻留、不同厂商 WebView 与真实音视频权限未验证。当前不注册 Service Worker，不承诺 PWA 离线首启。

本轮没有运行 Core 全仓测试；没有修改 Core、读取私人数据库或操作真实 QQ/B站、用户设备、生产、真实 Core Provider 或主体记忆。真实网关/认证、事件流、设备动作、Core 权威设置、备份恢复执行、Live2D、语音/摄像头仍未接入。
