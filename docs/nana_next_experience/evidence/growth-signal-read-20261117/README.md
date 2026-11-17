# 原S3/G经历读取：对应断言的原索引，不裁剪生活

A基线3598ebb / Brain271；其Growth业务源码逐字同固定d5c0a42，消融从该固定Git AST提取原assertion_view/assertions，不重写一个假旧版。原C、Growth、独立证据计数、偏好/人格、Memory和Record仍唯一权威。

## 真实代价与最小改动

用原LifeApplication/SubjectLoop.run形成48项合成私人偏好，每项2个实际独立输入，合计96条assertion_signals（PERSONAL与PROJECT各半）。以前每次对每一项偏好都Store.all整个信号表再按assertion_id过滤，一次完整投影48次完整扫描；随偏好/经历增加形成重复读取。baseline.json保存仅旧实现尚未修改时的有效结果：完整投影中位20.902ms，48次全扫描/865 SQL，近似65800 SQLite VM步。

现在仅原ContinuityStore owner使用既有subject_assertion_roots(assertion_id,root_evidence_id)查本断言信号，ORDER BY rowid与原插入次序相同。原隐私检查仍在读payload前，active支持/反证/独立根去重/撤回/输出数量规则完全不动；没有截断较老兴趣、提高常量、加缓存/数据库/索引或模型阶段。历史只读facade保留原all()的过滤与horizon，不从其db绕过访问限制。EXPLAIN实际用原索引及小型rowid排序；不强制INDEXED BY，所以旧SQLite/缺重建索引仍按同SQL正确读取。

## 同一Store旧/新消融

same_store_profile.py/final.json交替6轮旧/新，5种投影（全部、PERSONAL、PROJECT、不同kind空结果、privacy空结果）逐字段完全相等，包含同一Record/Evidence IDs、来源时间、独立根/反证和排序。不是重新生成两套身份后比较大概输出；全过程snapshot和total_changes相同。原只读_ReadView以真实mode=ro连接复验24项PERSONAL旧/新输出相等，仍无写权。

本轮同场完整投影中位wall旧19.913→新10.595ms，CPU19.750→10.594ms；近似VM65700→22300（每100步回调估计），SQL仍865条，未假称调用数下降。PERSONAL 9.504→6.338ms、PROJECT10.076→5.263ms。无匹配kind .087→.087ms；空privacy .392→.446ms，没有宣称所有场景均更快。首次候选同库样本first-after也完整保留，不挑最快值宣称P95。48/96是小规模合成，不能外推100k延迟/磁盘P95或真实手机端到端性能。

相关原60测试18.20s通过：原独立证据/复制根/反证/撤回改变未来C选择、真实SIGKILL原子恢复、主体迁移/关系复用、社交双倾向竞争/新当前选择和原只读Inspector。没有新测试框架或扩大断言资格。结果仍同样选择，不冒称本批学会新的技能、人格成长或完成全部内心生活；实际收益是正常成长读取在保留所有证据和自主取舍时降低程序开销。Provider0、新网络0、Goal/动作0、读阶段写0，无新增持久数据或依赖；真实Token/费用未测，不能把CPU收益当节省模型Token。

原分析夹具第一次使用未配置SECRET触发SUBJECT_CONTEXT_POLICY_BLOCKED，未改权限，改为已配置PERSONAL/PROJECT；随后固定AST初稿未携带模块globals报NameError，profile-namespace-first保留。这两者不是旧Core行为/性能对照，只有修正后baseline/final用于对比；保留首次已建局部合成目录不清除。

原CI只补growth.py精确push路径和现有60项consumer组，原分级资格/沙箱不改。下一实读本批独立CI；PR24已采用，PR22/23仍按实际草稿/后继状态协调。继续原S3意义和多动机/可靠反馈/G未见迁移，私QQ父源/私Bili保留前C、B22主链适配/存储隐私/实际Token及A–H，非总工程完成。CURRENT266+409，9a2历史候选不含264以后；本批未发行/手机/真实模型/真实平台/生产/自然度/跨日。回退growth.py至3598，无DB迁移/清理或人格重置。
