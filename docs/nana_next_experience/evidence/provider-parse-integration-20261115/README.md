# A采用PR17：原状态投影复用不可变配置解析

固定A基线5d4457e5551aaf6fdbe5e34c4fa7045d1b7b1478/Brain240，B候选30459c54564c3e246d92e1c8e97f2ec2df4b9409。**结局：采用，进入现役ProviderConfigService._load及原life.provider.provider_status消费者。** B负责实现，A负责本次集成；不新增Store/主体或认知权威。

只有18行运行差额。原frozen DTO全部嵌套为标量/tuple，不缓存密钥值/许可/路由结果/主体状态；4项精确原始字节LRU，文件owner/mode/nlink/regular/O_NOFOLLOW和256KiB读取上限每次重做。错误与自定义文档验证不缓存，同大小mtime编辑仍即时反映；原CAS、幂等及动态凭据检查未改。输入输出/配置版本不变，无迁移/依赖。

## 实际消费者与对照

exact_baseline.py从固定5d Git对象AST提取**原_load函数原文**，使用同一配置、原状态投影/工厂和不可变数据定义；不是用候选重写一段近似基线。8供应商32模型/14470字节，交替6×40各240次，逐字段输出相等。原版中位0.598376ms/P95 0.775142ms/CPU均值0.625345ms；候选0.116817/0.195252/0.132269ms。仅本地同步状态投影，非HTTP或聊天延迟，实际模型/Token/费用均未测（calls=0）。

B原provider-config-parse-cache-20261113的其他大小、内存和冷miss对照直接复用：四大文档Python跟踪保留2338373字节，非RSS/全合法schema最坏值；两次冷miss P95均退化，原数值未改。不声称冷读收益，不把本次温缓存结果推广为产品端到端收益。采用理由是稳定配置反复状态投影的CPU负载降低，容量4有界，额外标准库实现18行；频繁配置抖动仍有尾部成本。

## 资格与限制

related166.txt：166 passed/32.10s，覆盖新增8个精确字节/原文件信任/动态凭据/自定义验证边界、原Provider配置CAS与路由/超时/原生适配、Vault epoch、配置权限、真实本地认证BFF模型目录与runtime设置。没有真实Provider/账号；没有重复前端/APK/全仓/发布。比较脚本首轮误传额外参数在比较开始即TypeError，保留comparison-first-error.txt；按现有真实单参数接口修正工具，运行代码/测试断言不因此改变。

原C/D/G/Memory/Store、63标准及CURRENT266+409不变。撤回18行即回到本基线逐次解析，无数据/协议回滚。最终包需在其余集成收口后固定新源统一构建；旧fee8候选不包含本批。下一审核PR18固定可见6645fd0的新来源/旧reader/withdrawal/最小运行闭包并协调原平台成果；B视觉算法不重复实现，所有原A–H继续。
