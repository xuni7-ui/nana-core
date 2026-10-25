# 冻结框架与当前状态对齐

本次阅读对象为独立 checkout 的 `e1679b2010c2d49148c9b99b096b9947dfdba8ff`。它在用户给出的 `d695ed7d47a33cb3df62a144908df30b7d7c693d` 之后有三个提交：Precision baseline、因果任务图/局部重规划、未知检查点恢复加固。

## 依据与当前事实

- 规范：[00_MASTER_FRAMEWORK.md](../../../PROJECT_BRAIN/00_MASTER_FRAMEWORK.md)，版本 1.0 FROZEN；十域、三轴和修改门不变。
- 资格：[01_CAPABILITY_MATRIX.md](../../../PROJECT_BRAIN/01_CAPABILITY_MATRIX.md)，固定 63 criteria；S1–S9 在明示受控范围全部 Foundation Qualified。S10-C05/C06 两高级项 UNKNOWN，不是本次前端或 First-Life 的基础前置。
- 当前任务：[09_STATE.md](../../../PROJECT_BRAIN/09_STATE.md) 顶部 `CORE_PROJECT_CURRENT_STATE_V1`，revision 30，workstream `PRECISION_ARCHITECTURE_OPEN_WORLD_INTELLIGENCE_UPGRADE_V2`，状态 `IMPLEMENTED_TARGETED_TESTED_FINAL_QUALIFICATION_PENDING`。
- [07_ROADMAP](../../../PROJECT_BRAIN/07_ROADMAP.md) 与 [08_TASKS](../../../PROJECT_BRAIN/08_TASKS.md) 的 Precision V2 P1 块已同步：23 targeted PASS；heldout、全仓、portable 等最终资格待验。

09 中大量历史 CURRENT 标题保留。当前状态必须按顶部 typed contract 的 revision、as_of、scope 和 evidence refs 理解；不能抓取任意旧段落生成“当前生活”。工程状态是外部 PROJECT 事实，不是奈奈个人经历。

原 24h Foundation 开发驻留资格与后来 Controlled World 中断的 ≥5h Advanced 资格是不同版本和范围。后者仍为 `PARTIAL_EXTERNAL_LIMIT`，不由时间流逝补成 PASS；Human `NOT_RUN`、First-Life `NOT_READY`、Beta `NO`。Nana Space 的 Demo、前端测试和视觉效果不改变这些状态。

## Surface 如何表达十域

| 冻结域 | 前端承载 | 权威边界 |
| --- | --- | --- |
| S1 Subject / Identity | 来源模式、Subject ID、连续性信息 | 不创建或选择第二个活跃 lineage |
| S2 Memory / Experience | 共同记忆、来源、纠正、撤回、生活手记 | 浏览器内容不自动成为真实记忆 |
| S3 Motivation / Affect / Relationship | 公开关注、关系与分享、允许不同意见 | 不推算人格、情绪、愿望或亲密度分数 |
| S4 Runtime / Living Presence | 当前活动、休息、恢复、断线状态 | 不运行第二个 SubjectLoop 或调度意志 |
| S5 World / Perception / Cognition | 世界研究、证据、矛盾、不确定性 | 观察、模型推断和结论保持不同来源 |
| S6 Judgment / Goals / Planning | 自主/用户/共同目标、依赖、计划变化 | 用户提议不直接等于采纳、Grant 或执行 |
| S7 Hands / Action / Verification | 阻塞、动作结果与独立核验 | UNKNOWN 不盲目重试；模型措辞不是成功证据 |
| S8 Learning / Self-Evolution | 测试、留出、后续复用、反例和暂停 | 开发者修代码不是奈奈学习；不强制学习 |
| S9 Self-Extension | 技能候选、资格、复用和退休 | 安装或启用按钮不创造新权限 |
| S10 Lineage / Deep Evolution | 恢复入口、谱系与未来扩展位置 | 不宣称深层 Core 自改已接入 |

Shared Life 与 Independent Life 同时保留：空间可以表达共同经历，也允许研究、安静、休息和不分享。Platform/Surface/Embodiment 扩大窗口，不扩大主体数量。Manager/Authority/Privacy/Recovery 限制外部后果，不替奈奈决定思想或愿望。

必须始终保持：

```text
One Subject / One authoritative Store / One SubjectLoop / One active lineage
C = WHAT / WHY；D = WHEN
Desire ≠ Permission；Relationship Importance ≠ Execution Authority
UNKNOWN ≠ Failure；MODEL_DERIVATION ≠ RAW_OBSERVATION
```

## 与 Precision V2 并行

源码只在 `apps/nana-space/` 实施；工程记录仅追加 changelog。未修改 SubjectLoop、Store、Runtime、Kernel、Planner、Learning Core、Master、Matrix 或 09 当前状态；未访问另一会话 staging，未运行生产或私人数据库。

正式接入时重新读取 Precision 最终交付版本，更新版本化映射并定向测试。当前 `VERIFIED_TASK_PREFIX_V1` checkpoint 是有时效的独立证据，不是永恒世界事实或执行授权。机械动作成功与任务质量 Experience 分开呈现；补偿也必须是新授权动作，不能伪装世界已回滚。

读取时的 SHA-256 仅证明文档快照，不证明运行态：

```text
00_MASTER_FRAMEWORK.md fe6efe121a05145b44178d5ec26b99430a28e873fca8d1b80f16671c65e5133c
01_CAPABILITY_MATRIX.md 2c0ca3893ec55cbb9f7c1b91b542eef37c627f0edbb2b4d49d888443f959cdf5
09_STATE.md fa28ba6912219a6c078a12bc17c5750a4490b786690305b2108548491ce9fdde
```
