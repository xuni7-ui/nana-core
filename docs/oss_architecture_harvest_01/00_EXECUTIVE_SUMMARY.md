# OSS-ARCH-HARVEST-01 — 源码研究结论

状态：RESEARCH_COMPLETE / DESIGN_ONLY。采集日 2026-10-16 UTC。没有实施 adoption。

Nana 实际基线：`dev/nana-core-relational-autonomy-v1-codex @ 67326d195edd0693d41eacc63fcc00e1c3205bd6`。
任务参考 `e26288e` 是祖先；不能忽略当前 PROJECT_BRAIN 已确认的 Relational 离线候选。
本研究分支 `dev/nana-core-oss-architecture-harvest-01`，不改业务源码、schema、测试、依赖、生产或 main。
当前能力是 OFFLINE / SYNTHETIC，不等于真实生活/模型/宿主已验收。

## 首要判断

Nana 缺的不是另一个 Agent framework。外部源码最有价值的增量，是把已有单一主体变得更及时、更省、更可检查，并改善长生命记忆的时间表达与检索质量。
比较均限于固定 commit 的已读路径；“Nana 更强”指明确的不变量/现有合成证据，不是没有做过的性能或人格效果排名。

| 排序 | 最值得借的机制 | 来源 | Nana 落点 |
|---|---|---|---|
| 1 | reactive/living 两种 cadence，用户到达唤醒、维护让路 | YuriOS turns/loop，Anima interruptible sleep | D 调度，同一 C SubjectLoop |
| 2 | 值得做与值得打扰分开评估 | YuriOS 两道 salience gate | C social 判断 + 后续独立 delivery authority |
| 3 | 低成本 appraisal、预算压力降低后台活动 | YuriOS policy/budget；Nana 已有 NO/LIGHT/FULL | D 资源机会；C 仍决定动机 |
| 4 | 可暂停、可恢复、小块后台维护 | YuriOS DREAM jobs；Letta worker | 同一 Store 的 source-linked proposal，单 writer 验证 |
| 5 | journal / decision / action / context 四类关联视图 | YuriOS trace/journal/promptlog | Nana authoritative records 的可删除派生投影 |

Nana 已较强的五个边界：① durable queue+lease epoch+commit recovery；② Grant/Budget/Capability/Manager/Verify 分离；③ UNKNOWN 不盲重试；④ PrivacyJournal+依赖删除闭包；⑤ identity/growth 的独立来源与 counterevidence，关系永不提权。
具体对照见 01、05、06，不把这些优势推广到未读路径。

## 必答二十问

1. YuriOS 最值得借的五项：上表五项，均 BORROW_PATTERN；不移植其第二套 reply brain。
2. Nana 更强五项：上段五项；SignalBus 明确不 replay，不等同 Nana durable ingress。
3. Graphiti temporal semantics：值得借。尤其 valid time / recording time / reference time，以及计划成立≠事件已经发生。
4. 第二图数据库：不需要。先做同一 Store 上的 TemporalFactView；图查询需求/性能尚无证据。
5. Letta tiers：借组织/可见性模式；HOT 不是更可信，非 system 内容也不等于无隐私。
6. Mem0：BENCHMARK_ONLY，先比较同一合成长生命语料；不替换 MemoryService。
7. LangGraph：BORROW_PATTERN；REJECT 作为 D 替换。checkpoint 不提供任意外部副作用 exactly-once。
8. Temporal：BORROW_PATTERN 概念；当前不安装。4GB 单 runtime 不值得新增 workflow 服务体系；未实测其 RAM。
9. dual cadence：YES，作为 D 的两种处理时限/机会，不是两个主体或两个 writer。
10. adaptive heartbeat：YES，deterministic bounded idle wait + incoming-event interrupt；不拿聊天频率定义人格。
11. Living Journal：YES，派生、最小隐私、source-linked；不能成为新的自传权威。
12. Background Maintenance：YES，低优先级窗口；DREAM 只是产品比喻，不是事实/身份自动认证。
13. one-intention-per-wake：保留“一个 cycle 最多一个 committed intention”，不强制有行动；不把它变成所有长期目标只能一个。
14. Memory 三个缺口：显式 temporal validity/as-of；语义/多样性检索实测；跨多轮 source-linked consolidation 的质量与删除闭包 qualification。
15. Runtime 三个缺口：当前同步 step+固定 sleep 没有完整用户抢占；call-count budget 不是准确 token/cost reservation；缺少可中断维护与四面关联运营视图。
16. Eyes/Hands：OpenHands SDK 的 action/observation/confirmation、Comma 的 device/session admission、OpenWatari 的 thin edge；均 FUTURE_STAGE。
17. 更强社交：独立 appetite（Nana 已有）+具体历史召回+interruption gate+delivery 状态分离+silent journal。不是更频繁联系。
18. 伤害 Primary Bond 的模式：把用户 profile 当 Subject identity、互动量当关系质量、同意当奖励、单一 affection 总分、空闲强制说话、设备掉线就新建另一个主体。
19. 绝不引入：LLM直接写权威事实/人格；dream→truth；Git历史当彻底删除；计时器→承诺/外发；checkpoint→盲重试；第二 Store/第二 SubjectLoop；AGPL代码无审查复制。
20. ONE milestone：**D-V2 Bounded Preemptible Cadence**，见 11：同一队列/lease/SubjectLoop，incoming wake、deadline-aware wait、可暂停后台 slice、可验证延迟/成本。

## 证据与导航

01 YuriOS；02 Graphiti；03 Letta；04 Mem0；05 Runtime matrix；06 Memory matrix；07 Autonomy；08 Relationship；09 License；10 Adoption；11/12 概念；13 Eyes/Hands；14 拒绝；15 未决；16 逐项目统一档案；17 研究验证。
固定 SHA、文件 hash、实际阅读范围、许可证、活动时间见 `sources_manifest.json`。阅读范围是实读片段，不冒充每个仓库全量审计。
上游完整套件/模型/服务未运行。11 个隔离语义/抽象边界检查通过（含上游失败处理观察），不能当作上游系统或 Nana 新能力验收。
新源码引用只指 public source；未导入第三方业务代码、模型权重、私人文件。
