# B22机制最小原生吸收：容器相对PTS进入原S5/C/H1

A / Advanced S5及S2/S3/S6/S7因果。原基线4f25b48a / Brain280；B22仍draft，固定d63c1ba163c47209aafda00b46768615a531c29f。本次实际读其tools/nana_next_experience/experiments/video_pts_decode.py，吸收容器相对时间与有理数PTS思想到原MediaDecoder，不调用B不带沙箱的原型runner，不合并整个研究PR。dsh变化/长视频覆盖/窗口/旋转/语义取帧仍候选。

## 有效真实字节原版失败

用FFmpeg7.1.5生成32x24/red/25fps/1s MPEG-TS，共8460bytes，SHA633f142b3cb422db0eed058c53dcb03473e025eea2a9a48013356bc952fc136a。实际format.duration1、start_time1.440000、video time_base1/90000。原代码把绝对PTS1.44当成播放时间并要求<1，拒绝MEDIA_FRAME_TIME_INVALID，因而该有效容器无法进入原技术观察/私人疑问/H1。原3failed1.56s保留；不是放宽任意格式、模型自述或世界语义真值。

原封签ni277与新源码实际对同一个不变文件读取：旧2ffprobe后拒绝，新2ffprobe+原1ffmpeg成功；两边SHA相同，未改封签槽。新elapsed.348s，旧拒绝.229s，不把错误少做工作称节约。新caller CPU.00378s只是父进程，FFmpeg子进程CPU/实际峰值RAM未测，不以RLIMIT假装实测。探针原生子进程输出大小均记录。原source input16MiB、30s、4096实际帧/8样本、512MiB进程上限/CPU10s/墙12s、file/pipe协议及bwrap隔离全部保留，无私视频落盘支持放开。

## 原生变化及消费者

原ffprobe同第一视频流多读整数best_effort_timestamp，使用原stream time_base，在原沙箱外轻量Fraction换算相对container origin；匹配AVFormat微秒起点的最早精确stream tick，避免24fps起点微秒舍入造成伪负时间。不是把视频第一帧强制归零：较早音轨存在时保留真正的leading video gap。metadata帧数先按原4096界检查，不为超界列表先做复杂换算。

非零origin帧保留source_pts_ticks/source_time_base/timeline_origin_s，供实际source byte digest回溯；缺整数元数据时保留实际时间文字换算。0origin保留原timestamp_time投影，避免无关老source摘要改变。本次实际226158B多轨MKV SHA95abed512977fe0d9af1081f55f494e4721710187448439b56c6d25db1282eee，旧/新完整decoded对象相等，均3原生进程；frame probe485→651B增加166B，elapsed.345→.348s单样本不称普遍性能/成本结论。新TS decoded payload2748B是bytes不是Token。

原S5 Source/Memory/Record/World接口没有新增顶层schema或第二缓存；原C现能从该来源的实际红色像素统计形成原私人疑问，撤回原媒体使其来源支持失效，没有Goal/Grant/动作。原H1打包同一第一轨/对应frame index，MEDIA parts时间0..1，实际ground仍EXPLICIT_SEGMENTS并保留采样间空白；较早音轨的video gap和来源撤回拒绝继续生效。C为一个明确synthetic ModelPort，H1为一个loopback MEDIA，不是真实模型或视频语义能力评分，不伪造看到完整影片。

## 验证与首次失败

最终原world/H1两个文件16passed9.55s，包含0origin/多轨、音视频长度不等不宣称同步、旧尾部未知、missing/N/A/legacy packet duration、非零origin→C/H1/撤回、24fps精确tick及真实leading gap。此前同3目标4.16s、首轮14过8.48s+一个FFmpeg参数fixture错误（-itsoffset .5须写0.5）、修该单项1过1.15s、量化2过1.61s都保留，不混作一次全仓。

原相关七文件81passed/1failed23.29s，失败是原Bili UNKNOWN重启后独立帧在100ms请求预算下STALE。实际账本表明prepare提交已晚于deadline，terminal晚69527us；未触发新VIDEO代码（Bili帧仍IMAGE），未删断言/调超时/重发UNKNOWN。待原生重活完成后，固定旧ni277同项1passed.69s/100业务模块、当前同项1passed1.01s。保留首错与时间敏感差额，不把82项称整批通过，也不以此改生产默认120s。首次相关选择写了不存在h1_live_semantics/test_boundaries.py，0项执行，改为已有test_wire.py才运行，单列为选择错误。

280匹配独立CI run43958311970/job133618977017实际179pass/1warning38.76s，clientSKIP，完整日志归档；不是本281匹配CI。现281待推送后实读独立结果，尤其原100ms情形，不能提前填PASS。

## 后继

这是B22机制的局部原生吸收，B/C原负责人职责和现役PR14/17/18/20/21/23/24保持。真实Bili视频字节来源、私人媒体/保留、跨流时钟对齐、长视频/实时队列和两仓完整自适应准确率/成本对照仍需原任务开发；公开storyboard不能冒充平台原始视频attestation。

下一核对原PerceptionService重复同来源时仍先重新解码的问题，在原Memory/Record权威中复用已保存且支持有效的同一观察，兼顾来源/实体/范围/撤回/字节冲突，不建立第二事实缓存；为后续自适应采样保留旧源连续性。原S3长期/S8-S10/物理存储Token/多端及A–H继续。b196两槽联合候选不含279–281后继，不每次修改打APK/全仓；CURRENT266+409不变。真实模型、手机、账号、生产、自然度、实际长期未新增资格。
