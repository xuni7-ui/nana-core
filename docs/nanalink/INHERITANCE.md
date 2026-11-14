# NanaLink C · 继承与实施差额

[实测] 2026-11-14 Asia/Shanghai；现役基线 `87c32b3290687c4e2ab8dc674dcc36ff4653ac3c`，从远端现役分支创建独立 worktree/`feature/nanalink-unified-platform`。原 `work@18bc736` 保留，未提交变更为零。PR14/17 为 B 候选 d409a55/30459c5，均未合入；base45e7432不是当前A。PR5–13已合入治理成果继承，PR16由14替代。未查到NanaLink或独立QQ Gateway的现役PR；未提供的旧聊天回执为未知。

权威任务入口是 PROJECT_BRAIN/09_STATE.md 的C段。本文件只说明源码映射。归属Platform横轴及S1-C03/S2-C01,C02,C04/S4-C04,C05/S5-C01/S7；Advanced接口扩展，不修改冻结Master/Matrix或A主体机制。

| 旧事项/源码 | 继承状态 | C的增量 |
|---|---|---|
| life/platform_runtime、platform_bridge；QQIngress/QQCapabilityPort/QQGovernedDelivery | 已实现、历史受控HTTP已测试；真实账号未知 | 复用原绑定、独立回读、原Kernel；新增WS会话，不建QQ决策器 |
| live_api/platform_events、platform_forward | 已实现签名metadata/有界队列 | 复用转发；传输ACK不等于送达 |
| patches/astrbot/*qqofficial* | 已实现历史补丁；现役官方账号未知 | 保留官方路径/依赖；OneBot资格不推广为官方Bot资格 |
| bili_agent/event_source、event_pump、send_core；C.4/C.5-V | 旧有设计与证据 | 复用纯normalize；发送继承现役Core，旧pump决策路径由统一Core接入取代 |
| life/bilibili{,_account,_runtime,_life,_frames} | 已实现、历史受控测试 | 包装字幕/采帧/兴趣选择/回执，不重写Agent |
| SurfaceSession/MemoryService/RecordService/ActionKernel/Grant/Runtime | 现役权威 | 不建主体、Store、记忆、认知调度器或权限中心 |
| Nana Space PlatformPanel、native凭据/CAS/OperationLedger | 已实现；首次连接步骤不足 | 原页面增强能力、健康与向导，不建第二前端 |
| 统一SDK registry、WS/reverse WS、会话健康、第三源 | 基线缺少统一实现 | 本C开发；测试/账号/手机/生产分别记账 |

## SnowLuma优先评估

[实测] 指定GitHub repo、raw LICENSE/package.json、官方介绍页当前404；NapCat LICENSE亦404。未下载/复制受限源码或native二进制。不能据搜索摘要判定当前完整分发许可。

[文档，索引2026-11-14] [官方README](https://github.com/SnowLuma/SnowLuma/blob/main/README.md) 描述真实QQ会话、每UIN实例、OneBot/WebUI/SDK，source-available非商业许可、公开衍生分发/商业需书面许可、native专有；[部署页](https://snowluma.github.io/en/docs/guide/deploy/docker) 描述ptrace及seccomp限制。这些是待原文回验的设计线索，不是复用授权。本C独立实现标准OneBot网络兼容，不分发/自动安装QQ、SnowLuma或NapCat。用户自行取得外部服务时适用其自己的许可。

Native research尚缺可核对addon接口许可、客户端版本、目标host能力及可重复维护收益；不启动独立注入研发。未来验证须在独立侧车进行，Core不提权、不增SYS_PTRACE、不共享宿主PID。普通WS/HTTP兼容无需进程注入。

## 取舍

版本化连接/观察/动作封套复用原Core持久记录和Kernel。SDK队列及媒体缓存只是有界传输。OneBot WS桥适配原HTTP所需动作，ACK不升级独立Verify。第三源采用实际RSS/Atom读取：标准库解析、无账号、网页订阅感知、无发送能力，固定来源与字节/条目预算。
