# 原G评价编号不再冒用旧成功

基线b5481b59add453990f654fb8fa0839cb4cf26907 / Brain259。A负责原S1/S2/S6/S8及来源/隐私/恢复横轴的局部因果完整性，不是新G或新评价标准。

## 旧行为与后果

原EpisodeLearning.assess先校验本次来源可读、解析case，再按lesson_id/episode_key命中旧行即返回assessment_id。未比较新episode内容、旧评价记录的scope/privacy/current。因此相同编号的新精度反例、其他scope的来源，以及原评价已随来源撤回的情形，都能直接拿到旧SUCCESS编号，调用方难以区分重复与变更。

original4.txt实际旧3failed1passed1.74s：完全同源重放控制通过；同key异内容/不同scope/来源已撤回三场景不抛错。initial-original3保留最初未增加撤回场景的旧2fail1pass。复用原grown：G练习/held-out、实际不同后续Kernel/Verify及EpisodeLearning记录，不手工插SUCCESS/ACTIVE或改独立裁判。

## 最小修复和实际闭环

只补原cache分支：在读旧payload前核对STRATEGY_REVIEW类型、同scope、调用者可读privacy、ACTIVE及当前来源；之后比较canonical episode全内容。编号同而内容不一致抛STRATEGY_EPISODE_KEY_COLLISION，范围或来源失效抛STRATEGY_SOURCE_RETIRED；不记录伪成功、不自动生成新编号或重评，不把错误变成静默重试。

原完全相同重放仍返回同ID且db.total_changes不变；包括已将lesson置SUSPENDED的同一反例再次送入，保持幂等，不要求lesson重回ACTIVE才承认历史反例。新独立发生由调用者提供独立稳定编号和来源，仍用原IndependentEvaluator；测试的精度case [.1,.2]期待.3使原NUMERIC_SUM进入COUNTEREXAMPLE/SUSPENDED。该case是受控数学评价，不带旧Kernel action_id，不伪造一次新现实动作。

current5.txt实际5passed2.25s：完全相同、不同内容、跨scope、撤回、不可读私有旧评价。最后一个以原API正常形成PERSONAL评价，再用可读PUBLIC新来源重复其编号；public caller在旧私有payload读取前被拒，artifact guard实证没有读取该私文。既有assessment与lesson历史不被碰撞改写。

related42.txt实际42passed33.84s：原World学习/反例/重新资格、真实能力需要、成长内心行为/消融、私人问题选G/不同后续场景/来源撤回与259注意群。既有原反例重放/恢复仍通过，不相加称全仓。不新增真人/真实模型、实际账号或生产验收。

## 成本与兼容

无Provider调用阶段、费用、模型Token增加，无表/索引/字段迁移。cache命中比旧直接回ID多读取原头部/有效支持及原episode，存在确定性的本地检查开销，未做大规模耗时/磁盘基准，不宣称零CPU成本或性能提升。普通第一次评价流程不改；额外复杂度为原分支12行和5个来源边界场景，服务于真实学习结果与权限完整性。

新调用可能收到明确碰撞/来源失效异常，不能继续把同编号不同内容当作重放；应沿既有来源纠错/独立发生编号处理，不自动改写旧评价。回退world_loop/learning.py本锚，不复制/回滚Store。原CURRENT266+409不动；c1d历史匹配候选不含256/257/259/260，不为这处补丁重打APK或重复发行流程。

下一仍为原C情感/多动机/持续策略、G更广独立迁移；259留下的可见但不合格/同课题重复挤占需先真实基线，不盲目提高32或制造更多G标签。B真实FFmpeg/两原版对照与A现役S5接线、主链物理隐私/真实Token及全部A–H继续；真实模型/手机/自然度/实际跨日长期仍未资格。
