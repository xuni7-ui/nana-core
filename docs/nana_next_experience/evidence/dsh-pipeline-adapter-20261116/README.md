# 直接调用 dsh 原始实时选帧管线

B负责，基线A b5481b5；隔离入口 `dsh_pipeline_adapter.mjs` 从调用者明确指定的本地可信 checkout 加载上游 `src/pipeline.js::createPipeline`，不复制其Apache-2.0源码。实测 checkout [dsh-see-now](https://github.com/SAOS-3624/dsh-see-now) `0b4bd110074b3e2cd043da8b078f7272589d50b0`；测试核固定HEAD。该模块运行所选checkout的本地JS代码，调用方必须自行确认来源、许可和无未提交篡改；不得接收任意用户不可信代码路径。

输入：已授权本地RGB24文件、宽高、逐帧**原始时间戳**、fps及来源引用；不读取平台账号、不解码、不传图/网络/模型/Store，引用是调用方声明，不是身份或隐私证明。限制像素262144、输入64MiB、1200帧、单图上限1–16。直接输出上游日志选中时间和原因；因上游日志将时间四舍五入至0.01秒，若不同输入映射同一日志时间则拒绝而不猜来源。单图帧限制不是全片帧预算，输出数可超出模型预算，禁止未经原路由/预算/来源检查直接请求视觉模型。返回source_ref供回映，不复制帧或建立新的事实。

在本地FFmpeg解码的12秒48帧黑/白/运动合成片中，实际原管线输出0/start、4/cut、8/cut、11.5/mark，均精确回映输入时间。单次Node启动及处理wall0.247秒、Node及子进程累计CPU0.393秒、最大子进程RSS47776KiB；不含视频解码、上传、模型或生产，非基准对比。输入来源由实验传入，不声称验证过真实授权。

复现：`NANA_DSH_SOURCE=/path/to/dsh-see-now PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_dsh_pipeline_adapter.py -q`。Node及固定SHA checkout缺失时明确skip；实际3通过，含原管线切点、时间戳精度冲突拒绝和RGB字节长度不匹配拒绝。与现有视频/来源相关共46通过。模型Token、真实画面、实时背压/中断恢复和跨端平台尚未资格。

A后续决定何时把受授权的视频与原S5/路由连接；NanaLink负责受控输入、来源/账号/撤回，B继续预算、区域和真实素材对照。当前仅可运行实验，不是现役消费者；撤回适配器及测试即可，无数据迁移或第二主体。
