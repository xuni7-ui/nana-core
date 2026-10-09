# 20 · Codex Cloud environment 阻塞复测（R10）

> 时间：2026-10-10 04:38–04:43 CST ｜ 执行：奈奈 ｜ 授权：姐姐「A，动手」（第 4 条：推送后验证 `@codex` 派单）
> 范围：Issue #1 **两次真实触发**（写评论）+ 只读 API 诊断。
> 约束：生产零改动、不自动合并 PR、不启用付费 API、未 force。

---

## 一、结论（一句话）

**触发链路完全正常，卡点是「environment 未生效」。**

- ✅ `@codex` 写评论 → timeline **必现** `mentioned(codex)` 事件（0～1 秒）
- ✅ `chatgpt-codex-connector[bot]` **3～5 秒内回复**
- ❌ bot 回复内容固定为：`To use Codex here, create an environment for this repo.`
- → 说明 **Codex Cloud 侧没有把 `xuni7-ui/nana-core` 关联到任何 environment**

---

## 二、实测记录 `[实测 2026-10-10]`

| # | 时间 (CST) | 动作 | comment id | 响应 |
|---|---|---|---|---|
| 1 | 04:39:25 | POST 评论「环境已建好，请接手任务」 | 6088873418 | 04:39:29 bot：`create an environment for this repo` |
| 2 | 04:42:38 | 隔 **~120s** 后二次 POST（排除传播延迟/缓存） | 6088919356 | 04:42:42 bot：**同样回复** |

**Issue #1 timeline（只读 `/issues/1/timeline`）**：

```
20:39:25Z commented  xuni7-ui
20:39:26Z mentioned  codex          ← 触发成功
20:39:29Z commented  chatgpt-codex-connector[bot]
20:42:38Z commented  xuni7-ui
20:42:42Z mentioned  codex
20:42:42Z commented  chatgpt-codex-connector[bot]
```

**旁证**：
- `GET /repos/xuni7-ui/nana-core` → private=true，default_branch=`main`，**200**
- `branches` = `['main']`；`pulls?state=all` = **[]** → Codex **未产生任何分支/PR**
- `GET /repos/xuni7-ui/nana-core/installation` → 401（**PAT 无权读 App 安装**，非异常，属权限边界）

---

## 三、排查：**不是**「本机离线」导致

姐姐问「不会不能是离线吧？」→ **不是**。理由（架构层面）：

| 环节 | 跑在哪 | 依赖本机网络？ |
|---|---|---|
| `@codex` 识别 | GitHub 服务端 | ❌ 不需要 |
| ChatGPT Codex Connector（GitHub App） | GitHub → OpenAI 服务端 | ❌ 不需要 |
| Codex Cloud 执行 + 开 PR | **OpenAI 云端** | ❌ 不需要 |
| 奈奈读 diff / 复测 / 验收 | 本机（只读 GitHub API，**已通**） | ✅ 需要，**且实测可达** |

即：本机 `chatgpt.com` 不可达（R5 结论）**不影响** `@codex` 闭环；本机与 GitHub API 通信**正常**（本轮全部调用 200/201）。
环境是 **OpenAI 侧的对象**，本机通不通网都不改变它的存在与否。

---

## 四、真正需要姐姐核对的（按顺序，约 2 分钟）

> 关键点：**environment 建在 ChatGPT 账号侧**，而 `@codex` 由 GitHub 侧 App 投递。两者必须指向**同一个 GitHub 账号 `xuni7-ui` + 同一个仓库**。

1. **确认账号一致**
   打开 https://chatgpt.com/codex/cloud/settings/environments —— 必须是**拥有 Codex 云权限的那个 ChatGPT 账号**（Plus/Pro/Business/Team），并且它连接的 GitHub 账号 = `xuni7-ui`。

2. **确认「仓库在 App 授权范围内」**
   GitHub → 右上头像 → **Settings → Applications → ChatGPT Codex Connector → Configure**
   看 `xuni7-ui/nana-core` 是否在授权仓库列表里；若不在 → 勾上它（或 All repositories）→ **Save**。

3. **在 environments 页重建/重选仓库**
   - 若列表里**已有** environment：编辑它，确认 **Repository 选的是 `xuni7-ui/nana-core`**（不是别的仓库）。
   - 若**没有**：新建 → Repository 下拉里选 `xuni7-ui/nana-core` → 保存。
   - ⚠️ 下拉里**看不到** `nana-core` ＝ 第 2 步没生效，先回第 2 步。

4. **确认套餐支持 Codex 云执行**（免费号无 Cloud environment 能力，会一直提示建环境）。

做完回奈奈一声，奈奈**立刻再发一条新的 `@codex` 评论**验证（旧评论不会补触发）。

---

## 五、边界

未改生产 ｜ 未自动合并 PR ｜ 未启用付费 API ｜ 未 `--force` ｜ 未安装/未登录任何 OpenAI 侧工具 ｜ 未升级本机权限。
Issue #1 只增两条中文触发评论，**仓库代码零改动**（`main` 仍 = `a314c4c`，无新分支/PR）。

## 六、复现命令（只读）

```
GET  /repos/xuni7-ui/nana-core
GET  /repos/xuni7-ui/nana-core/issues/1
GET  /repos/xuni7-ui/nana-core/issues/1/comments
GET  /repos/xuni7-ui/nana-core/issues/1/timeline
GET  /repos/xuni7-ui/nana-core/branches
GET  /repos/xuni7-ui/nana-core/pulls?state=all
POST /repos/xuni7-ui/nana-core/issues/1/comments   { "body": "@codex …" }
```
