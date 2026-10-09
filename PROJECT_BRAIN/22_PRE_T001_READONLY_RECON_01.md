# 22 · T-001 三项只读前置核验（R12）

> 时间：2026-10-10 07:0x CST（服务器本地时钟为 UTC）｜ 授权口令：姐姐「动手」
> 边界：**只读**。零生产改动、零 push、零 PR、零建环境、零联网安装。本地仅新增文档并提交（无 remote 写入）。

---

## 1. ① 祖先关系与提交差 —— 结论：**线性、无分叉、对齐成本 = 0**

| 检查 | 命令 | 结果 |
|---|---|---|
| a314c4c 是 a9b1d36 的祖先？ | `git merge-base --is-ancestor a314c4c a9b1d36` | ✅ exit=0（**是**） |
| 反向？ | 同上一句反向 | ❌ exit=1 |
| a314c4c..a9b1d36 差几个提交 | `git log --oneline a314c4c..a9b1d36 \| wc -l` | **1**（a9b1d36 = R10） |
| merge-base | `git merge-base` | `a314c4c`（即分叉点就是 a314c4c 本身） |
| 本地领先 origin/main | `git log --oneline origin/main..HEAD` | **1**（e681716 = R11，未 push） |

**判读（修正 + 澄清）**：
- `a314c4c` 是 `a9b1d36` 的**严格祖先**，两点之间**只有 1 个提交**，**无分叉**。⇒ 对齐到 `origin/main` 是**纯快进**，不可能冲突。
- 「在 a314c4c 上开发会让 PR 把 main 往回退」这句要**精确化**：不是历史回退（不可能），而是 **PR 的 diff 里会出现 a9b1d36 的逆向差异**（分支缺少 R10 的内容）。⇒ **风险仍然成立，处理结论不变：一律从 `origin/main` 起分支。**

## 2. ② 远端 main 是否含 C.5-V-1 源码 —— 结论：**有，Codex 有源可改**

以本地追踪引用 `refs/remotes/origin/main`（= `a9b1d36`）的树为准：

| 需要的文件 | 在 origin/main 树内 |
|---|---|
| `src/bili_agent/c5v_wiring.py` | ✅ 12028 B |
| `src/bili_agent/test_c5v_wiring.py` | ✅ 8149 B |
| `src/c5v/bili_video_vision.py` | ✅ |
| `docs/c5v_wiring_design.md` | ✅ |
| `bridge/tasks/c5v_wiring_increment_01.json` | ✅ |
| `tests/` 目录 | ❌ **不存在** |

**两条硬事实（会改变任务卡写法）**：
1. `e896574`（隔离副本那次提交）**不在本仓** —— 但内容**已在 origin/main**，因为 a9b1d36 树内确实有 c5v 文件。⇒ 「没上远端」的担忧**排除**。
2. **没有 `tests/` 目录**；测试是**自跑脚本** `src/bili_agent/test_c5v_wiring.py`。
   `python -m pytest src/bili_agent/test_c5v_wiring.py` → **`no tests ran`（0 条）**；
   `python3 src/bili_agent/test_c5v_wiring.py` → **11 通过 / 0 失败**（本轮实测）。
   ⇒ **正确测试命令是后者。** 之前写的 `python -m pytest tests/ -k c5v -q` **作废**。

## 3. ③ 环境/分支/账号关联 —— 结论：**服务器侧读不到，如实标「未知」**

| 项 | 结果 |
|---|---|
| `origin` URL | `https://github.com/xuni7-ui/nana-core.git` ✅ |
| `origin/HEAD`（默认分支符号引用） | **未设置**（`fatal: ref refs/remotes/origin/HEAD is not a symbolic ref`）→ 默认分支=main 属**推断**，非实测 |
| 本地 git 身份 | `Nana <nana@local>`（**仅本地提交身份，与 GitHub 账号/Codex 环境归属无关**） |
| `gh` CLI / `codex` CLI | 均**未安装** |
| `GITHUB_TOKEN` / `~/.git-credentials` / `~/.config/gh` / `~/.ssh` | **全不存在** ⇒ 服务器**无任何 GitHub 凭据** |
| Codex 环境设置页：归属 ChatGPT 账号 / 绑定分支 / 隐私 | **未知**（UI 信息，服务器不可读，不猜） |
| 远端实时 refs（`git ls-remote`） | ⚠️ **本轮未取得**（见下） |

### 3.1 新的网络边界（如实记录）

| 目标 | 结果 |
|---|---|
| `https://github.com` | **超时**（curl rc=28，http=000） |
| `github.com/.../*.git/info/refs?service=git-upload-pack`（git 端点） | **超时**（http=000, rc=28） |
| `git ls-remote origin` | **超时**，`timeout` 退出码 **124**，无任何输出 |
| `https://api.github.com` | ✅ 200 |
| `https://api.deepseek.com` | ✅ 401（可达） |
| DNS `github.com` | ✅ `20.205.243.166` |

**⇒ 结论：** GitHub 的 **API 主机可达，但 github.com 的 git-over-HTTPS 端点本轮不通**。
所以：
- 本轮**无法**用 `git fetch/ls-remote` 复核远端真身；
- `origin/main = a9b1d36` 的时效 = **上次 fetch 于 2026-10-09 20:48 UTC**（距今约 2h15m），**属历史快照，非实时**；
- **不猜**远端现在的状态。Codex 任务里必须自带 `git fetch origin`（在云端跑，不走本服务器的网）。

## 4. 提交 → 交付物

- 任务卡：`docs/tasks/T-001-c5v1-wiring-increment.md`（目标/范围/验收/测试/禁止/基准/回滚 七段齐全）
- 本文件：`PROJECT_BRAIN/22_PRE_T001_READONLY_RECON_01.md`

## 5. 本轮未做（明确）

❌ 未 push ｜ ❌ 未开 PR ｜ ❌ 未改生产代码/配置 ｜ ❌ 未建/改 Codex 环境 ｜ ❌ 未发 `@codex` 评论 ｜ ❌ 未联网安装任何东西
