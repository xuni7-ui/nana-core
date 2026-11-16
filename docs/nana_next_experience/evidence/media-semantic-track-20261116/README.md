# 原S5技术观测到H1模型输入：同轨、真实覆盖

A基线3608bd0 / Brain269。不是另一套视觉算法；直接修原package_media与MediaSemanticService.associate_audio的消费者。复用268原公开多流合成fixture，不复制B的FFmpeg/自适应算法。

## 真实旧行为与现在

原S5已精确第一轨，而package_media再次ffmpeg自动选轨。旧3项实际native失败2.75s：VIDEO技术red而模型打包blue，validate_media_input报MEDIA_FRAME_COVERAGE_MISMATCH；AUDIO自动多轨输出在原raw pipe失败MEDIA_MALFORMED_OR_UNSUPPORTED。第三项同一2秒video/1秒audio容器，associate_audio错误把不等长当不同源而拒绝。269原35pass1fail的正常AAC尾样本场景继续保留，未修改原测试断言。

现在package_media明确-map 0:v:0/0:a:0，原技术摘要/字节digest/part时间/模型输入验证在同一轨。VIDEO模型wire实测red、AUDIO实际16k mono静音，经原CognitionSession→MEDIA fixture→ground保存MODEL_DERIVATION，非模型生成事实/新任务/权限。源撤回后ground拒绝。

associate_audio仍要求VIDEO/AUDIO顺序、完全相同编码字节digest、各自PROPOSED/grounded且可读有效；不再把等长当同源必要条件。新结果保存video_duration_s和audio_duration_s，temporal_alignment明确NOT_ESTABLISHED。只证明同容器，不声称音画同步、音轨覆盖全片、时间原点一致或字幕已校对。不同文件/角色对调仍拒绝；重复0新record/模型，撤回audio使关联依赖失效而独立video保留。旧已保存关联原样返回，不改历史记录或靠自动重写补资格。公开payload仅加字段，无schema/私有模型权限变化。

## 验证和成本

related73.txt实际73passed31.67s：原H1（含正常AAC关联/真实SIGKILL恢复/隐私与grounding）、H1-live、S5多流、H2捕获。随后resource3.txt只重跑新增3项3.57s，实测原decode VIDEO3进程/AUDIO2进程，原package各1进程，不新增进程/模型阶段；每个单轨场景仍1个原fixture Provider请求。同预算通过，不声称真实Provider Token/费用/内容准确率或P95改善。无新依赖/商业调用/账号/设备/安装/发行。

原269独立CI run43891338072/job133383385077：Native host实际success，原46passed38.92s，ci269-core46.txt保留。客户端当时仍执行，不能把Core成功冒充整个run通过。旧265/267/268第一次导出脚本JSON转义错误留下空文件，记录时未检查非空是本次证据保存错误；已从同一实际连接器日志恢复，全部>10KiB，校正原source.sha256与09锚，未伪造重新跑CI。本修复源270尚需自身独立CI，原265/268失败事实保持。

## 接续

模型端观察与原S2/C支持关系接通；真实视觉理解、ASR、非零起点同步/原片覆盖与B22自适应融合仍待，非两仓视觉完工。旧9a2候选不含264及以后，CURRENT266+409。继续S3多动机/可靠结果与G广迁移、私QQ父来源/私Bili保留前C、B22原生适配以及原A–H/匹配发行；无真实模型/手机/生产/自然度/实际长期新增资格。回退仅本semantics.py与对应新增测试，无DB迁移；不建议为回退重新引入观测错配。
