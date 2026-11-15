# 失败响应的已报告消耗不再漏计 — 2026-11-14

[实测 Advanced 全局资源/Token及S1/S2/S4/S7连续性，原A–H/G范围] 起点3fe05c0841ac0b9cacdc9d26912f23aa02d1a00a。原OpenAI兼容拒绝/截断/格式错误已有安全响应元数据，但资源统计只读成功proposal的usage；原生Anthropic还会在读取usage后因stop_reason提前退出而漏掉整个报告。结果是失败消耗被显示成缺失，无法准确评估自主生活成本。

复用原accounting数字receipt及同一cognitive_requests/Store。CognitionSession原terminal事务仅在相同request ID的完整已收2xx响应/hash及严格有效usage对时写原数字metadata，失败状态/错误码、费用UNKNOWN、原预留及无重发全部保留。无响应/超时/无效usage不写0。原生Messages在判断refusal/max_tokens/tool前先提交已验证数值；输入仍为uncached+cache creation+cache read，不把缓存报告冒充省钱实证。没有接受被拒提案、生成经历/Grant/动作或推断成功。

同时修正失效反例：过滤usage时不能删掉坏类型的别名或total而把剩余值拼成一份有效报告。先对原完整usage调用原reported_usage_pair，再保留数值白名单；坏bool别名/含私文total直接缺失，私文不入metadata。响应仍FAILED，账单未结算。

精确3fe的298个运行源码与Git逐字匹配；同一最终29场景旧9fail20pass7.36s→新29pass7.25s。相关161pass36.70s，含原Provider路由/原生Messages、world边界/重启/流式/完整wire、私人生命周期、原隐私及便携包入口；不是全仓或实际发行安装。

4个实际owned HTTP失败场景：partial/refusal/malformed每次仍1请求/FAILED，旧0报告→新fixture input10/output10；429无报告仍缺失。保留费用actual_cost_micro=None/unknown_cost_calls=1、预留不退款，失败不产生COGNITION_PROPOSAL/动作/Grant。撤回来源→重启同身份→重放不请求网络，数字receipt不丢。原生6模式中成功/思考及三个拒绝分支有效报告均input15/output4（含cache3+2），坏usage不报告。以上均fixture数值，不是真实商业Token/模型质量。

两个错误usage反例为内存codec/实际exchange，不冒充HTTP网络。另实际HTTP partial后同port超时：旧metadata不串入新UNKNOWN，usage仍缺失，费用预留保持；再建独立请求可正常PROPOSED，旧UNKNOWN仅replayed无补发。没有把一次UNKNOWN锁成全日生活停摆。

成本：无新请求阶段/Prompt/schema/依赖/索引/表，失败响应同1网络请求。三个兼容失败各新增原core_meta中123字节JSON数字payload；37046bytes请求预留保持，零费用fixture保持未结算。此为逻辑payload大小，非SQLite物理增量或回收实测；native cache子项仅原响应metadata保留，总数入原V1数字receipt。CPU/延迟仅上述合成总耗时，无真实费用或长期成本收益数字。

首次失败保留：首版新夹具forget未传/未绑定原authority，不是Core基线故障；修正夹具后有效四场景旧3fail1pass。后补29场景新1fail因测试期望零默认reserve增长，改为明确1000合成预留再对照，未改运行预算或断言方向。old最终9fail、新29和161才是本批口径。一次源指纹脚本误把带转义的bili文档路径当真实文件，后以git ls-tree -rz限定实际298 Core源码完整核验，不作资格失败。

前继私人生命周期3fe独立CI run43618468386/job132518838188实际264pass96.25s；client/full/portable/install跳过，仅归前继。现有workflow为accounting/resources加入原reported-usage、native、privacy/package定向消费者，不另建发布工程。复跑见两个测试文件与related-161日志；source.sha256有09锚，仅证明采集文件。

未新Core/Web匹配包、APK、安装、真实模型/手机/生产/真人自然度/跨日成长，CURRENT266+409未动。下一回私人兴趣→原C选项→原G/Planner实际消费者：已确认原D的无program私念仅提供WATCH/REFLECT/REST，扩大枚举不会产生可执行学习/创作。需要沿原已配置能力/原C候选做真实接线，不造第二Planner或强制思想成目标。其余情感多动机、S8更广独立迁移、存储隐私、模型特定Token与产品最终发行及原A–H全部继承。
