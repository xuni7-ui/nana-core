# 商业认知主链：私念在公开生成前影响原C交流选择

基线b6f4069980bac74096062ad7895042f334847f55，当前仍同一NEXT_EXPERIENCE主任务。S1/S2/S3/S6/S7 Advanced候选，基础资格/冻结63标准不改。复用原PrivateIntent/V2/V3及C/Store/Context/CognitionSession/CommunicationPurpose，没有第二主体/Planner/情感系统或模型循环。

## 实际接线与旧缺口

旧正常商业chat只有相关private_interest_refs进入C的Appraisal/Motivation；INTERPRET拿不到内文，C也没有把可选交流方式传给RENDER的消费者。现在：

`LifeApplication._model → CognitionSession._prepare → SubjectLoop.dialogue_private_refs → ContextAssembler(PRIVATE_INTERNAL_STATE，仅当前相关INTERPRET/实际请求预算) → 原INTERPRET返回可选communication_proposal → 原C独立Appraisal/Motivation/Judgment/Intention及norm → context_fit.consider_communication → CycleResult.communication_choice → CommunicationPurpose.choice → 原RENDER`。

候选只是LISTEN/CHAT/EXPLAIN/PLAY/EXPLORE、信息密度及可选追问，不是Goal/任务/学习/工具/执行授权，没有固定条数或生活优先级。原C先决定是否属于可交流的方向，候选必须绑定当前已核验INTERPRET、实际上下文中私念记录、当前自有有效支持；低可信解释、边界/权限不允许等不能靠候选越过。原social_proposal保持候选语义，新choice是本请求经C考虑的交流方式，没有独立决策器。

私念正文只进入授权且相关的INTERPRET，普通ROLE/无topic/PUBLIC不读更高隐私；完整请求计量与动态装配继续。RENDER不接收PRIVATE_INTERNAL_STATE内文或choice的basis_private_record_ids。原PRIVATE_INTENT_STATE安全投影仍可含无内文状态及依赖句柄；不是声称RENDER没有任何来源ID。所有复制上下文绑定原依赖/撤回，普通journal不输出请求正文。用户本轮未保留的原话不进Core artifact。没有逐字推理日志。

## 行为与对照

精确Git blob旧包核验，pytest覆盖pythonpath防止误测现役源码：同输入同名义预算旧版两轮均简短，目标断言1fail；新版关闭私念投影仍简短，开启后同一旧私人疑问进入INTERPRET，C采用EXPLORE/DEEP/NONE，RENDER实际产生更充分的合成交流。不是事后补内心独白。

同一个全新合成Store顺序停旧源/启新源，身份、原私人疑问record保持，同input16384/output2048/每阶段120s名义预算，各2个既有HTTP模型调用，0额外认知往返。原调用动作/Grant均0。普通chat不自动改为Goal。源撤回前至少2份含内文的原artifact，撤回后0且之后不再影响选择；这是逻辑依赖撤回，不宣称物理擦除或容量回收。

重启换另一个fixture模型仍同主体/私念；无效私念依据拒绝且不RENDER/不重试；篡改C公开choice绑定被拒；外部渲染/无当前topic不能用private context flag。当前用户要求lighter时原C改为CHAT/BRIEF/NONE，自己的兴趣仍ACTIVE。该反馈是本轮合成输入，未冒充真实人际效果或长期S8评价。

## 验证与首次失败

最终相关170pass44.57s，含私念/Context/Cognition/正常HTTP/记忆反馈/Precision规划恢复/provider frontend/context-fit；后补当前topic门7pass4.99s，最终强化撤回前存在复制及两role拒绝3pass1.23s，各自范围不相加称全仓。新8个受控场景接入原affected CI，不新增发布流水线。旧b6独立CI174pass56.35s/clientSKIP已实读，非当前候选CI。

初始8192模型限额场景两个私念竞争、后续历史增加会正常裁掉私问，导致目标措辞仍短；日志保留。最终对照预先统一配置32768模型上限/实际16384输入预算，旧/新和消融均同预算；不调松容量或强制注入私念，低预算不保证每次带入。

首轮相关37pass/1fail是旧断言禁止所有INTERPRET读内文，与新明确授权的内部消费者冲突；改为仅当前匹配且可读的INTERPRET允许，所有RENDER/无关/PUBLIC/撤回仍严格禁正文，未删隐私保证。

协议复核发现旧的手写schema定义裁剪漏掉CommunicationProposal，新增$ref闭包断言真实失败后修复：只带可达定义，旧schema也不要求不存在的新定义。pre-schema-preliminary-report只作未资格探索，不能当最终协议证明。新私念提示仅INTERPRET，RENDER只遵守已承诺公开choice。完整模型/角色/事实/CSRF/撤销/UNKNOWN边界沿原机制。

## 成本与实际范围

当前工具same-store-report：旧/新都是2次fixture HTTP，wire输入分别21682+21205=42887 / 24735+21552=46287 bytes，增加3400 bytes，未称免费或Token节省。单样本CPU132533/112235微秒、wall133479/113111微秒，峰RSS约59.9MB；仅本次合成样本，不作性能提升/P50/P95。逻辑页数各增25；重启/WAL状态不同，族分配字节原值保留，不作物理节省比较。Core修改行数、时间及磁盘原始数见JSON，不以逻辑删除充物理回收。

fixture的10/10 usage是人为常量，非实际计数；真实Provider Token/费用null，真实调用0。私念正文额外输入的收益目前只由受控行为差异证明，真实模型/真人自然度/手机/平台实际投递/跨日成长未资格。环境CPython3.12.14+SQLite3.53.1，不冒云端3.51.3。

## 可复核重跑与剩余

手动工具只接受全新unsymlinked /tmp或/dev/shm目录；原比较Store不存在时拒绝，不悄悄新建替代身份。只许合成loopback，不读生产/Key。旧包按baseline-source-proof中7文件Git blob构造，命令：

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/nana-test-env/bin/python tools/nana_next_experience/qualification/inner_communication_v1.py --home /dev/shm/CHOOSE_A_FRESH_DIRECTORY --baseline-source /dev/shm/nana-commercial-c-baseline --candidate-source src
```

临时包/Store可能随环境丢失，仓库保留原日志/JSON/源码指纹；不是便携包安装或生产升级。sourceTable不包含自身，09另存锚。

**仍为候选、非完整内心生活验收。** choice目前CURRENT_COGNITIVE_REQUEST_ONLY，不是持久策略。下一复用原Record/Experience做有界跨轮策略延续/明确反馈与反证、实际结果归因→S8独立后续迁移；不能把沉默/送达/模型自评当改善。更多情感/多动机、低预算检索质量、长期注意及原A–H继续。新choice非空和private ref队列的旧reader安全回退未资格，CURRENT仍266+409，无新APK/生产切换。
