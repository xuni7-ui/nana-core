# Nana Core 非生产网页与多工具工程验证

## P2 单工具里程碑（C-034）
[实测] 复用 ActionKernel、Grant、Attempt、预算、CapabilityRouter 和统一身份。WebSourcePort 只接受操作者冻结的 source URI → URL/GET/HEAD 绑定；模型只能引用 URI。路由新增可选 development_public scope，默认仍 synthetic_only，不新增 Core 表、依赖、生产适配。

PublicHTTPTransport 默认拒绝非 HTTP(S)、非标准端口、凭据/query/fragment、私网/回环/保留/元数据地址、混合 DNS、解析变化、重定向、压缩响应及超限响应；两次 DNS 检查，数字目标经既有受管代理发送，Host/TLS SNI 为原始域名。只在 HTTP unrestricted 且代理配置与平台策略匹配时启用，不尝试直连绕过策略。总截止时间覆盖 DNS、连接、头与正文。代理后的源站 peer 未直接验证，信任边界为平台代理和 TLS 校验，不声称端到端独立 peer 证明。

网页正文为 UNTRUSTED_SOURCE_DATA；原始 bytes/hash、来源 URL、实际 UTC 获取时间保留，HTML 摘要显式衍生且去脚本。定位只读取同一 Goal/Plan 已独立核验的历史回执，不再次联网。核验检查独立工具 journal 的完整原始数据及 hash，不代表网页现在仍相同。丢失回执时 UNKNOWN，禁止盲重试。

[实测] 对应命令：`.venv/bin/python -m pytest tests/development/test_public_http.py tests/development/test_web_source.py tests/migration --development-report docs/nana_core_development_evidence/web_single_tests.json`，84 passed / 0 failed。开发专项为 55 passed，S6 回归 29 passed；详情 web_single_output.txt。受控 HTTP 服务仅 loopback，不能计为公网或模型服务。

[实测] 单次授权公开 GET https://example.com：Core 动作 UNKNOWN，WEB_TIMEOUT；HTTP request attempts=0、proxy connection attempts=0，未取得正文/状态码。保留预算消耗和未决记录，不自动重试。证据 public_web_attempt.json；公网能力尚未运行验收。真实模型调用 0、模型费用 0，E12 NOT_RUN；不涉及生产账号/凭据/资料。

[文档] 许可证边界：新增代码为本仓库受控实现，无第三方源码复制或新增依赖；受控正文全合成。公开正文仅在实验 DB 中保存，不纳入仓库，不以工程许可覆盖来源内容许可；仓库整体 owner 授权仍见 LICENSES_AND_PROVENANCE.md。

P3/P4 的真实跨进程闭环与经验消融尚待执行，不能以本阶段单工具测试替代。
