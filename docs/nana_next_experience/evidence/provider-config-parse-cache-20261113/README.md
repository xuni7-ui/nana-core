# 不变Provider配置的解析复用候选

[实测] B工程基础设施，S1-C04/S5-C03 Advanced支持；基线A b016e6c，原C/记忆/Store/Growth/SubjectLoop不改。API重复调用life.provider.provider_status，每次新建配置服务，重复JSON解码、canonical编码与strict DTO验证。不缓存模型结果、路由选择、许可、凭据或主体经历。

候选仅18行生产差额：标准库LRU最多4份精确原始字节→已验证不可变ProviderConfiguration。每次仍原路径O_NOFOLLOW、owner/mode/nlink/regular检查、实际读取与256KiB上限；原duplicate-key/strict DTO验证在miss执行，错误不缓存。原CAS/flock/atomic事务不变，secret_state每次动态查询。相同大小/mtime也按字节立即失效，实例文件不同不会共享可变状态；自定义document_type不缓存。无新依赖/API/配置/持久化/主体权威或模型调用。

## 同条件对照

可复现命令：

```sh
PYTHONPATH=src:. python tools/nana_next_experience/experiments/provider_config_cache.py > result.json
```

原版reader为基线A的等价原_load正文，候选为实际ProviderConfigService；两者走同一原projection/运行时factory，逐项输出相等断言。各组交替顺序6×40次/每侧240次，文件/OS缓存温热，配置为合成公开元数据。benchmark.json同时记录wall中位/P95、process CPU均值、字节数、Python tracemalloc。并行测试/宿主调度可能影响尾部，不作为发行性能承诺。

|供应商/模型|文档字节|原状态投影中位ms|候选中位ms|单份缓存Python跟踪保留字节|
|---|---:|---:|---:|---:|
|1/1|1029|0.11618|0.03164|6864|
|8/32|14470|0.63630|0.10725|75771|
|64/256|114336|4.61919|0.73232|584763|

这些是本地同步状态投影耗时，包含原文件检查、反序列化/DTO及输出序列化；不含网络HTTP/聊天/实际Token/费用。不变配置重复读取有益，普通小配置绝对收益仅约0.085ms，不声称可感知聊天加速。64/256的240次均值CPU为5.04434→1.01869ms。

强制每次miss的冷解析无收益：64/256中位3.80657→3.79049ms，但P95 5.1845→6.87082ms。因该尾部退化追加一次无并行测试的同对照（cold-control-repeat.json），中位4.29319→4.26091ms、P95 6.81242→7.29670ms、CPU4.86633→4.91916ms。保留两次原数值；不能推广为冷读优化。原候选适用稳定配置，频繁变更/缓存抖动仍有维护与尾部成本，A可据工作负载决定是否吸收。

64/256四个修订的缓存Python跟踪保留2338373字节，最多4项；不是RSS，也不是所有合法填充方式的最大进程内存。每项raw硬上限256KiB、DTO模型最多64供应商/256模型/9路由，缓存不持有凭据值字段。没有新增磁盘/网络/模型调用；无Token节省主张。

## 验证及接入

validation.txt记录89相关通过、2个环境缺PIL失败→装仓库指定Pillow12.3.0后原媒体3路径通过/2.31s；仅复跑受影响路径。新增8个回归包含同大小/mtime修改、不同实例、atomic回到旧文档、warm后权限/软硬链接/缺失/超限/重复键、frozen DTO、动态凭据状态及自定义验证；原CAS回归亦保持。初次7通过/1失败是测试把原MISSING误写UNAVAILABLE，按既有真实协议修正；原始失败在first-failures.txt。未更改产品协议或放宽断言。

接续A6655a28资源暂停恢复仅正常合并；本批源码/测试/实验指纹不变，保留A账本前缀，复用以上验证。

唯一集成位置ProviderConfigService._load，不修改主体行为；A原调用者无需变更。撤回18行即可回原全量解析，无数据迁移、配置开关或运行数据回写。客户端不变，不重复Web/APK/发行。候选未主线集成/部署，真实账号/Provider/手机/生产不在范围。源码表指纹仅采集时状态，不是运行证明。
