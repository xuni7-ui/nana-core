# nana-core

## 工程恢复入口

先读 [Master Framework](PROJECT_BRAIN/00_MASTER_FRAMEWORK.md) 与 [Capability Matrix](PROJECT_BRAIN/01_CAPABILITY_MATRIX.md)，再读 [当前状态](PROJECT_BRAIN/09_STATE.md)。总框架已于2026-10-20冻结；能力进度按固定条件与证据核算。

> 奈奈工程（Nana）的**独立开发副本**与**权威事实源仓库**。
> 创建：2026-10-10 CST ｜ 维护：奈奈（Nana）

---

## 这是什么

`nana-core` 是奈奈工程对照 Codex Cloud 协作而建立的**独立、非生产**目录。它不是 AstrBot 的分支，也不是任一插件的镜像，而是：

- **事实源**：`PROJECT_BRAIN/` 记录奈奈工程的架构、源码、配置、验证状态。
- **开发副本**：`src/` 存放奈奈**原创**源码副本。
- **证据仓**：`manifests/` 存放白名单、敏感扫描、指纹与改动 diff。

> ⚠️ 本目录**不包含**任何生产数据、凭证、聊天记录、数据库或日志。

## 目录结构

```
nana-core/
├── AGENTS.md          # 本项目 AI 协作规范（奈奈工程专用）
├── README.md          # 本文件
├── PROJECT_BRAIN/     # 权威事实源（事实层 00–06 + 账本层 07–11，共 12 文件）
├── docs/              # 迁移报告 / 校验说明
├── manifests/         # 白名单 / 扫描报告 / 指纹 / diff / 拟提交清单
├── upstream/          # 第三方来源登记（不含其源码）
└── src/
    ├── plugins/       # 奈奈自制插件（4 个）
    ├── bili_agent/    # B站 Agent 外挂脚本
    └── c5v/           # C.5-V 感知骨架
```

## 快速导航

| 我想了解… | 去看 |
|---|---|
| 整体架构 | `PROJECT_BRAIN/01_architecture.md` |
| 有哪些源码 | `PROJECT_BRAIN/02_source_inventory.md` |
| 配置/数据在哪（不含内容） | `PROJECT_BRAIN/03_config_runtime.md` |
| 哪些做完/在做/没做 | `PROJECT_BRAIN/04_verification_status.md` |
| 第三方许可 | `PROJECT_BRAIN/05_third_party_licenses.md` |
| 风险 | `PROJECT_BRAIN/06_open_risks.md` |
| **现在到哪一步了** | `PROJECT_BRAIN/09_STATE.md` ⭐ |
| **接下来做什么** | `PROJECT_BRAIN/07_ROADMAP.md`、`08_TASKS.md` |
| **为什么这么定** | `PROJECT_BRAIN/10_DECISIONS.md` |
| **上次改了什么** | `PROJECT_BRAIN/11_CHANGELOG.md` |
| 能传什么/不能传什么 | `manifests/upload_whitelist.md` |
| 安全扫描结果 | `manifests/sensitive_scan_report_20261010.md` |

## 安全纪律（务必遵守）

1. **白名单制**：默认禁止，只有 `manifests/upload_whitelist.md` 列出的可入库。
2. **密钥零容忍**：发现硬编码密钥 → 阻断该文件并报告（不输出原文）。
3. **生产只读**：本目录**不**回写生产；生产改动需**明确批准**。
4. **4 核 / ~4 GB 资源约束**：禁止重型扫描、爬虫、死循环。
5. **不可逆操作（commit/push/deploy）须人类批准。**

## 当前状态

🟢 **P1 + P2 已完成（2026-10-10）**：事实口径已修正、证据改为四档制、项目账本（ROADMAP/TASKS/STATE/DECISIONS/CHANGELOG）已建立、本地 Git 版本控制已建立。
⏸ **未 push、未上传 GitHub、未改生产。**

详见 `PROJECT_BRAIN/09_STATE.md` 与 `PROJECT_BRAIN/11_CHANGELOG.md`。

---
*本仓库内容 DRAFT 状态。第三方版权归其原作者，详见 `upstream/sources.md` 与 `PROJECT_BRAIN/05`。*


---

## 附：远端仓库初始 README（原样保留）

> 来源：`origin/main` 首提交 `23e583b`（Initial commit）。合并无关历史时按「保留双方 README」原样保留，未删改。

# nana-core
Nana Core — portable AI agent architecture and development workspace

## 独立开发体验（无需 AstrBot / QQ）

```bash
.venv/bin/python -m nana_core.life init --home /tmp/my-nana-life --project "$PWD" --demo-materials --allow-local-artifacts
.venv/bin/python -m nana_core.life run --home /tmp/my-nana-life
```

原单主体 Runtime 可在无人输入时处理批准的真实源码材料、核验报告、从失败选择并
复用已验证的方法；可直接输入普通文本，或 `/status`、`/pause`、`/resume`、`/quit`。
默认无真实模型/外网/社交发送；离线语义与真实 provider 资格严格分开。
新环境安装、配置、删除/撤权与恢复见[最短用户指南](docs/nana_independent_life_quickstart.md)。
