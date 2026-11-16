# dsh背压下区分选帧日志与队列

B负责；A基线35740e7，固定本地dsh `0b4bd110074b3e2cd043da8b078f7272589d50b0`。原`createPipeline`默认queueDepth=1，生成新拼图时队列满则移除最老拼图，但`pipeline.log`仍记录所有曾经选择的帧。上一版隔离适配器返回完整日志作为候选且没有表示队列损失；没有发图或声称已投递，但后续消费者可能误把选过当成可直接投递。

当前适配器显式沿用原queueDepth=1，返回`selection_state=SELECTED_NOT_DELIVERED`、累计创建/当前排队/挤掉的拼图数量与当前队列帧时间；原选帧日志仍保留以便在**原来源依然可访问并经授权**时考虑回取，绝不是已投递事实。适配器从未调用take，因此本离线运行中`dropped_sheets=stats.sheets-queued_sheets`；该计算不能泛化为已经被其他消费者取走的在线队列。融合候选传递dropped_sheets，并标`CANDIDATES_NOT_DELIVERED`；旧输入缺少字段为未知None，不编造0。没有发起模型请求，返回值不构成平台发送/ACK/成功。

48帧合成黑白交替、每图最多2帧：dsh选帧日志7条、生成4张拼图、队列剩1张、3张被挤掉，队列中帧时间10秒；原始数据/帧未入库。`NANA_DSH_SOURCE=/path/to/pinned/dsh-see-now PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_dsh_pipeline_adapter.py tests/nana_next_experience/test_video_fusion_prototype.py -q`：11通过，包含实际上游队列和损失传递，没上游checkout/Node时明确skip。前一个dsh-pipeline-adapter-20261116源码表对应提交3cb5583，前一个融合表对应7d053c9，本表为后继。

只展示离线一次性输入且无消费者取队列的语义；真实实时背压、取消、断线重连/恢复、平台真实投递与独立回执均未实现或资格化。NanaLink负责原授权来源/回取与回执，A负责原S5/Provider预算接线；B继续实际队列/背压对照。无数据迁移；撤回本批元数据字段可回到旧实验但不得把选帧声称已投递。
