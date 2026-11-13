# 原正常D选择商业资源（显式宿主绑定）

同一主任务S1/S2/S3/S4/S6 Advanced，基线dde862bc1471d512f7fb6cb291f9bc28eae456c0。上一批只把SELF资源接到原cognize；本批把它接回原CognitionCoordinator、队列、Runtime.step及LifeApplication配置路由。没有新主体/Loop/Store/Planner/付费轮询。

## 真实行为与因果

显式owner调用LifeApplication.bind_provider_cognition()，复用原router.inspect/resolve、host小时/日/profile/总量预算与_session恢复；绑定不派发、不持久化新收费模式，宿主重启按自己的配置策略重新绑定。旧应用默认行为不变，公开客户端尚无新开关，不冒充普通用户产品交付。资源callback由宿主提供，模型只收到不可变DTO。

正常D仍按原Need/private condition/quiet/前台/lease/来源版本选择机会。资源层的preview在实际完整请求上核算字节、model framing与费用，只读不预留；费用不足/未配置等保留私人队列READY，重复同条件检查DB/events/attempts不增；恢复后同队列ID实际继续。执行通过原cognitive_requests与usage/UNKNOWN，不再调用fixture reserve/finish，实际Provider请求依然独立重验，不能拿正面预览绕过后来变化的预算。

原私人计划→原D条件机会→原Frame与内容投影→owned HTTP SELF→同C形成新问题。无用户消息，仍同identity/Store，1HTTP/1原账本/0fixture账本，原plan与question共存，后续同条件不再调用。对相同已存在计划、同预算、同一个数据驱动fixture关闭internal_projection后，计划保持ACTIVE、仍1HTTP但不形成该新问题；因此不是把新问题预写入Store。该语义fixture按是否实际收到PRIVATE_PLAN投影决定提出问题或WAIT，证明数据流/消费/选择接线，不是商业模型自发性、自然度或长期学习效果。

重用原有限前台中断：实际在途被USER_EVENT抢占→UNKNOWN，旧candidate不采用；前台先处理、同Store重启并重新绑定后也不重发旧请求。源在排队时或factory竞态撤回均IGNORED/0HTTP；实际源失效不假作资源暂停。当前失败/UNKNOWN不凭空做轻量替代完成旧语义，保留原私人关注，独立新条件仍受原预算。1.6s延迟的真实owned HTTP通过，超过原fixture默认1.5s；provider路径传120000ms请求预算，不套fixture的1.5s/30s配置。

## 对照、验证与成本

手动工具沿既有qualification入口，两个独立等价DEV Store、相同旧计划/输入/32768与2048预算/同一HTTP proposer：精确dde旧包经原测试port注入已有provider资源，两条账项（fixture1+provider1）；新显式绑定fixture0+provider1。两边均HTTP1、同样由C形成新问题、actions/grants0。旧槽注入仅用于隔离诊断，不是支持的生产适配；对照证明资源计数差，不证明提供方收费/模型质量改进、同Store换源、安装或生产。程序与原始JSON可复跑，根及报告路径均要求全新/tmp或/dev/shm，不能覆盖现有Store/证据。

316相关87.78s通过，含原私念/Runtime/Context/Cognition/native Anthropic/Precision及HTTP continuation；随后只省掉claim后的重复完整预览（实际派发重验保留），105相关15.52s通过，正常机会只有1次完整预览；最终数据驱动消融/宿主绑定等11专项4.28s。分列非全仓，未相加作为更大“通过数”。额外本地装配仍有D预览、原C冻结、实际provider请求三个阶段，未宣称CPU/P95或真实Token节省；预览没有模型调用，原来重复的claim预览已去除。

预览测试以total_changes与完整Store snapshot证明无写入；framing/cost失败零预留/零HTTP，已有请求只回原状态；另一真实PREPARED占掉日额后，先前正面预览不能通过实际prepare。字符framing fixture不是商用Tokenizer，真实Provider Token/费用null，真实模型/用户账号/手机0。旧dde独立CI498pass1warning205.99s/clientSKIP另记，非本批CI。

## 未完闭环

显式宿主API已接实际LifeApplication和D，但客户端常规模型向导/持久startup选择尚未暴露；不自动让既有安装开始新收费。没有旧Memory/Record的首个商业请求仍需真实自身“请求考虑/发生”追源，不能拿已验证模型proposal发生文本冒充尚未发生的调用，亦不能强制保存短念。需继续压缩本地重复装配、情感意义/多动机/策略真实效果/G后续迁移，以及原A–H、reader回退与匹配发行。旧fixture模式及默认配置保留；正式CURRENT仍266+409，无新安装/APK/生产/自然度/跨日长期资格。
