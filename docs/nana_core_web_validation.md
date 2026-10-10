# Nana Core 非生产网页与多工具工程验证

## P2 单工具里程碑（C-034）
[实测] 复用 ActionKernel、Grant、Attempt、预算、CapabilityRouter 和统一身份。WebSourcePort 只接受操作者冻结的 source URI → URL/GET/HEAD 绑定；模型只能引用 URI。路由新增可选 development_public scope，默认仍 synthetic_only，不新增 Core 表、依赖、生产适配。

PublicHTTPTransport 默认拒绝非 HTTP(S)、非标准端口、凭据/query/fragment、私网/回环/保留/元数据地址、混合 DNS、解析变化、重定向、压缩响应及超限响应；两次 DNS 检查，数字目标经既有受管代理发送，Host/TLS SNI 为原始域名。只在 HTTP unrestricted 且代理配置与平台策略匹配时启用，不尝试直连绕过策略。总截止时间覆盖 DNS、连接、头与正文。代理后的源站 peer 未直接验证，信任边界为平台代理和 TLS 校验，不声称端到端独立 peer 证明。

网页正文为 UNTRUSTED_SOURCE_DATA；原始 bytes/hash、来源 URL、实际 UTC 获取时间保留，HTML 摘要显式衍生且去脚本。定位只读取同一 Goal/Plan 已独立核验的历史回执，不再次联网。核验检查独立工具 journal 的完整原始数据及 hash，不代表网页现在仍相同。丢失回执时 UNKNOWN，禁止盲重试。

[实测] 对应命令：`.venv/bin/python -m pytest tests/development/test_public_http.py tests/development/test_web_source.py tests/migration --development-report docs/nana_core_development_evidence/web_single_tests.json`，84 passed / 0 failed。开发专项为 55 passed，S6 回归 29 passed；详情 web_single_output.txt。受控 HTTP 服务仅 loopback，不能计为公网或模型服务。

[实测] 单次授权公开 GET https://example.com：Core 动作 UNKNOWN，WEB_TIMEOUT；HTTP request attempts=0、proxy connection attempts=0，未取得正文/状态码。保留预算消耗和未决记录，不自动重试。证据 public_web_attempt.json；公网能力尚未运行验收。真实模型调用 0、模型费用 0，E12 NOT_RUN；不涉及生产账号/凭据/资料。

[文档] 许可证边界：新增代码为本仓库受控实现，无第三方源码复制或新增依赖；受控正文全合成。公开正文仅在实验 DB 中保存，不纳入仓库，不以工程许可覆盖来源内容许可；仓库整体 owner 授权仍见 LICENSES_AND_PROVENANCE.md。

P3/P4 的真实跨进程闭环与经验消融尚待执行，不能以本阶段单工具测试替代。

## P3/P4 跨进程闭环（C-035）
[实测] 新增 `python -m nana_core.development.web_lab --output <不存在的开发目录>`（安装后的入口 nana-web），复用 ReadingCard 模板、FixtureModel、PlanCompiler、ExperienceEngine 与既有两库。父进程只启动合成 loopback HTTP 服务；8 个顺序工作进程（7 正常退出、1 SIGKILL）继承 PATH/PYTHONPATH，不继承凭据变量。不会同时常驻第二个 Runtime。

纵向链路：合成研究观察→同一身份/原始事件→严格计划→既有 Grant/预算/单执行方→网页 GET→独立 journal 原文/hash 核验→合成卡片→带来源引用的 WEB_CITED_RESULT（来源 URL、实际获取 UTC、原始事件 UTC、read action、核验 event/artifact ID、FULL 原始证据及 SUMMARY 标注）→反馈受限经验→冻结已关闭两库→新进程新事件→实际定位→写卡。完整网页不进入模型权威或权限，正文中的 ignore grants 仍是不可信引用文本。

冻结 snapshot 两库逐字 hash 相同；with/without 两组观察和夹具提案相同，只由操作者撤回对照组策略。with 实际 read→locate→create；without 实际 read→create。locator 精确使用同 Goal/Plan 已核验 read 的 action ID、verification event、原始字节 hash；card 真实保存该 locator，非仅输出计划。经验未修改 Grant、预算或身份约束。本实验只证明受限规则的因果行为差异，不证明真实模型理解。

[实测] CLI 的 18 条检查均成立，5 次实际 loopback GET、0 次公网 HTTP、0 模型；独立测试同样 5 次。真实 SIGKILL exit -9 位于 GET 完成且工具独立 journal 提交后、Core 本地回执丢失前；恢复前 DISPATCHING，恢复进程 proposal=0/GET=0，后续 locate/card 正常完成。若崩溃发生在 GET 已发出但 journal 尚未提交，仍 UNKNOWN、禁止 refetch（单工具缺失回执测试覆盖），不声称可恢复不存在的证据。

限制定位授权时，read 已核验、locate AUTH_REQUIRED、goal BLOCKED；再重启仍 BLOCKED、GET=0、card 没有新副作用。重投事件与完成后重启不增加目标或卡片。

专项 `pytest tests/development/test_web_source.py tests/development/test_web_lab.py`：20 passed / 0 failed；实控 HTTP 14 次（web_source 8 GET+1 HEAD、跨进程实验 5 GET）。新增 HEAD 明确 HEAD_NO_BODY，不冒充文档全文；HEAD 不建源缓存、无法创建阅读卡。locator 文本/上游 action/hash 三类篡改均独立 FAILED_EFFECT，阻断卡片。

证据：web_continuity_report.json/web_continuity_output.txt（实际 CLI），web_multitool_tests.json/web_multitool_output.txt/web_multitool_proof.json（实际测试）。此前代理/DNS 公网尝试仍 UNKNOWN，不自动重试；真实模型和公网端到端均未运行验收。S0—S6 最终全量回归待下一检查点。

[实测] 修正记录：新增 HEAD 测试首轮 18 pass/1 fail，测试曾预期 UNKNOWN，但已有 FakeWorld 的完整独立查询给 FINAL_NO_EFFECT，正确终态为 NOT_APPLIED/goal FAILED；改为更明确断言后19 pass。实际缺口为 HEAD 的顶层 body_coverage 曾是 FULL，现改 HEAD_NO_BODY 并加入独立核验与断言。未删测试、未放宽授权或状态机。

## P5 最终统一回归与交付（C-036）
[实测] 最终命令：

```bash
NANA_DEV_ENGINEERING_PROOF=docs/nana_core_development_evidence/final_integration_proof.json \
.venv/bin/python -m pytest tests/offline_continuity tests/semantic_migration tests/migration tests/development \
  --development-report docs/nana_core_development_evidence/final_engineering_tests.json \
  --junitxml docs/nana_core_development_evidence/final_junit.xml
```

228 collected：**227 passed / 0 failed / 0 errors / 1 skipped**，11.31s。S0—S4 56 passed、S5 engineering 42、S6 29、开发100；唯一跳过 E12 真实双模型。对应最终 stdout、JUnit、proof 均入库，无测试删除或关键断言降低。

最终回归实际26 loopback请求：12 POST模型协议模拟器 +8 GET/1 HEAD网页专项 +5 GET跨进程实验；独立CLI额外5 GET。公开只读尝试单次在DNS超时、HTTP与代理连接0；不计为成功请求且UNKNOWN未盲重试。真实模型0、生产0、模型/外部服务费用0；模拟预算单位并非真实货币。

| 里程碑 | 结果 | 已核对远端提交 |
|---|---|---|
| P0 恢复保存 | PASS，原成果保留，截图未提供不能据图认定 | b05468d63182c17644037be447688798fa5ce6b4 |
| P1 ModelPort 工程收尾 | 81 targeted passed | 0d13ecc8ed84ee9c0cd3e28b19cf0cfed00fe5db |
| P2 授权只读网页 | 84 targeted passed，真实公网未验收 | ccad1a2b9811eec853b4ecc908649ac3cc532de9 |
| P3/P4 引用结果、恢复、经验与多工具 | 20 targeted passed；CLI18checks | fced7f8204b82da03e6fc9d60fe73e29727c3d0c |
| P5 最终回归/证据 | 227 passed /1 skipped；最终SHA以Git/ls-remote及交付报告为准 | 本检查点提交 |

分支 `dev/nana-core-v1-dev-validation`，私有 xuni7-ui/nana-core；无 main 合并、生产部署或生产树改动。开发 URL绑定持久化、路由scope显式，不接真实私人材料。Core schema v1与两库基础未变，零新增依赖。版本化验收汇总 final_delivery.json。

### 权限类别和未知边界

详见既有 access_boundary.json / nana_core_development_validation.md。已确认 GitHub 开发推送可达、公开 HTTP 网络策略 unrestricted（不是生产鉴权证明）；元数据仓库 GET成功、workflows0、hooksGET403。默认沙箱 Docker socket 请求 PermissionError，拒绝阶段未记录；未申请解锁、未连接生产daemon或登录SSH。

可见配置无就绪生产SSH/凭据绑定，无生产命名挂载；/root候选元信息权限拒绝。生产鉴权、SSH网络可达、泛名卷来源、Docker生产关联、webhooks/外部轮询均**无足够证据判断**。不得将“未发现”写成“绝对不可访问”；也不能保证dev push不会被未知外部部署系统监听。没有执行生产探测或读取密钥值。

### 未验证与最短路径

1. 公开 DNS 当前不可用；一次失败后未尝试绕过代理或盲重试。需开发环境支持合规DNS解析及代理numeric CONNECT/Host/TLS路径，再为新的操作者明确授权动作执行一次受限GET核验。现有UNKNOWN不自动重发；其证据不能凭未来成功补造。
2. E12保持NOT_RUN。需要两个经操作者核实的真实开发端点、service_kind=real_model、development/existing_quota或真实local_offline、独立NANA_S5_DEV_*绑定与调用/费用预算，运行既有nana-semantic冻结身份快照/未见案例/双模型顺序/消融；模拟器不替代。
3. 当前计划模板只有reading_card，结果是可追溯私有阅读卡；未实现通用网页研究推理、多模态/浏览器/登录/爬虫、真实写工具或生产迁移。将来验证真实模型对不可信网页的理解需要独立语义任务；本轮不能因夹具工程通过声称已具备。
4. 代理信任与受信Python进程边界仍在；不是恶意插件OS沙箱或公网peer独立证明。GET后journal落盘前崩溃可保持UNKNOWN但不能重建消失的正文。
5. 私有仓库原创许可证仍待所有者决定；本轮没有引入可替代既有核心的大框架或新依赖，不涉及派生代码迁移。
