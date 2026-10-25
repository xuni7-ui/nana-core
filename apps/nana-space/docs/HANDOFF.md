# 当前交接：真实开发 Core 接入

当前分支 `dev/nana-space-core-integration-v1-codex`，基线主线87f73d2与前端b403f60。已实现宿主网关、Core view/Inspector 投影、PROJECT 对话与不重发的 UNKNOWN 核验，具体操作和资格见 [LIVE_INTEGRATION](LIVE_INTEGRATION.md) 与 [STATUS](STATUS.md)。旧 V1 分支完整保留；以下为其交接历史。

# Nana Space V1 — 独立前端交接

当前：原续作计划中的前端修复和模拟验收已完成，80 项浏览器检查与 12 项单元测试通过。下一阶段若接真实 Core，应先读 STATUS.md 与 CORE_INTEGRATION.md；下方 WIP 是历史检查点。

## 获取源码

仓库：`https://github.com/xuni7-ui/nana-core`，分支：`dev/nana-space-v1-codex`。
前端位于 `apps/nana-space/`。请从远端检出此分支，不依赖原会话的 `/workspace` 路径。

```bash
git clone --branch dev/nana-space-v1-codex --single-branch https://github.com/xuni7-ui/nana-core.git
cd nana-core/apps/nana-space
npm ci
npm run dev
```

## 开发边界

本分支源于 `e1679b2010c2d49148c9b99b096b9947dfdba8ff`；不自动合并继续前进的 Precision 主线。
Nana Space 是 Surface / 三横轴的 Advanced 前端工作，不改变 Foundation 资格。
仅提交 `apps/nana-space/`。按用户最新要求，不占用 PROJECT_BRAIN 状态、任务、决策或变更账本；本目录的文档和 Git 记录承担前端交接记录。
Core、生产、私有数据库、真实社交/设备、模型凭据与付费调用均不在本交接范围。
One Subject / One authoritative Store / One SubjectLoop / One active lineage 不变。

## 初始交接检查点（历史 WIP，b4cda18）

十页、Demo 数据层、静态角色、Inspector V1 白名单导入、planned gateway 已实施。
之前实际检查：build PASS；指定 adapters 单元测试 12 PASS；五视口十页路由无横向溢出；desktop 交互 6/9 PASS。
这是中途检查点，不是最终完成或真实 Core 连接。最终状态以同目录 STATUS.md 和后续提交为准。
当时已知缺陷：导入吞错假成功、附件 URL 清理、输入 12000 与 adapter 8000 限制不同、搜索初始焦点、quiet 偏好未实际影响提示、npm test 误收 Playwright；流式测试定位重复。这些是初始检查点的历史缺陷，后续修复及最终验收见 STATUS.md。

## 原续作计划与验收依据

1. Inspector 拒绝无效快照时保留原快照、明确显示错误，不产生成功提示。
2. 修复附件 URL 创建释放，添加/移除/发送/卸载均正确；统一 8000 字并保留失败消息，UNKNOWN 不盲目重试。
3. 修复搜索焦点、Tab/ESC 与焦点恢复；quiet 实际控制非必要提示，首页分享/通知/时间统一依赖场景投影。
4. 认真检查手机触摸区域、横屏聊天、浅色主题、减少动画与 120% 缩放。
5. 分离 Vitest 和 Playwright，修复测试定位，补多附件/长消息/重试/UNKNOWN/场景取消/无效快照/身份检查。
6. 构建、单元与五视口浏览器验收；审查截图。模拟视口不能替代 Android 实机资格。
7. 更新 README、接入/资源/状态文档，按前端白名单扫描与指纹后提交、非强制推送本分支。

## 本次收尾改动

- 修复导入错误传播、同身份检查与清除后的迟到导入；拒绝导入不会替换旧快照。
- 附件 object URL 独立管理，StrictMode updater 无资源创建副作用；输入统一 8000 字；发送互斥、错误保留、UNKNOWN 不重试。
- 搜索与导航使用有标签原生 dialog、焦点锁定/恢复；文件选择器可键盘操作；跳转主内容不破坏 hash 路由。
- 安静偏好减少非必要提示与红点；分享卡/通知来自同一场景，quiet 不填造消息；日记和聊天日期对齐快照。
- 手机触摸区域、横屏/安全区和缩放、浅色标题对比度修复；按页面懒加载。局域网 HTTP 环境可能缺少 crypto.randomUUID，Demo 消息使用局部递增 ID 回退（不用于主体、认证或授权）。
- Vitest 与 Playwright 分离，浏览器测试使用生产构建；支持系统或 Playwright Chromium。
- 前端 source manifest 和 verify-source.py 可用于验证获取文件，不能证明运行态或主体资格。

## 正式接入限制

已有 Frontend/Provider/Perception 是 Python 应用契约，不是浏览器 HTTP API。
Inspector JSON 导入是本地静态快照，不是实时连接；不与 Demo 混合。
真实 Gateway/认证/聊天流/设备控制/Live2D/生产部署继续标记未接入。参见 CORE_INTEGRATION.md。

## 变更记录

- 初始开发检查点：收录已保存的全部前端源码与资源，使不同会话可以通过独立分支交接；未修改 Core 或共享主线状态。验证按上述实测范围记录，不将失败测试写成通过。
