# 上游声学判型反例：合成语音被判非语音

负责人B；[video-watch-plus](https://github.com/xinhailaopo/video-watch-plus) 固定 `8ca266f9cf9e5ffce7e9d424aa0e937a897b608d` 的 `scripts/audio_probe.py::verdict` 实际运行，不复制其MIT源码。它用NumPy计算频谱/节拍等量测，再用固定阈值输出声学类型；自身提示必须与ASR/VAD交叉核验。当前环境 FFmpeg 7.1.5/libflite，系统Python 3.12.14、NumPy 2.3.5；以上依赖只用于隔离实验，无包/模型下载或第三方源码入库。

可复现：`PYTHONPATH=src:. python tools/nana_next_experience/experiments/compare_audio_upstream.py --watch /path/to/video-watch-plus --upstream-python /path/to/python-with-numpy`。脚本生成三个路径均临时删除：三秒纯正弦、FFmpeg FLITE合成英语语音、原版JSON。固定版本原版结果见comparison.json：纯正弦被判“器乐/音乐为主”且confidence high；合成语音被判“纯音/提示音（非语音、非音乐）”且confidence medium。本地原FFmpeg静音测量在这两段均无≥1秒静音，只能说明门槛结果，不证明语音或非语音。不同版本/模型/片段可能不同；每类1条不能计算泛化准确率。

结论仅为：**这套阈值判型不能作为否认语音的权威或阻断字幕/主体学习的规则**。可以继续研究声学原始数值和独立来源交叉验证，不把单一分类标签写为事实；保留UNKNOWN和来源撤回。本实验0模型/网络调用，无实际ASR/VAD、真实语音、音视频Token、费用或真实平台资格。下一B研究合法可复现的多样语音/音乐/噪声和时间对齐，NanaLink负责来源，A决定现役融合。删除隔离对照脚本即可回退。
