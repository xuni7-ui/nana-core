# 字幕与声学静音的来源化时间复查候选

B负责，A基线90a31b6；NanaLink PR20已合入提供原Memory读取的`storyboard_samples` v1，原字幕范围只含来源ID、区间与序号，正文省略。隔离函数`review_storyboard`每次调用原只读投影、按原scope/privacy检查，复用其源ID、平台、BVID/CID、账号未绑定、隐私、发生/观察时间；没有向Store写入，既有Memory仍是来源/撤回权威。声学输入由调用者提供，当前只有本地FFmpeg静音测量，要求同一视频来源ID和一致时长；原素材字节哈希/账号/时间轴的真实性当前仍由受信任调用者自行核验，`timeline_aligned=True`只记录调用方声明，不是工具验证。默认False。

每段字幕计算与声学静音区间的时间重叠。重叠比例≥0.8只标`REVIEW_SILENCE_OVERLAP`，低于阈值标`BELOW_SILENCE_REVIEW_THRESHOLD`，均不代表字幕正确、错误、有人讲话、真实声源或事实；字幕可以描述音乐或画面。无音轨、分析不完整、未确认时间对齐、零时长字幕均为`UNKNOWN`。拒绝无来源、重复ID、非法/重叠静音区间及非范围字段，不接收字幕正文。阈值只是实验复查提示，不控制主体或用户行为。

[实测] `PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_caption_acoustic.py tests/nanalink/test_bilibili_video_history.py -q`：12通过。其中合成原B站owned loopback→原Memory→原NanaLink投影→本实验，音频测量为精确时间替身；原来源撤回后重新调用被原Memory拒绝，跨来源标识拒绝。既往生成的内存返回对象不会自动撤回，因此禁止把它当持久事实；若A接入，仍须通过原来源依赖与撤回闭包重读/删除。另用FFmpeg真实合成静音/纯音测量喂时间复查；纯音并非人声，未调用ASR/视觉模型。相关音频+字幕单测9通过；最近全视觉/音频测试30通过后仅标签名与实验接口增量，相关12再次通过。

本候选尚不在现役调度调用链；没有真实B站账号、真实音视频、语音活动检测、字幕校对准确率、模型Token或费用资格。后续B需验证有独立时间标注的真实可授权素材、多音轨/时间偏移与声学方法；NanaLink负责经过授权的同源媒体与来源，A负责原S5/S2/C/S8接线和撤回持久化。删除实验和测试即可回退，无数据迁移。
