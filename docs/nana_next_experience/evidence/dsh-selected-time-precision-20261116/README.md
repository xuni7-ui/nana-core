# dsh日志时间精度：只对实际选中帧检查歧义

B负责，A基线35740e7；固定dsh `0b4bd110074b3e2cd043da8b078f7272589d50b0` 的日志和队列帧时间精确到0.01秒。此前适配器若**任意输入帧**四舍五入时间碰撞就拒绝整个视频，即便上游根本未选到这些帧，也会无谓丢失其他可安全映射的选帧。

现建立每个日志时间到所有原始输入时间的映射，仅对上游实际选中、当前排队或本地取出的帧要求唯一候选；有歧义或缺失仍拒绝，绝不猜测或虚构时间。队列本地取出仍非投递；此改动不改变原dsh检测、选帧、模型预算、主体或平台权限。

[实测] 同一4帧静止合成RGB、输入0/0.501/0.502/0.75秒：0.501与0.502均显示为0.50但均未选中。固定旧适配器`80a097c`拒绝整段；新适配器通过并只映射实际选中的0秒。另一反例中0.001/0.002均显示0.00且实际选中，该歧义仍被拒绝。`NANA_DSH_SOURCE=/path/to/pinned/dsh-see-now PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_dsh_pipeline_adapter.py tests/nana_next_experience/test_dsh_restore_fixture.py tests/nana_next_experience/test_video_fusion_prototype.py -q`：14通过，缺可信checkout/Node明确skip。没有真实视频/设备、实际Token、送达/ACK或生产资格。

本更改没有提高上游原0.01秒输出精度；选中帧真正重叠仍不可恢复，需要上游暴露更精确时间或更改原接口后由B继续验证。NanaLink拥有媒体来源/授权，A拥有原S5主体与源撤回接线。可撤销本批适配器代码，无数据迁移；旧证据按对应提交保留。
