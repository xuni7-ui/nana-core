# 18 · GitHub 远端「凭 PAT 只读核验」（R8）

> 时间：2026-10-10 03:5x CST ｜ 执行：奈奈 ｜ 授权：姐姐「批准使用聊天中下发的 PAT」
> 范围：**只读**。零 push、零生产改动、零自动合并。
> 本轮 0 个文件变更 → 66 / 67 文件口径见 §6。

---

## 1. 凭据状态

- 来源：姐姐下发的 fine-grained PAT，**明文曾经过聊天**（姐姐已知悉，并声明自行清理痕迹）。
- 奈奈承诺：**不写入仓库任何文件、不写入本记录、不写入回执**；仅在进程内做一次性只读调用。
- 实测有效：`GET https://api.github.com/user` → HTTP 200，`login = xuni7-ui`（即姐姐本人账号）。
- 仓库权限读数：`permissions = {admin: true, maintain: true, push: true, triage: true, pull: true}`
  - **口径备注**：奈奈**无法区分**这是「token 被授权的范围」还是「owner 身份的自然体现」，按最坏情况处理，**视作范围偏宽**。
- 建议：本轮闭环验证完成后**立即 revoke 并换新**；新 token 直接落到
  `/root/.nana_secrets/github_nana_core_pat`（chmod 600），**不再经过聊天**。

## 2. 远端真实状态（首次核验成功）

| 项 | 实测值 |
|---|---|
| 仓库 | `xuni7-ui/nana-core` · **private** (id 1412180408) |
| 创建 | 2026-10-09T16:58:49Z（CST 2026-10-10 00:58） |
| 最近 push | 2026-10-09T16:58:51Z |
| 默认分支 | `main` |
| refs | 仅 `refs/heads/main` → `23e583b2af0258ae87c1a161b9272a8a43800c62`（无 tag、无其他分支） |
| 提交 | 1 个：`23e583b Initial commit` |
| 内容 | **仅 1 个文件** `README.md`（2 行：`# nana-core` / `Nana Core — portable AI agent architecture and development workspace`） |
| 体积 | 0 KB |

**结论**：远端是**近乎空的骨架仓库**，不存在需要保护的业务内容；唯一的「既有内容」是初始 README 那两行。

## 3. 关键阻塞：远端历史与本地历史**无共同祖先**

- 远端 `23e583b`（Initial commit）与本地 `2d93df1` **unrelated histories**。
- 本地 `README.md`（3138 B，中文项目说明）与远端 `README.md`（2 行英文）**内容不同**，且本地 README **不含**远端那两句。
- ⇒ 直接 `push master:main` 必定被拒（non-fast-forward）；
  `push --force` 会丢掉远端 `Initial commit` 与 README → **奈奈不做**（违反「不覆盖远端已有内容」）。

**候选方案**

- **A（推荐）**：`fetch` 远端 main → `merge --allow-unrelated-histories` → README 冲突**双方都保留**（把远端那两句并进本地 README 的合适位置）→ 产生 1 个合并提交 → `push master:main` 即为 fast-forward。
  远端历史与内容**零丢失**，无需 `--force`。
- **B**：只推新分支（如 `import/initial`）+ 开 PR 到 main，由姐姐点合并。
  优点：main 在被验收前零改动。缺点：姐姐仍需一次点击，与「退出日常传话」目标相反。

## 4. 凭据 / 敏感复扫口径澄清（重要）

- 全历史 blob 复扫：字面 `sessdata` 命中 **10 次**。
- 逐条定位：**全部是键名 / 文档描述**，分布为
  - `PROJECT_BRAIN/03_config_runtime.md`、`PROJECT_BRAIN/17_GITHUB_SYNC_RECON_01.md`
  - `src/bili_agent/bili_agent.py`、`src/bili_agent/bili_refresh.py`、`src/bili_agent/bili_send_core.py`（读取 cookie 用的 JSON key）
- **真实 `sessdata` 值**（正则 `sessdata":"<≥16 字符>`）命中 = **0**。
- 其他密钥模式（`sk-` / `github_pat_` / `ghp_` / `AKIA` / `BEGIN … PRIVATE KEY`）命中 = **0**。
- **口径修正**：此前「0 命中」应精确表述为
  → 「**密钥值 0 命中；`sessdata` 等键名出现属正常代码，不构成泄露**」。

## 5. 白名单登记缺口（本地已修，见 R8 提交）

| 项 | 白名单旧写法 | 实际 |
|---|---|---|
| `PROJECT_BRAIN/*.md` | 12 个（00–11） | **18 个**（00–17） |
| `src/bili_agent/*.py` | 10 个 | **12 个** |
| `bridge/**` | 未登记 | **9 个文件** |
| `docs/c5v_wiring_design.md` | 未登记 | 存在（`docs/*.md` 可覆盖，已注明） |
| `manifests/nana_iris_changes.diff` | A 类「允许入库」∧ C 类「条件入库」**自相矛盾** | 统一改为 **首发排除** |

## 6. 首次 push 拟清单（**待姐姐最终点头**）

- 源 → 目标：本地 `master` → `origin/main`（先执行方案 A 的无关历史合并）
- 文件：**66 个** = 本地 67 − 排除 `manifests/nana_iris_changes.diff`
- push 方式：**normal，绝不使用 `--force`**
- push 后：立刻进入 `@codex` 派单 → Codex 开 PR → **奈奈本地复跑测试 + 独立验收**
- 全程**不碰生产、不自动合并**

## 7. 未决 / 下一步

1. 姐姐点头：**方案 A** + 目标分支 `main` + 66 文件清单。
2. 凭据落位 `/root/.nana_secrets/github_nana_core_pat`（600），供后续自动化引用；remote URL **不带 token**，用 `GIT_ASKPASS` 取值。
3. Codex Cloud 侧：姐姐称「已连接 nana-core 仓库」→ 待用**最小真实任务**实测 `@codex` 是否真触发；不触发则直接报阻塞，不自研桥。
