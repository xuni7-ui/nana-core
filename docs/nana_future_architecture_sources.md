# Nana Future Architecture — 来源、现状与阅读边界

设计基线：`ef7750e012a1004cbfb9d888319001f0b04154db`（R045）；本轮独立设计分支，不修改实现。

对全仓版本化文件做目录盘点：697 个文件，55 个 Core 文件；重点逐段阅读了下列实现及相关 PROJECT_BRAIN/验收文档。二进制归档、所有历史测试日志及每个辅助脚本未逐行复审；这不是全仓安全审计，也没有读取真实宿主或私人 Store。

本轮解析既有 R045 JUnit：763 个用例、762 passed、0 failed、0 errors、1 skipped；用时147.667秒是原记录。本轮设计没有重新运行这些测试。R044对应记录同数、94.238秒。E12仍NOT_RUN。

R045 final-summary 中 `R045_final_SHA=760e5e8...` 是包 support source，远端当前 HEAD 为上述 ef7750e；不得混用。旧账本“零代码”“无远端”等是历史快照，后续明确增补优先。

仓库不存在单独的、完整原始《Architecture V1》规范文件；本设计依据 S0–S6 实现报告、D-031 及后续裁决和源码，不声称读过未提供的原稿。

Approved 包从 ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513 获取55文件。当前 checkout 相对它已有一处历史 preflight Pydantic门差异；本轮没有修改。完整源码身份必须同时注明包Core SHA、support SHA、checkout SHA。

以下链接固定到本轮读取的 Git SHA，避免未来分支前进后行号漂移。设计文中的 [Sxx] 指向此清单。

## S01

最新工程事实与真实边界

[`PROJECT_BRAIN/09_STATE.md:606`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/PROJECT_BRAIN/09_STATE.md#L606)

## S02

五阶段前身、单 Runtime 与生产优先纪律

[`PROJECT_BRAIN/07_ROADMAP.md:57`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/PROJECT_BRAIN/07_ROADMAP.md#L57)

## S03

人格与独立判断的既有裁决

[`PROJECT_BRAIN/10_DECISIONS.md:8`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/PROJECT_BRAIN/10_DECISIONS.md#L8)

## S04

当前身份创建、数据库与恢复

[`src/nana_core/storage/sqlite_store.py:61`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/storage/sqlite_store.py#L61)

## S05

15 表与一个 live goal / 一个 plan 的真实约束

[`src/nana_core/storage/schema_v1.sql:39`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/storage/schema_v1.sql#L39)

## S06

严格但 reading 专用 DTO

[`src/nana_core/contracts.py:27`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/contracts.py#L27)

## S07

事务记录、原文复制和去重

[`src/nana_core/storage/sqlite_store.py:180`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/storage/sqlite_store.py#L180)

## S08

回放与备份隔离

[`src/nana_core/storage/sqlite_store.py:200`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/storage/sqlite_store.py#L200)

## S09

合成记忆检索与最小冲突判断

[`src/nana_core/memory.py:12`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/memory.py#L12)

## S10

reading 驱动、恢复与持久化唤醒

[`src/nana_core/runtime.py:9`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/runtime.py#L9)

## S11

上下文裁剪、固定计划和经验插入

[`src/nana_core/planning.py:6`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/planning.py#L6)

## S12

有限经验、验证与撤回

[`src/nana_core/experience.py:12`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/experience.py#L12)

## S13

动作状态机、权限、预算、UNKNOWN

[`src/nana_core/actions.py:6`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/actions.py#L6)

## S14

模型和能力 Ports

[`src/nana_core/ports.py:6`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/ports.py#L6)

## S15

开发模型端点与响应契约

[`src/nana_core/semantic/contracts.py:10`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/semantic/contracts.py#L10)

## S16

调用账本与 HTTP ModelPort

[`src/nana_core/semantic/model_port.py:16`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/semantic/model_port.py#L16)

## S17

原始提案与独立行为评分/E12

[`src/nana_core/semantic/evaluation.py:8`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/semantic/evaluation.py#L8)

## S18

模型能力选择，不授予权限

[`src/nana_core/semantic/selection.py:33`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/semantic/selection.py#L33)

## S19

initiative 是数字评估夹具且只激活 reading

[`src/nana_core/initiative.py:14`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/initiative.py#L14)

## S20

合成旧记忆信封与导入

[`src/nana_core/migration/legacy.py:12`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/migration/legacy.py#L12)

## S21

Iris 字段映射与可恢复导入

[`src/nana_core/migration/iris.py:16`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/migration/iris.py#L16)

## S22

Iris 锁定源码映射规范

[`docs/nana_core_phase3_iris_mapping.md:27`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/docs/nana_core_phase3_iris_mapping.md#L27)

## S23

单执行方 Router 是模拟/开发域

[`src/nana_core/migration/routing.py:24`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/migration/routing.py#L24)

## S24

执行与记忆 authority 仍为模拟协议

[`src/nana_core/integration/authority.py:26`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/integration/authority.py#L26)

## S25

Shadow draft 和实际 Action 分离

[`src/nana_core/integration/shadow.py:29`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/integration/shadow.py#L29)

## S26

宿主能力是 catalogue / 默认禁用

[`src/nana_core/integration/capabilities.py:18`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/integration/capabilities.py#L18)

## S27

受控开发能力仅 literal patch / 固定 AST runner

[`src/nana_core/integration/engineering.py:40`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/integration/engineering.py#L40)

## S28

metadata-only OneShotReceipt

[`tools/nana_astrbot_shadow/one_shot.py:49`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/tools/nana_astrbot_shadow/one_shot.py#L49)

## S29

Store binding 与单次原子消费

[`tools/nana_astrbot_shadow/one_shot.py:124`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/tools/nana_astrbot_shadow/one_shot.py#L124)

## S30

source seal 与 runtime proof 分离

[`tools/nana_astrbot_shadow/onboarding.py:145`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/tools/nana_astrbot_shadow/onboarding.py#L145)

## S31

默认生产 trust EMPTY

[`tools/nana_astrbot_shadow/sealed_trust.py:7`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/tools/nana_astrbot_shadow/sealed_trust.py#L7)

## S32

有界隔离 worker

[`tools/nana_astrbot_shadow/bridge_worker.py:22`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/tools/nana_astrbot_shadow/bridge_worker.py#L22)

## S33

真实 hook 覆盖有限，框架保证≠adapter纪律

[`PROJECT_BRAIN/03_config_runtime.md:80`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/PROJECT_BRAIN/03_config_runtime.md#L80)

## S34

Iris Semantic Gate 是检索策略

[`materials/iris_customizations/NEW_FILES/semantic_gate.py:165`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/materials/iris_customizations/NEW_FILES/semantic_gate.py#L165)

## S35

Iris 流水截断/保留期限

[`materials/iris_customizations/NEW_FILES/conversation_flow.py:44`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/materials/iris_customizations/NEW_FILES/conversation_flow.py#L44)

## S36

旧 B站发送仍有回包自证快路径

[`src/bili_agent/bili_send_core.py:316`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/bili_agent/bili_send_core.py#L316)

## S37

旧 B站事件泵重放限制

[`src/bili_agent/bili_event_pump.py:140`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/bili_agent/bili_event_pump.py#L140)

## S38

许可证与派生边界

[`LICENSES_AND_PROVENANCE.md:5`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/LICENSES_AND_PROVENANCE.md#L5)

## S39

R045 回归与包证据

[`docs/nana_r045_evidence/final-summary.json:1`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/docs/nana_r045_evidence/final-summary.json#L1)

## S40

R044 风险、恢复与测试证据

[`docs/nana_r044_evidence/final-summary.json:1`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/docs/nana_r044_evidence/final-summary.json#L1)

## S41

源码/宿主对照与已知 inode 环境差异

[`docs/nana_r045_merge.md:1`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/docs/nana_r045_merge.md#L1)

## S42

独立执行回执与结构化协作边界

[`bridge/codex_bridge.py:40`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/bridge/codex_bridge.py#L40)

## S43

时间解析和单调时钟

[`src/nana_core/clock.py:6`](https://github.com/xuni7-ui/nana-core/blob/ef7750e012a1004cbfb9d888319001f0b04154db/src/nana_core/clock.py#L6)
