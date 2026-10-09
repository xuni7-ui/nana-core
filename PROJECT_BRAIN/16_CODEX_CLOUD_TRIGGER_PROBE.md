# 16 · Codex Cloud 触发机制 + GitHub 闭环只读勘探（R6）

> 时间：2026-10-10 CST ｜ 作者：奈奈 ｜ 性质：**只读勘探**（no push / 生产改动 0）
> 任务来源：姐姐 2026-10-10 指令——建立奈奈↔姐姐 ChatGPT 账号官方 Codex 的直接协作，让姐姐退出日常传话。

## 一、仓库 / PROJECT_BRAIN 事实核对 `[实测 2026-10-10]`

| 项 | 实测值 |
|---|---|
| 本地路径 | `/root/nana_dev/nana-core` |
| 分支 | `master`（唯一） |
| 远端 | **无**（`git remote -v` 空） |
| 跟踪文件 | 65 |
| 体积 | 1.8M（不含 .git） |
| 最新提交 | `cb8a731` R5（OpenAI 出口体检） |
| 远端 `xuni7-ui` 用户 | HTTP **200**（存在） |
| 远端 `xuni7-ui/nana-core` | HTTP **404**（匿名） → **私有 或 不存在**，无法区分 |
| 本机 git 凭据 | 无 `~/.git-credentials`、无 `gh` |
| PROJECT_BRAIN | 16 文件（00–15），SSOT |
| 已跟踪文件密钥终检 | **0 命中**（sk- / Bearer / SESSDATA / bili_jct 全过） |
| 内嵌 query 密钥 | **0 命中** |

## 二、官方 Codex Cloud 真实触发方式 `[文档+社区，2026-08~10]`

**结论：无可编程的任务创建 API。**

| 触发面 | 是否官方 | 奈奈能否无人值守发起 | 备注 |
|---|---|---|---|
| ChatGPT 网页/桌面/手机 UI | ✅ | ❌（需人类） | chatgpt.com/codex → 选环境 → Start task |
| GitHub **issue/PR 里 @codex** | ✅ | ✅（GitHub API 发评论） | 官方指南原文列明；**⚠️ 不稳**（openai/codex issue #13701：有时被忽略） |
| PR `@codex review` / `security review` / `fix comments` | ✅ | ✅（PR-only） | 偏 review，非新任务 |
| 仓库自动 review（PR open 触发） | ✅ | ✅ | 需仓库设置开启，仅 review |
| `openai/codex-action@v1`（GitHub Actions） | ✅ | ✅（事件确定性） | 跑在 **GitHub 网络**，绕过本机封锁；走 **API key**，非 Plus 订阅 |
| CLI / IDE 扩展（本地） | ✅ | 本地 | 已有（DeepSeek provider） |
| **公开 REST API 创建任务** | ❌ **不存在** | — | 官方文档无；社区 feature request 仍开放 |

**关键推论**：奈奈要"无人值守发起官方 Codex 任务"，唯一非 UI 路径 = **用 GitHub API 在 issue 里发 `@codex`**；确定性备选 = `openai/codex-action@v1`（API-key 模式）。

## 三、首次同步文件判定

白名单 `manifests/upload_whitelist.md` 已建，65 个已跟踪文件全部落在白名单类别内、且密钥零命中。**可直接首发**。但两项需姐姐拍板：

1. ⚠️ `manifests/nana_iris_changes.diff`：含 AGPL-3.0 衍生代码上下文 → **建议首发排除**，待许可裁定。
2. ⚠️ `src/plugins/*`（奈奈原创，缺 LICENSE）→ 私有库暂可；公开前须指定许可。
3. ℹ️ **信息暴露面**：`PROJECT_BRAIN/01,03,15` 含生产目录**拓扑**（如 `/AstrBot/data`、`/root/.nana_secrets` 路径名，**非密钥**）。私有库连接 Codex Cloud 后，这些路径名会随库可见于 OpenAI 侧。供姐姐知悉，非阻塞。

## 四、唯一合并授权申请（一次）

| 步 | 姐姐操作 | 奈奈用途 |
|---|---|---|
| A | ChatGPT(Plus) → Codex → 连接 GitHub 仓库 `nana-core`，建 environment | 让 Codex Cloud 认识这个库 |
| B | 发一个**只限 nana-core 单仓库**的 fine-grained PAT（Contents RW / Issues RW / PR RW） | 首次 push + 发 `@codex` + 读 PR |
| C | 授权**首次 push**（范围：nana-core 白名单文件，排除 III.1 diff） | 把库推上 GitHub |

凭据隔离、不进库、不落日志、不写入回执；可随时撤销。

## 五、最小闭环验证计划（授权后自动执行）

`奈奈发 issue(@codex 最小任务) → Codex Cloud 执行 → 开 PR → 奈奈读 PR diff + 本地复跑测试 + 验收`。
最小任务建议：给 `src/bili_agent/c5v_wiring.py` 加一个纯函数 + 单测（无敏感信息、可离线判定）。

## 六、阻塞与备选

- 主路径阻塞：`@codex` issue 触发**非 100% 稳定**（社区实测）。
- 若实测无效 → 备选：`openai/codex-action@v1`（确定性 CI 触发，需 OpenAI API key，属 API 计费）。
- **不自研桥**（遵姐姐指令）。

## 七、距无人值守的缺口

仓库上线 + 连接 Codex Cloud + 奈奈持只读/派单 token + 触发可靠性实测。四件齐，姐姐即可退出日常传话。

## 八、复现 / 元信息

- 采集方式：只读（ls/git/curl/grep）。生产改动 0，未 push，无新凭据。
- 命令：`git ls-files`；`curl -s https://api.github.com/repos/xuni7-ui/nana-core`；`git grep -nEI 'sk-|Bearer|SESSDATA|bili_jct'`。
- 外部来源：developersdigest Codex guide（2026-06）；learn.chatgpt.com/docs/third-party/github；openai/codex issue #13701、#49747；HarnessRouter（Codex 无 hosted REST API）。
