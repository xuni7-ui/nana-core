# dsh本地队列take/restore受控反例

B负责，A基线35740e7；实际调用本地固定dsh `0b4bd110074b3e2cd043da8b078f7272589d50b0` 的原`createPipeline`、`take`、`restore`，无源码复制、平台连接、模型或Store。48帧以上按需生成黑白变化，输入为合成数据；测试仅同一Node进程/原队列深度1。

实际结果：队列空且尚未外发时，取出拼图后restore返回true，下一次take得到同一对象；旧拼图持有期间如果已有新拼图占队列，restore返回false，新拼图仍在且来源时间2秒晚于旧拼图0秒。另在模拟UNKNOWN时，测试代码主动不调用restore、不做任何外部发送，队列保持空；这是测试调用方选择，不是上游自动提供UNKNOWN语义、持久状态或真实幂等保障。

复现：`NANA_DSH_SOURCE=/path/to/pinned/dsh-see-now PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_dsh_restore_fixture.py tests/nana_next_experience/test_dsh_pipeline_adapter.py tests/nana_next_experience/test_video_fusion_prototype.py -q`，13通过；无Node/固定checkout相关项显式skip。输出为SYNTHETIC_IN_PROCESS_ONLY，0模型、0外部发送。

进程崩溃、跨进程重启、真实平台发送/ACK丢失、断线重连、账号绑定和来源撤回均未资格。特别是不能把待恢复拼图等同真实消息尚未送达，UNKNOWN不能自动重发。NanaLink负责原平台回执/恢复和权限，A负责原S5/主体、来源与预算，B继续在同一架构交候选。删除实验脚本和测试即可回退，无数据迁移。
