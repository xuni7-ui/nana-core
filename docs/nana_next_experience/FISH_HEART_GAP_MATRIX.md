# Fish Heart 设计借鉴差额矩阵 — 同一十域精修主任务

Advanced Growth / S3+S4+S2+S6+S8；不改 Master、63 criteria、主体/Store/Loop 或任何执行权限。起点9562f4f，远端相同；上一批 Core6f2a491 完整回归1905通过/12显式跳过。旧工作成果保留，软件优化没有取消。Iris v2已上线收口及云端恢复由用户/运行负责人报账，本地无当前宿主访问绑定，不假称核验在线状态。

参考固定为 Vivy33/astrbot_plugin_fish_heart `new@6a338343e2427a9173cf8860f0519ff912194e34`，metadata版本0.3.8，MIT（LLL/Vivy33）。只读研究，不运行或安装插件。源码/许可证指纹见 upstream/fish-heart-reference.json；许可保留 upstream/licenses/fish-heart-MIT.txt。以下为思想对照，未复制插件实现。

| 机制 | 原 Core 实现与实际范围 | 差额/本轮选择 |
|---|---|---|
| 短期心境与长期关系分开 | subject/policy.py Appraisal、relational/projections.py appetite、autonomy/relationships.py 多方面关系；人格/身份不等于当下活动 | 复用，不造九维分值。时间状态与源支持先检查，不能凭聊天感觉重设人格 |
| 随时间变化/重启补偿 | ConcernCue.valid_until_us、RelationshipDetails.valid_until_us、world_loop/attention.py 三天未更新候选退役；UTC发生/观察时间与持久Store | 已有绝对时间重算，不补发停机期间消息。长期关系不能因时间静默自动归零；进一步场景验证 |
| 同事件重复收益递减 | Growth._roots 对人格/兴趣断言按原始证据去重；ConcernService.offer当前仅比较Memory ID并encounters+1 | 明确缺口：同一观察的不同派生记忆可能被当作多个独立遭遇，促成INTEREST/再次唤醒。优先增强为原来源根比较，保留新真实来源的机会 |
| 念头持续/完成/放下 | open_concerns的TRANSIENT/INTEREST/DEFERRED/PROPOSED/ABANDONED/EXPIRED，原Intentions及Goal生命周期；S3 ExperienceNeed OPEN/SETTLED | 直接增强既有Concern，不能建立另一个thought_engine；无目标的念头也不应为了主动而强制发言 |
| 冷却与主动选择 | next_review_us、原C WATCH/REST/IGNORE/EXPLORE、DeliveryAdmission与RecipientState、quiet window | 已有，时间只安排机会；不抄随机说话概率、强制索取回应或惩罚性沉默 |
| 主动草稿与真实经历 | life/shared.py只从独立Verify的实际经历产生候选；C/Manager/Privacy/Delivery逐项约束；conversation/person_self保留来源 | 来源与草稿语义仍分开；不是有效citation就证明每个自然语言细节。实时模型/真人自然度未验，不冒充自动事实验证完成 |
| 第三方转述/对象归因 | 事件entity/scope/source、subject ingress admission、source-aware memories及PersonSelf reported speech；没有负面关键词扣亲密度 | 已具备基础，继续场景复核；不把引用、群聊旁观或模型推断升级为直接用户评价/执行权 |
| 晚安/忙碌/安静 | 原RecipientState availability/expiry、quiet_timezone/quiet window、DELIVERY话题边界；拒绝不等于改变自己的兴趣 | typed边界已有，真实“晚安”语义到投递边界的入口仍需独立复核，不凭定时器推断用户欠回应 |
| 真实经历改变未来行为 | 原G/Experience/Lesson、S3 need projection、S8 practice/heldout/transfer/reuse，6f2a491修复新缺口再次学习并防重复训练 | 本批已有受控因果证据，继续与来源独立的兴趣/关注联动；真实模型与跨日陪伴仍单列 |
| 人可理解的状态可见 | /life、Inspector、Nana Space生活页/专业控制台均为权威投影，无人格数值编辑器 | 优先把现有Concern状态译成简洁中文并保留来源，不增加“好感养成”面板 |
| 不采用 | 九维固定奖励、按消息数刷关系、惩罚式已读不回、索取安慰、成人功能、无模型时自动编社交兜底并真实发送 | 全部排除。静默不惩罚关系，Manager只管现实执行，独立生活/兴趣/S8与Shared Life并存 |

验收使用同一原Core：同根派生重复/独立新遭遇对照、跨重启与时间流逝、不同人物与转述、quiet/busy/refusal、受控真实结果后的行为改变、反例和来源撤回。先引用已有受控证据，仅对缺口加测试；开发夹具不等于真实模型/手机/真人/长期驻留。性能与费用分别报告，不为自然度结论额外发起付费调用。
