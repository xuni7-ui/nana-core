# 19 · GitHub 首次推送 + 官方 Codex `@codex` 派单实测（R9）

> 时间：2026-10-10 03:58–04:20 CST ｜ 执行：奈奈 ｜ 授权：姐姐「A，动手」
> 范围：首次 push（**normal，无 force**）+ `@codex` 触发面**真实实测**。
> 约束：生产零改动、不自动合并 PR、不启用付费 API。

---

## 1. 凭据落位（安全）

| 项 | 结果 |
|---|---|
| 路径 | `/root/.nana_secrets/github_nana_core_pat`（`chmod 600`） |
| 是否进仓库 / remote URL / 日志 | **否**（remote = `https://github.com/xuni7-ui/nana-core.git`，URL 不含 token；凭据由 `credential.helper` 运行时读文件） |
| 只读验证 | `GET /user` → **200**，`login = xuni7-ui` |
| 建议 | 闭环完成即 **revoke 换新**（该明文曾过聊天，姐姐已知悉） |

---

## 2. 历史重写：真正排除 `nana_iris_changes.diff`

- 定位：该文件在**根提交** `9ec3c5f`（原 `26ef7af`）中 → 单纯 `git rm` 不够，blob 会随历史一起被推。
- 可恢复备份：`/root/nana_backups/nana-core_pre_rewrite_20261009_200156.bundle`
  - `sha256 = daa8b02961cc83e8171b4a36c105d43d929503a02ec87dee6ea1ab6eea59b012`
- 方法：`git filter-branch --index-filter 'git rm --cached --ignore-unmatch <path>' --prune-empty -- master`
  - 随后 `rm -rf .git/refs/original` + `reflog expire` + `gc --prune=now`
- 结果：**11 个提交全保留**（SHA 变，内容仅去掉该路径）；`git rev-list --all --objects | grep nana_iris_changes` → **0 命中**。
- 仓库外留档：`/root/nana_backups/nana_iris_changes.diff.offrepo`（`md5 = 13828c7a254ad3dd4be93a0de929aa29`，与指纹表一致）。
- **因从未推送，非 force push。**

---

## 3. 无关历史合并（保留双方 README）

| 项 | 值 |
|---|---|
| 远端原状态 | `origin/main = 23e583b2` *Initial commit*，**仅** `README.md`（2 行） |
| 合并 | `git merge origin/main --allow-unrelated-histories` |
| 冲突 | `README.md` **add/add** |
| 解决 | 本地 README 为正文；远端原始 README **逐字保留**于文末「附：远端仓库初始 README（原样保留）」节 |
| 合并提交 | `e406127` |

---

## 4. 首次 push（成功）

- 命令：`git push -u origin master:main`
- 结果：`23e583b..e406127  master -> main` → **fast-forward，未使用 `--force`**。
- 远端核验（API）：

| 项 | 值 |
|---|---|
| `main` SHA | `e40612749739…` |
| blob 数 | **67** |
| 含 `nana_iris_changes.diff` | **False** |
| `README.md` 存在 | True |
| 历史 | 11 本地提交 + 远端 Initial + 合并提交，**全部保留** |

- **文件口径**：67 = 白名单 66 类 + `.gitignore`（防御性文件，无密钥）。
  细分：`PROJECT_BRAIN/ 19` + `bridge/ 9` + `docs/ 7` + `manifests/ 4` + `src/ 24` + `upstream/ 1` + 根 3（`AGENTS.md`/`README.md`/`.gitignore`）。
  （白名单文档正文写「PROJECT_BRAIN 18」为撰写时的旧计数，实际 19；口径以 git 为准。）

---

## 5. `@codex` 派单机制 —— 真实实测结果 `[实测 2026-10-10 04:1x CST]`

**探针**：Issue [#1](https://github.com/xuni7-ui/nana-core/issues/1)（最小、离线、只加新文件的任务）。

| 触发方式 | 实测结果 |
|---|---|
| `@codex` 写在 **issue 正文** | ❌ **无任何反应**（timeline 无 `mentioned` 事件，bot 无回复） |
| `@codex` 写在 **issue 评论** | ✅ **5 秒内触发**：timeline 出现 `mentioned(codex)`，`chatgpt-codex-connector[bot]` 立即回复 |

**bot 回复原文**：
> To use Codex here, [create an environment for this repo](https://chatgpt.com/codex/cloud/settings/environments).

### 结论
1. **`@codex` 机制真实可用**，bot 身份 = `chatgpt-codex-connector[bot]`（ChatGPT Codex Connector GitHub App）。
2. **必须用「评论」形式触发**；写在 issue/PR **正文里不可靠**（与社区 openai/codex #13701 一致）。
3. ⚠️ **当前阻塞**：该仓库在 Codex Cloud **尚未创建 environment**，bot 因此拒绝接管。
   与社区 #20093 / #27003 现象一致。
4. 备选（确定性、非 UI）：`openai/codex-action@v1` —— 但需 **OpenAI API key（付费）**，姐姐明令禁止，**暂不启用**。

---

## 6. 唯一待姐姐动作（人工，1 步）

1. 打开 **https://chatgpt.com/codex/cloud/settings/environments**
2. 为仓库 **`xuni7-ui/nana-core`** 创建一个 **environment**。
3. 建成后回奈奈一声 → 奈奈在 Issue #1 **发一条新的 `@codex` 评论**触发
   → Codex 云执行并开 PR → **奈奈读取 diff + 本地复测 + 独立验收**。

> 注：环境建成后，**旧的那条 @codex 评论不会自动补触发**，需重新发一条。

---

## 7. 本轮未做（守边界）

- 未修改生产、未自动合并任何 PR、未启用付费 API、未使用 `--force`、未把 `diff` 推上远端。

## 8. 复现 / 元信息

- 采集：只读 API + git（本地）。
- 关键命令：`git filter-branch …`、`git merge --allow-unrelated-histories`、`git push -u origin master:main`、`GET /repos/xuni7-ui/nana-core/commits/main`、`POST /repos/…/issues/1/comments`。
- 外部来源：openai/codex issues #13701、#20093、#27003；`openai/codex-action`。
