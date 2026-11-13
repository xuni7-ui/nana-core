# 原D私人活动：资源等待与陈旧队列

基线b016e6c。机会已入队后停机改无模型/零预算，原版两例均把READY消耗为DONE，随后资源恢复无法继续。新版本在原队列claim前以现有C/资源判断只读检查；无方法资源则保留READY，资源恢复后同queue/同identity恰好1fixture，非另建机会或模型轮询。普通队列metadata无ref即走旧路径，不重复打开其正文。原唯一writer/lease/事务仍负责claim，用户优先/流序/到期有效。

2首次失败保留→8目标通过1.09s；后补陈旧plan修订队列淘汰9通过1.21s。加入进程中断后RESERVED→UNKNOWN场景，旧请求保持UNKNOWN、无模型也能正常结束原队列轻量恢复，不重派发；最终相关115pass20.53s（私念/continuous_runtime/cadence/recovery/resources/quiet-checkpoints/independent UNKNOWN）；最后仅把UNKNOWN测试元数据断言收紧后1pass0.47s，不拼116总数。

资源未变连续四次refresh/step的Store total_changes、events、attempts、模型调用均不增加；原D仍提供低成本只读检查，没有额外服务/循环/模型往返/状态表。来源被修订的旧精确ref在模型前淘汰，不把旧plan送给模型；源撤回资格继承前批。离线fixture actual_tokens/cost0，不当商业Token/账单/CPU或磁盘收益测量。

实读先前d291独立CI run43368824797/job131699714353：205pass54.24s，clientSKIP，摘录及所选检查另附；不冒充当前后继CI/全仓。无artifact下载重试。

仍未资格：新ref队列/模板旧reader安全回退、商业INTERPRET/C/RENDER长期策略/明确反馈/S8闭环、单topic64及真实跨日长期、全A–H/最终匹配安装发行。CURRENT266+409、真实模型/手机/生产不动。下一先窄查商业主链当前private refs的真实消费者与topic绑定，再在原机制中补接；不为本批重打APK。
