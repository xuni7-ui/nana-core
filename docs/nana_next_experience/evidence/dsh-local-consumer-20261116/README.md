# dsh队列的受控本地消费者实验

B负责，A基线35740e7，调用可信本地dsh固定0b4bd110的原createPipeline，队列深度保持原默认1。先前隔离适配器仅模拟完全不取队列，不能比较消费者速度；现在可选`take_every_n_frames`以输入帧数控制原`pipeline.take()`本地取走拼图；0保持不取。返回创建、挤掉、仍排队、已本地取走的张数及对应源帧时间，四种计数满足创建=挤掉+排队+本地取出。图像只在进程内交本地测试消费者后丢弃，不发模型或平台；`TAKEN_LOCALLY_NOT_DELIVERED`、`SELECTED_NOT_DELIVERED`明确不代表ACK、实际送达或观察。

[实测] 同一48帧4fps黑白切换合成RGB、每张最多2帧，三种受控本地取出节奏：不取→创建4/本地取0/排队1/挤掉3；每24帧取一次→4/2/1/1；每帧取→4/3/1/0。最后一张在输入结束时仍在队列，不自动补取；时间为同步模拟，不等同网络延迟/真实用户设备。各情况0模型调用。原始dsh允许丢旧图；本实验仅准确记录，不通过额外模型调用强行补齐，也不把本地取出当对方已看见。

复现 `NANA_DSH_SOURCE=/path/to/pinned/dsh-see-now PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_dsh_pipeline_adapter.py tests/nana_next_experience/test_video_fusion_prototype.py -q`，12通过；缺Node/固定上游checkout显式skip。上游日志和队列时间需能唯一回映输入原时间，否则拒绝。旧背压证据 `dsh-backpressure-accounting-20261116` 源码表对应8e8fe1b，本表指本次后继。

尚未验证真实实时摄像头/平台发送、取消、断线重连、恢复、真实ACK、真实Token或生产；调用方来源引用仅声明。NanaLink负责平台来源与真实回执，A负责原S5/Provider消费，B继续研究背压、重要变化保留及资源，禁止建立第二投递或主体权威。删除实验增量可回退，无数据迁移。
