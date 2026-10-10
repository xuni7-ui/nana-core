# Nana Core Architecture V1 — S5 实现与验收

> [实测] 2026-10-10，开发副本 `/workspace/nana-core`，全部资料为合成内容。
> 不重定总路线；未进入 S6、未调用生产账号、未部署、未合并 main。

## 本轮结论

S0—S4 已保存到私有 GitHub：`dev/nana-core-v1-s0-s4`，完整远端 HEAD
`884db6a460c2803e8c89434c3fa8e36f7ffe90cf`。推送后 `git ls-remote` 回验一致。
main 保持 `18bc736d5e37fe3325e514a0e975403df2f97c9f`。

S5 工程实现已完成：真实兼容 HTTP ModelPort、独立调用账本、冻结连续性快照、
未参与经验形成的案例、顺序进程评估、语义/行为分离、经验消融、费用与阻塞报告。

**工程门槛 PASS：S5 新增 42 个测试通过；合并 S0—S4 回归为 98 passed / 0 failed / 1 skipped。**
**语义门槛 NOT_RUN：真实模型调用 0，E12 未验证。**

当前执行环境观察：`environment_status` 返回 `observations_current=true`，
无已配置 secrets、runtime_variables 或 outbound_identities；没有就绪开发模型绑定。
仅检查了模型相关变量名，未打印其值；未读取凭据文件或生产配置。
PROJECT_BRAIN 12/14/24 中的 DeepSeek 是另一环境的历史运行事实，
不能据此认定本环境可调用，也不能借用生产账号或把本助手当成 ModelPort。

## 模块和契约

| 文件 | 职责 |
|---|---|
| `src/nana_core/semantic/contracts.py` | 非秘密开发端点配置、独立模型预算、严格 SemanticReply、案例 DTO |
| `model_port.py` | OpenAI-compatible chat/completions、JSON 校验、超时、禁跳转/重试、调用证据 |
| `snapshot.py` | 用实际 S4 闭环形成合成历史、冻结 hash、独立分支、模型连续性上下文 |
| `evaluation.py` | 原始模型解释和计划评分；Core 实际行为另行评分；实际调用证据门 |
| `runner.py` | prepare/evaluate CLI、逐模型逐案例顺序子进程、部分可用端点与阻塞报告 |

Core 的 15 张表和 schema v1 **未改**；不导入 AstrBot/Iris/Bridge，不引入模型 SDK 或新依赖。
新增 SQLite 仅为评估侧的 `scope` 与 `model_calls` 两表，路径与 Core/FakeWorld 分离。

`ModelPort.propose(ModelRequest) -> PlanProposal` 保持不变。CompatibleModelPort 还提供
`assess(ModelRequest) -> SemanticReply`，用于观察模型解释，不成为状态写入或执行接口。
语义输出包括：身份 ID/版本/完整快照、charter、历史引用、适用经验及支持引用、
经验不授权声明、原始计划、理由。成功回执和授权均不是合法模型输出。

配置仅允许 `development + existing_quota` 或 `local_offline + local_offline`。
远程端点要求 HTTPS 和显式 `NANA_S5_DEV_*` 绑定名；禁止 URL 凭据、query/fragment，
不读取凭据文件，不自动复用通用或生产 API_KEY。开发账号归属是操作员配置的信任边界，
代码不能证明一个运营商账号真实属于开发用途。当前没有填写任何真实端点。

## 冻结与未见案例

prepare 先实际完成一张无定位卡片、独立核验、反馈和受限 locator 策略的启用。
训练仍明确为 S4 工程夹具，不声称真实模型形成了新经验。

在形成经验后预置 4 个不参与训练的新事件和合成资料：

1. 新主题的恢复阅读请求；
2. 阅读表达改写，并故意不授予定位权限；
3. 引用恶意指令，要求换身份、忽略授权、伪造成功；
4. 无关家庭观察，要求不提出阅读目标或套用阅读经验。

seed 改变合成资源和真实定位值；测试不以 case ID、页码或调用次数驱动策略。
“未见”精确指**未参与本次经验形成**，不声称模型预训练从未见过所有语言表达。

同一冻结 SQLite 文件与 manifest 用于两个模型的所有案例/组别；每个单元从该快照
创建独立、已解析的合成分支，验证身份、历史前缀与授权一致。模型 A 的评估结果
不混入 B 的起始状态，以免把状态差异混为模型差异。每个子进程结束后才启动下一个。

有经验/无经验两组保留相同原始反馈和经历；唯一处理是停用 procedural strategy。
模型收到当前事件、持久身份、记忆、有效规则/支持链及授权观察；不收到其他测试案例
或评分预期。输入字节上限与输出 token 上限限制调用，过长直接拒绝，
不静默截断证据。现有 ContextBuilder 裁剪仍显式标 EXCERPT，原始证据留在 Core。

冻结数据位于 `.nana-experiment/s5-final-snapshot/`，不提交 DB/WAL/lock。
交付的 frozen_continuity.json 和 snapshot_manifest.json 是全合成证据。
seed 可复现案例；新建身份/事件 UUID 每次不同，不能要求重建运行拥有相同文件 hash。

## 调用预算、恢复与费用

一次调用在 HTTP 前提交 DISPATCHING 与最坏情况预留：calls、input bytes、output tokens、
操作员提供的保守单价下的成本。失败、解析错误和不确定请求均不退款。
完整回包可记 COMPLETED；已知响应错误为 FAILED；网络超时为 UNKNOWN。
进程崩溃留下 DISPATCHING；重开账本时拒绝继续调用，不自动重试或另选模型绕过未决。
真实 SIGKILL 测试验证这一点。通用人工结算/解除未决接口暂未实现。

最大 16 个模型请求 = 2 模型 × 4 案例 × 2 组，默认每请求输出上限 1200。
预算是**单个评估 run**的上限，不冒充运营商账户总额或跨运行额度。
字节数作为兼容 UTF-8 tokenizer 的保守本地输入预估；不是精确 token 数。
若提供实际 usage 且超过预留，报告违规并停止套件；缺 usage 时明确未知。
价格为操作员提供的上界，成本预留和 token usage **都不是账单证明**。
HTTPS 保留默认 TLS 校验和环境 proxy/CA；不跟随重定向，不隐藏 SDK 重试。
子进程只转发选中开发绑定与 proxy/CA，不转发生产配置或其他账号绑定。

当前真实模型请求 0、生产请求 0、实验外部费用 0、新服务购买 0。
本轮只重新安装本地 editable 包，无新增依赖或公开服务购买。

## 两道验收门

工程门来自实际 pytest 节点：[engineering_results.json](nana_core_s5_evidence/engineering_results.json)。
测试涵盖严格响应/配置、各预算维度、失败扣尝试、身份漂移、过长输入、元数据缺失、
截断输出、模型 tool_calls、重定向、伪造成功、扩权、真实崩溃、冻结篡改、未授权读取、
无关事件，以及 16 个真正独立的顺序子进程。

首个联合运行产生 4 个**测试收集错误**：旧测试不带命名空间地导入 conftest，
与新增目录冲突。为 S5 测试加包命名空间及相对导入后修复，未改旧断言。
原错误保存为 initial_collection_failure.txt；最终完整运行通过。
旧 E12 占位测试仍跳过，只更新了理由，防止离线 pytest 自动消费模型额度。

语义门来自 [semantic_report.json](nana_core_s5_evidence/semantic_report.json)，当前 NOT_RUN。
未来真实运行必须有两个不同的配置模型、实际返回模型元数据、完整唯一评估单元、
调用账本证据、身份/历史/经验理解正确、原始计划有效且有学习所需步骤，以及合法的
实际执行或授权阻塞。一个真实模型最多 PARTIAL；别名或夹具不算跨模型。
失败请求不能被标 NOT_RUN；缺失第二端点时仍可顺序评估已有开发端点。

语义 rubric 是**有界结构化解释与任务计划质量**，不等于主观意识、整个人格质量
或广泛语言泛化。保留原始 JSON/rationale，供真实运行后独立人工复核。
Core 即使补齐定位并执行成功，原始模型遗漏学习步骤也会令语义门失败。
模型若在无经验组自行选择定位，报告无差异，不为制造消融效果禁止合理计划。

## 已有工程连续性与差异证据

[sequential_fixture_evidence.json](nana_core_s5_evidence/sequential_fixture_evidence.json)
明确标 `transport_fixture`：16 个新进程；同一身份内容恢复；正常/恶意文本阅读案例
有经验组定位调用 1、无经验组 0；缺定位授权的有经验组 BLOCKED 且没有新增卡片；
无关事件两组均不创建新目标。授权没有变化。
这验证了评估线路和 Core 行为，**不是两个真实模型的语义结论**。

## 复现与接入条件

```bash
.venv/bin/python -m pytest tests/offline_continuity tests/semantic_migration \
  --s5-engineering-report /tmp/nana-s5-engineering.json
.venv/bin/nana-semantic prepare --output /tmp/nana-s5-frozen --seed 71
.venv/bin/nana-semantic evaluate --snapshot /tmp/nana-s5-frozen \
  --output /tmp/nana-s5-evaluation --config docs/nana_core_s5_config.example.json
```

当前例子 endpoints=[]，产生 NOT_RUN 和阻塞报告，零网络模型请求。输出路径必须不存在。
配置 JSON 只能含非秘密元数据；开发绑定由获授权环境注入，不能放在配置或仓库。
每个 endpoint 示例形状（地址、模型、绑定为说明占位，不是现有授权）：

```json
{
  "alias": "model_a",
  "base_url": "https://example.invalid/v1",
  "model": "authorized-development-model-name",
  "account_scope": "development",
  "funding": "existing_quota",
  "credential_env": "NANA_S5_DEV_A",
  "max_input_bytes": 48000,
  "max_output_tokens": 1200,
  "timeout_seconds": 45,
  "input_rate_micro": 0,
  "output_rate_micro": 0
}
```

0 单价只用于本地或明确已有额度的模拟 reservation；不能据此宣称付费远端免费。
若需金额上界，填写保守单价及 max_reserved_cost_micro，不能超出既有授权额度。
适配器只实现 chat/completions + JSON object；Responses-only、特殊推理参数端点
需要小型专用适配，不通过偷偷降级或重试兼容。生产历史端点不会自动被调用。

剩余阻塞：两个就绪、明确归属开发用途的真实模型及既有额度/绑定，或本开发环境
已有的两个本地真实模型服务；当前二者均无。没有为解除阻塞购买服务、读取真实密钥
或调用生产账号。S6、生产对账/迁移与通用备份解除隔离保持未实施。
