# 私人D机会：前台竞争及恢复

基线d29120b；沿原队列与quiet窗口，不新增循环或判断权威。前台在collector之前或schedule注册之后到达均先处理；worker在模型前核验当前private ref，并把原队列原子延后到静默窗口结束。反复同时间step不重新claim/调用。可空expires_at按原无期限处理，显式期限不足则过期，不虚构默认期限。

原版两竞态1fail/1pass（注册后用户插入仍马上后台认知），首修1fail/1pass暴露可空期限比较TypeError；日志均保留。修正nullable后2pass；追加静默队列停机/同Store重启换模型、无模型或预算恢复前不消费机会、已排队来源撤回，6pass0.88s。相关111pass17.81s覆盖私念、continuous_runtime、cadence/recovery/resources、Context/Cognition；不是全仓/新安装。后续仅格式调整，无语义变化。

重启模型换为另一个既有fixture，原identity、原private plan和同queue due保持；恢复后恰好1调用，同版本继续step不再调用。撤回后原队列IGNORED、0模型。全部合成PROJECT素材，真实Provider/外部动作/手机/生产0。原actual_tokens/cost为注册离线fixture 0，非商业节费证据；未测CPU/物理增长/真实Token，不作资源收益宣称。

未完成：已入队后资源改变可能使LIGHT结束一次机会；应保留原C选择与资源方法分离，定向修复，避免同条件反复写入/昂贵轮询。陈旧修订排队与新private ref旧reader安全回退仍待。正常商业INTERPRET/C/RENDER私人状态及可选策略/可靠结果→S8仍须实现，不以当前离线D称完成内心生活。新十九节指令逐节归入原mission/AGENTS及task_inputs，Foundation/63标准不改，原A–H继续。
