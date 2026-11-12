# 原私念保存和跨窗口的相关兴趣查询

基线2c203b3。首次两场景失败：原C连续40个不同topic创意选择全为CREATE/ENDORSED，但只有32条PrivateIntent被保存；一个仍有效的旧兴趣在100个无关活跃记录后不被decision_support找到。原32是后处理静默计数门，非实际权限或物理容量，不应成为主体永久兴趣限制。

删除该32计数门，不增加调用器/任务/权限；原C选择与原Store事务/现实资源控制仍在，不宣称无限磁盘。candidates新增可选owner/topic与for_decision过滤；先选择本人/话题/可读scope/privacy/当前header和有效来源，跳过withdrawn/abandoned后，再给最多64有效候选。原只读/无新缓存路径按当前允许header分页，不安装索引。全局元数据64候选、单话题64候选与长版本链仍不是永久存储容量资格。

为避免每轮扫描所有私念，在原REBUILDABLE_LOOKUP_INDEXES注册两个物理查询缓存：artifacts上的受json_valid保护的private-contract owner/topic索引，以及原continuity_records当前私念payload联接索引。权威仍是原header/原payload/原source，不新增Store/表/schema版本。旧7–12不建这些索引；JSON不可用时不建topic缓存，旧/只读无缓存路径按Python解析分页。portable export沿原机制剥离所有已登记缓存并保持严格schema校验。普通二进制/非私念JSON不受新index影响。

追加反例首次发现100条payload WITHDRAWN仍遮住有效旧兴趣：改为实际可用性在决策候选限额前判定，原严格断言保留。after_choice合并本人/话题有效候选，已存在的旧创意在窗口外也不会重复保存；精确review仍走原record引用。40个实际原C合成选择→40条不同私念通过；无关/撤回拥挤、scope/privacy、真实EXPLAIN双索引、隔离backup去新索引后的只读分页、原来源撤回→index项消失通过。3focused0.78s；原private/portable/隐私/Context/open_life/open_autonomy213相关通过28.13s，非全仓。

## 手动规模对照（不加进每次CI）

工具：tools/nana_next_experience/qualification/private_interest_scale_v1.py；命令见下。单个全新隔离Store、一个DEV主体/一个原C种子，增量构造1k/10k/100k多类型synthetic private records（V1/V2/V3、暂停、不同owner和privacy），**不是这些数量的真实经历或通用语义记忆**。每组21次、同Store/同64候选界限；旧逻辑使用先取64再按topic/owner筛选的消融，不冒称旧二进制。新逻辑原owner/topic lookup。没有模型调用，实际商业Token/费用NOT_RUN。

| 合成其他记录 | 旧后过滤命中 | 新查询命中 | 旧P95 ms | 新P95 ms |
|---|---|---|---|---|
| 1,000 | 0/21 | 21/21 | 8.792991 | 0.148551 |
| 10,000 | 0/21 | 21/21 | 5.801407 | 0.294858 |
| 100,000 | 0/21 | 21/21 | 5.735281 | 0.261898 |

原始每次latency、P50及nearest-rank P95（ceil(.95*n)-1）在scale-report.json。是已知精确话题兴趣的遗漏修复，不是语义准确率/自然回忆/所有Memory家族1k–100k验收；不能把该组数字覆盖原S2 literal/200k或Core/Iris资格。原脚本第一次strict Python DTO误用JSON list失败，原错和小型失败库保留；修正为Python tuple后用新目录完整运行，源码指纹实核匹配，没有把重算当重跑。

100k后SQLite dbstat实测两个新增index已分配页共18,247,680 bytes（约17.4MiB）；DB269,914,112 bytes，freelist0。该DB为合成直接Store测试，不宣称真实Life的所有资源策略或256MiB永久上限资格；也不是物理擦除/冷归档资格。新索引的写入开销未与无索引独立构建对比。/private-source撤回删除索引项不等于所有文件已物理回收。环境SQLite3.53.1，不冒称云端3.51.3实测。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:$PWD/src" /workspace/nana-test-env/bin/python tools/nana_next_experience/qualification/private_interest_scale_v1.py --home /tmp/nana-private-interest-scale-20261112-b --samples 21
```

已存在home会拒绝覆盖；重现时换新空目录。原源码/DB/Git/旧交付不删除。上一2c203b3独立CI43174971755/job131037209418实读229通过/1warning59.73s/clientSKIP，非本批源码。

剩余：多倾向关联/冲突与自然跨轮策略、明确反馈/真实投递、商业认知与自主机会融合；同topic更广相关选择、长版本链成本、全局元数据/时间触发窗口；原A–H通用检索/学习/存储隐私/模型/多端/最终发行继续。CURRENT266+409，不新增APK/生产/真实模型/手机或长期成长资格。

## 已提交源码12fa8b9的独立CI与缓存重建

GitHub run43184552494/job131068699107实读127通过42.33s，客户端按Core-only范围SKIP，非全仓/安装。100001私念头的原注册隔离备份删除两个可再生cache后，以原ContinuityStore重新打开：整体开库含重建1.242099281s，identity不变、recovery_quarantine=true保持、actions/provider requests均0。新build后index已分配页16,703,488 bytes，不等于主文件已回收；原增量索引分配17.4MiB样本保留，不用新值冒充相同测量。JSON见registered-cache-rebuild.json。

首次只复制SQLite缺少privacy anchor而被PRIVACY_ANCHOR_MISSING正确拒绝，保留工具回执；未绕过锚点/隔离门，改走原Store.backup后成功。这里只验可再生缓存在已注册quarantine副本的恢复成本，不是迁移激活、独立发行安装或DR。临时失败库和两份合成副本保留，不自动清理。
