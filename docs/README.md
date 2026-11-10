# 文档

从当前任务和使用入口开始，再按需要追溯历史。文档中的测试、部署和体验结论都只覆盖其明示版本与环境。

## 当前入口

| 目的 | 入口 |
|---|---|
| 从源码运行 | [独立 Nana 指南](guides/independent-life.md) |
| 安装便携包 | [包内 QUICKSTART](../packaging/portable/docs/QUICKSTART.md) |
| 使用 Web / Android | [Nana Space](../apps/nana-space/README.md) |
| 找到正式模块 | [源码地图](nana_next_experience/GOVERNANCE_SOURCE_MAP.md) |
| 接续开发 | [当前检查点](nana_next_experience/ACTIVE_CHECKPOINT.md) · [开放项](nana_next_experience/STATUS_AND_REMAINING.md) |
| 确认规范与状态 | [冻结总纲](../PROJECT_BRAIN/00_MASTER_FRAMEWORK.md) · [能力标准](../PROJECT_BRAIN/01_CAPABILITY_MATRIX.md) · [状态账本](../PROJECT_BRAIN/09_STATE.md) |

## 历史与验证材料

- [`archive/`](archive/)集中已移出的历史材料：[建仓 README](archive/repository/README-before-20261111.md)、[早期平台集成说明](archive/legacy-platforms/README.md)。
- `nana_*_implementation.md`、`nana_*_status.md`、阶段目录记录相应实现与版本背景，不是另一份最新状态。
- `*_evidence/` 与 `nana_next_experience/evidence/` 保存原始验证证据。历史失败、限定范围和未验收项继续保留。
- [`ADR/`](ADR/)保存架构决策；[`tasks/`](tasks/)保存既有任务卡。

有现役消费者、固定指纹或脚本引用的资料继续保留兼容入口；历史路径可结合原 Git 提交追溯。正式交付材料位于仓库的既有交付目录，按 selector、清单和摘要判断版本。
