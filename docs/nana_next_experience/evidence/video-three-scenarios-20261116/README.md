# 暗场弱切、连续运动和短文字的四方法对照

B负责；A基线35740e7，固定原始dsh `0b4bd110074b3e2cd043da8b078f7272589d50b0` 和video-watch-plus `8ca266f9cf9e5ffce7e9d424aa0e937a897b608d`，脚本执行前核对两checkout的HEAD及tracked文件无改动，不复制上游源码。使用本地FFmpeg生成8秒/4fps素材、无网络/模型/真实用户媒体；三组均指定最多4帧的对照口径（dsh maxFrames=8是单图上限，需如实报告其原始总数，非强制全片4帧）。均匀、原watch --max4、原dsh管线、已实现的变化换帧候选都实际调用；两原版输出超4时报告超额而不裁剪伪造同预算。watch的plan是请求偏移而非实际解码帧，文本指标仅表示请求偏移落在文字可见时间，不能冒称文字被解码或识别。

复现：`PYTHONPATH=src:. python tools/nana_next_experience/experiments/compare_video_scenarios.py --dsh /trusted/path/dsh-see-now --watch /trusted/path/video-watch-plus`。要求固定干净checkout、Node、FFmpeg及DejaVu Sans字体；FFmpeg 7.1.5、Node 24.22.0环境的原结果见results.json。每场景只1例，不能计算总体准确率或实际模型Token。

- 暗场弱亮度硬切：4秒切换两片接近的暗灰；切后0.5秒内选帧分别为均匀否、watch否、dsh否、候选是。dsh实际只选1帧/最大间隔8秒，其他各4帧；候选选切点不等于理解事件。
- 连续运动无硬切：watch报告0切，dsh报告7.75秒切点（该合成素材的假阳性）；候选变化分数不输出切点标签，不能与切点误报率直接等同。
- 灰暗周期亮度+3.0秒单帧文字：落入有字帧时段的请求偏移，均匀是、watch否、dsh否、候选否，各4帧。这是候选漏选反例，不能因为前一12秒素材选中过文字就声称普遍解决；无OCR/视觉模型识别准确率。

本实验没有CPU/内存的同条件对照、真实视频/字幕/ASR、真实Provider Token/账单或跨平台资格。局部误报不能由此推断原项目整体质量；下一B继续短文本/连续动作/亮度误报对照和预算策略，NanaLink负责有授权媒体与来源，A负责唯一原S5/S2/C/S8接线。实验只产生临时合成文件，无持久数据迁移或现役消费者。
