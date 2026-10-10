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
