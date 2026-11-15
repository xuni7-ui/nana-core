# 原视觉请求不被终态UNKNOWN永久锁住

基线b9778afdebfe9e4b87718af44e1dd41156009813/Brain244，原A职责S5/S4及全局G资源兼容。源码只将BilibiliFrameService.interpret两处unresolved_calls换为原有unresolved_live_calls；逻辑沿既有LifeApplication，未删除guard或新增调度/模型/账本。冻结S1–S10/原C-D-G/Store不变。

## 以前缺口与本次行为

原Router/VISION/H1在owned HTTP对某帧超时，原cognitive_requests留下UNKNOWN（账单未明）。旧服务同时把该终态行当作活跃互斥，导致不同帧的新请求被UNRESOLVED_PROVIDER_CALL_NO_RETRY阻断，同Store重开仍如此。baseline2fail1pass.txt是实际未改业务源的2失败/1通过2.13s，分别无重启/同主体重开；第三项已证明真实CALLING仍应互斥。

新after3.txt为3通过2.08s：旧帧仍UNKNOWN/请求整行不变/不重发/不退预留；另一帧走原Router/资源预算/H1实际一次请求并形成原World的有来源模型推断。再请求旧帧返回原UNKNOWN，HTTP保持2次；总调用额度降为已经占用的2后，第三独立帧精确被PROVIDER_TOTAL_CALL_BUDGET挡住。原来源撤回后新帧读为MEMORY_UNAVAILABLE、不调用模型；同身份跨正常关闭/重新打开后上述行为相同。

活跃互斥的场景在原owner收到响应但accept尚未结账的实际CALLING阶段探测嵌套视觉请求，仍拒绝，整个场景仅1次HTTP。没有把UNKNOWN当成成功、清账或盲目重发。原Runtime provider_unknown_calls_per_day后台节奏/前台独立请求与总字节/总费/总调用预留机制完全未改。

两帧是原B站故事板样本，不等于全片覆盖/视觉准确率升级；自主观看选择仍由原C，原Manager/账号授权不受此guard替代。终态UNKNOWN只不再禁止所有未来独立视觉；原同source key与原CognitionSession恢复仍决定请求是否可发送。

## 验证与成本

related32.txt：32 passed14.00s，覆盖新增3、原B站图片采集/原Router→H1→World/来源撤回、原C自主B站生活、UNKNOWN后台/前台与真实旧DEV release返回、原总调用/费用/Provider小时额度/完整wire预留/超时继承/启动开关。首个夹具在Provider worker内读取owner Store不成立，原线程边界拒绝；首轮3fail不当作3个生产缺陷，已改在实际owner accept前读取，旧版定为2fail1pass，未改安全边界或断言。原始输出保留。

每个继续场景总HTTP2（1次超时+1次新帧），重放旧帧/预算拒绝/撤回均无新增HTTP；所有模型与平台均本地合成，真实Token/账单/费用未测，不把fixture usage当成本收益。没有新增背景轮询/模型阶段/持久结构；100ms/350ms只是受控超时夹具，生产默认120000ms及原全链预算未改。两处field差额不要求再打本批Core/Web/APK，原9a固定候选不包含本修复。回退该源bilibili_frames.py即可，无数据迁移/退款或状态清理。

CI新增精确源/测试路径及原相关组消费者选择，不新增框架/每次全仓发行；已编译原工作流内嵌Python，实际新CI待远端回执。另独立实读固定9a run43763081801/job132962199511为290passed1warning129.55s，仅affected checks，client/full/portable SKIP；这不是本245源码CI或全仓结果。

下一仍属原唯一任务：B两仓算法候选及NanaLink新源I/O按固定提交对接；A优先原S5视觉观察在后续C/S3/S8的原生因果消费者与更广自然交流/多动机，避免单独视觉Agent。现役BilibiliLife只有首故事板帧被语义解释，覆盖仍明确采样，不把原3帧结构当全片理解；该部分应与B真实算法契约一起补共享预算/覆盖/时间戳，不盲目加大帧数或增加收费调用。原A–H、语义压缩/长期检索、物理存储隐私、更多Provider与通用客户端/匹配最终发行继续。真实模型/手机/账号/生产/自然度/实际长期未新资格，CURRENT266+409不动。
