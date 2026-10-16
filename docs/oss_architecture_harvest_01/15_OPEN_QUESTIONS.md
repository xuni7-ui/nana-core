# Open questions / 不能从本研究推出什么

1. Dual cadence的desired foreground latency与fairness：需离线压力实验定基线，不能先写营销SLA；最长同步C transaction/ModelPort safe point是主要约束。
2. Future真正provider的tokenizer、usage settlement、cancel语义/UNKNOWN reconciliation未跑；E12 NOT_RUN，不用mock替代。
3. Background维护worker究竟只返回candidate还是可执行index rebuild？建议proposal/索引计算可并行，authority commit一处；单Store不是禁止所有worker。
4. Multi-goal adoption与legacy one_live_goal约束：C候选多不代表E执行多，后续单独裁决，不能此次默默删index。
5. TemporalFactView完整bi-temporal存量迁移：原数据没有的validity必须UNKNOWN，不能从event_time批量伪造。
6. benchmark中“correct fact”由synthetic independent gold决定；Memory quality/自然表达/Primary Bond体验没有本轮真实模型数据。
7. Letta当前主repo已迁移、tomo旧curator/poster/planstore名字不匹配、OpenWatari上游身份未知；sources manifest明确版本，后续按实际symbols比较。
8. Mem0 Cloud Dream/Synthesis/Merge/Supersede、graph与advanced temporal不在已读OSS实现，UNKNOWN；若未来纳入需独立授权/源码，不把平台宣传当证据。
9. Graphiti多driver temporal过滤等价性和delete闭包没有测试。当前只执行独立normalize函数，不是完整Graphiti验证。
10. 4GB machine运行Temporal/Graphiti/embedding的真实RAM/CPU/latency没有测量；不建议为了研究去装重服务。
11. 代码许可证root只是初审；model/voice资产、vendor、服务terms、AGPL网络分发需具体集成时复核。本轮BORROW_CODE=NONE。
12. LivingJournal是否含自然语言？建议先semantic record view；未来renderer必须不编造effect、不输出内部隐藏推理或无授权敏感治理正文。

以上不是阻塞研究交付的架构冲突；都不能成为提前扩大authority的理由。
