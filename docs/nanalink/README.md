# NanaLink · C 开发入口

当前任务/分支/下一项以 [PROJECT_BRAIN/09_STATE](../../PROJECT_BRAIN/09_STATE.md#c-workstream--nana-link-01) 为准；[继承与取舍](INHERITANCE.md) 保留旧QQ Gateway、A/B及SnowLuma许可边界。本目录不是第二本项目账本。

NanaLink是原Core周围的通信基础设施：QQ与B站复用同一`Event`/`OperationReceipt`契约，仍由原`LifeApplication → SubjectLoop → Manager/Grant → ActionKernel → Verify`决定、执行并保存。RSS/Atom证明新增源不改Core；网页出版物经原记忆来源成为WORLD_EVENT机会，不能作为用户指令。未定义另一个Subject/Store/Memory/认知调度器。

## 现役平台能力与限制（2026-11-24）

| 平台/接口 | 已实现的受控范围 | 尚未资格或不支持 |
|---|---|---|
| QQ OneBot | HTTP、正向及反向 WebSocket；原主体和权限链治理的文字，以及下文限定条件的 PUBLIC 图片；账号和会话独立绑定 | 图片默认未接平台采集；表情、真实平台媒体回读及真实账号未资格。断线不重发 UNKNOWN，断线事件缺口不自动补齐 |
| QQ 官方 Bot | 独立原生身份适配及原主体文字路径；单次发送，缺独立确认时 UNKNOWN | 官方 C2C/群独立回读、真实账号与实际投递未资格；不自动重发 |
| QQ 消息撤回 | 已绑定撤回会产生会话内告警，提醒相关记忆如已保存不会自动撤销 | **不是自动删除**，告警不跨重启持久；可信撤回元数据及原 owner 删除闭包需 A 接线 |
| B站动态/通知/私信/评论 | 复用原事件 worker、授权、来源、记忆和行动；私人动态限明确读取与保留同意 | 实际平台删除、取消关注的完整变更信号未资格，不能以列表缺席推断撤回；动态发布无已治理端口 |
| B站视频 | 原服务提供可用元数据、字幕与故事板帧；`nanalink.video_handoff` 提供来源和有界样本投影、原视频观察及缓存引用核验，已有受控调用证据 | 故事板不是全片视频；该接口不自行获取或证明完整视频字节，也未证明真实 B站视频自动进入原 S5。平台字节绑定、来源派生及完整视频覆盖待接线/资格 |

连接保存不等于账号在线；真实账户登录、对外发送、Android 实机及生产运行均需另外授权和验收。有限的已实现代码及合成测试不得视为上述真实资格。后文保留历史交接，涉及能力状态时以本节和原代码为准。

### 专项交接

- C 源码核查基线 A `6a483b3c48648ae9d093b0aed0d1a4242fbd2171`；PR #25 已合入，PR #27 `636eb880d6fdbfa4fb074549df9493c822e3de28` 的 `media.py`、`onebot.py` 和 `sidecar.py` 已被 A 继承。A 随后加强了原视频观察绑定和原 B站回执；不能将旧 PR 整体覆盖现役文件。
- 在上述 A 固定源码执行 `PYTHONPATH=src:. python -m pytest -q tests/nanalink tests/person_self/test_nanalink_media_choice.py tests/living_release_v4/test_platform_bridge.py tests/living_release_v4/test_bilibili_runtime.py`：169 项通过（46.77 秒），使用隔离环境和合成/本地平台。示例 `--check` 未访问账号或网络，C.4 快照检查通过。旧 #27 的匹配 CI 和历史构建仅证明各自 SHA，详见 [PR #27](https://github.com/xuni7-ui/nana-core/pull/27)。
- A 接手一次性最小契约：以独立可信能力接收绑定账号、路由、会话、发送者及消息 ID 的 QQ 撤回元数据，精确关联原来源并使用原 Store 删除闭包；应覆盖伪造、跨账号、重复和已删除消息不可回读的反例。现有转发凭据只授权元数据准入，不能隐式获得删除权。此前提案保留在 PR #27；无需等待该契约完成本专项交接。
- B 视频候选仍需 A 确定原 S5 派生帧的可撤回来源依赖；平台侧尚需证明账号、bvid/cid、采集时间和字节摘要的真实绑定。不能以模拟或发布者故事板替代这些证据。
- 配置入口与回退见下方；真实账号授权、实际外发、手机、生产和长期运行交 A 统一验收。回退前须按原来源撤销和旧 reader 兼容要求处理，不能仅替换二进制。无本交接引入的数据迁移。

| 层 | 当前源码/可运行范围 |
|---|---|
| L0 | `nanalink.onebot`、`sidecar`：每账号独立凭据/监听/连接；正向WS、反向WS、HTTP；只恢复连接，不重放发送 |
| L1 | `sdk`：v1 manifest、显式安装/发现/启停、离线替换/回退、逐账号故障隔离、异步订阅；`adapters`包装原QQ/Bili工作流 |
| L2 | `contracts`、`transport`：来源/时间/关系/引用/扩展段、队列限额/背压/顺序/优先级/短期去重。跨重启去重和发送回执仍查原Core |
| L3 | `media`：分块传入、按哈希复用、限额/范围读取、来源撤回。B站元数据/字幕/帧/原兴趣驱动阅读沿用现役服务 |
| L4 | `core_bridge`：原QQ/Bili工作流，原Kernel回执只读查询；`feed.FeedCoreBridge`：原PUBLIC记忆来源/WORLD_EVENT机会，不当用户命令、不强制认知或Grant |
| L5 | Nana Space原“设备与连接”页：连接准备、账号尾号/会话、连接与收件健康、能力、暂停/凭据原接口、UNKNOWN说明 |

## 开发安装

在独立开发环境，Python3.12.14；运行实际Core测试须满足原项目SQLite运行门（本次环境3.53.1），侧车不构造Core Store。

```sh
python -m venv work/venv
work/venv/bin/pip install -r requirements-core-dev.lock -r requirements-nanalink.lock
work/venv/bin/pip install --no-build-isolation --no-deps -e .
PYTHONPATH=src work/venv/bin/python -m pytest tests/nanalink -q
PYTHONPATH=src work/venv/bin/python tools/nanalink_benchmark.py
```

前端沿用`apps/nana-space`的`npm ci`、`npm run build`与`npm run test:v3 -- --grep NanaLink`。原生新增`platform.setup`映射，旧APK不会自动获得新native操作；未宣称新APK/实机验收。

SDK插件通过`nanalink.adapters` entry points发现；只有显式host allowlist才能加载已安装包，不从事件/手机文本执行任意模块或下载代码。`install_adapter`可独立安装RSS/OneBot工厂；替换须先disable，保留前一实例可rollback。包版本、配置和映像均应固定；没有后台自更新。

## 无账号启动检查

```sh
PYTHONPATH=src work/venv/bin/python -m nana_core.nanalink \
  --config deployment/nanalink/config.example.json --adapter-vault work/not-used --check
```

这只校验配置，不登录、不解析凭据、不联网、不创建Core。要运行侧车，宿主必须先明确准备独立adapter-only vault（复用现有`DurableSecretResolver`，不挂载完整Core provider vault）。示例42为测试占位；用户真实授权之前不得换入真实会话后启动。

OneBot最小网络API保持`get_login_info/get_msg/send_private_msg/send_group_msg`。每账号独立loopback端口是给宿主部署者的内部参数，普通手机流程默认不用编辑它。正向WS连`ws/wss`服务；反向WS让外部服务连接`/reversews`，带Bearer及匹配`X-Self-ID`；HTTP事件`/events`遵循OneBot SHA1签名。侧车到Core继续走已有SHA256签名metadata接口，仅交message ID，原Core独立取回内容/账号/会话。

Core的QQ endpoint指向侧车loopback origin，凭据只引用该账号的`core_api_secret_ref`。不要把upstream token和Core API token复用。每个route精确绑定sender/conversation/channel；未绑定的来源不进入模型。`allow_send=false`默认不发；改为true仍不替代原C、Grant、canonical activation和独立Verify。

## 受控图片发送资格

OneBot 路径可在显式注入本会话 `MediaCache` 时，由原 C 从当前原感知记录选择图片，经过原 Manager、Grant、ActionKernel 和侧车发送一个不超过 8192 字节的内嵌图片。缓存按原记忆 ID 与源字节 SHA256 精确绑定，执行前及账号检查后重核来源；来源撤回、字节变化或缺少权限时拒绝发送。适配器不推断图片或收件人。仅当独立 get_msg 回读同时证明账户、会话、文字和原始图片字节哈希一致时才记为成功；无法独立证明时回执为 UNKNOWN，不抓取回读中的 URL，也不重发。该路径已用 owned HTTP/WS 假平台测试；原 owner 可显式调用 `PlatformRuntime.open_qq_media_cache(channel_id)` 创建按账号隔离的临时缓存，也可用 `bind_qq_media_cache(channel_id, cache)` 绑定调用方管理的缓存；自建缓存解绑及正常关闭时清理，异常崩溃后的残留不作为已验证清除；不同账号不可共用缓存，账号或端点变化即解除绑定，重启不继承。宿主可通过 `cache_qq_observed_image` 显式提供已经由原感知服务观察的 PUBLIC 图片字节；该方法核验来源、关系实体、SHA256 和撤回状态，不执行下载或授权。默认不绑定，平台媒体采集、真实 OneBot 兼容性和真实账号尚未验收，管理界面仍标示未支持。QQ 官方 Bot 和表情仍不可用。

## 手机使用与健康

原Nana Space“设备与连接”→“添加平台连接”→选择QQ OneBot或B站→账号/对象→保存。使用原认证、CSRF、CAS、OperationLedger；只创建暂停配置，read/send/private-read/retention/activation全部不授予。复用Android安全凭据输入，二维码/OAuth仍由实际客户端/平台提供。宿主须完成账号授权和匹配Core重启；按钮/保存成功不声称已连接。

可选BFF `nanalink_observers`配置（空值序列化省略，旧host默认不变）：

```json
{"platform":"qq","account_id":"42","channel_id":"primary","endpoint":"http://127.0.0.1:18790","credential_ref":"adapter.qq.primary.core"}
```

只探测显式配置的侧车（每次最多4个、各0.5秒），不访问账号API或模型。观测校验精确account key，页面分别显示会话连接与收件状态。更多账号标明未观测数量，不冒称都健康。

## 容器、回退与边界

`deployment/nanalink/Dockerfile`固定Python基础映像digest和独立依赖锁；只COPY受控Core源码。普通构建：

```sh
docker build -f deployment/nanalink/Dockerfile -t nana-link:1.0.0-dev .
```

受控开发代理若需CA，使用BuildKit `--secret id=proxy_ca,src=/path/to/ca-bundle`；CA不写入层，不关闭TLS。Compose是显式开发模板，共享指定现有Core的**网络namespace**以兼容原loopback约束，非共享PID；不挂Docker socket/Core DB，不增加ptrace、capability或宿主权限。UID999、只读rootfs、全cap-drop、192MiB/0.5CPU/pids64。vault及其父目录应为UID999/0700、内部文件0600；宿主复制/授权需单独实施。

停侧车可回到原OneBot HTTP服务并恢复原QQ endpoint/凭据引用；不删除Core原admissions/actions/UNKNOWN。Core旧schema/主体表没有变化。新配置中的`nanalink_observers`给旧BFF前应恢复旧host配置；新增platform/setup旧服务返回404，不由客户端反复提交。反向WS没有协议历史恢复保证，断线期间事件可能有缺口；从未把重连成功写成完整历史补齐。

## 历史资格记录（早期检查点）

- 真实QQ/B站账号、对外发送、Android实机、生产、长期驻留：NOT_RUN。真实模型费用/每次有效认知成本：未资格；本地基础设施测量不是Token效率收益证明。
- QQ官方后端继承AstrBot适配/原补丁，尚无新的原Core官方Bot闭环；手机有明确说明，不能用OneBot测试代替。Native仅研究边界，当前受限源码/许可原文404，不分发组件。
- 媒体支持统一段、惰性引用和流式缓存；原QQ行动端口仍只发送文字。编辑/撤回/动态发布等没有原权限端口时返回UNSUPPORTED，不能将类型存在说成真实动作已可用。
- B站评论/私信包装原工作流；字幕/采帧/自主视频阅读保留原`BilibiliLife`。C.4通知复用旧纯normalize的可核对分发快照（`tools/nanalink_sync_c4.py --check`），不启动旧Agent/pump/LLM。可选BFF `nanalink_bilibili_sources:["channel-id"]` 复用原事件worker请求原owner的`bilibili-notifications`；每300秒最多3次来源读取、12轮/小时，必须原channel enabled/read/private-read/activation均许可。消息再经原工作流独立回读及原C决定，历史UNKNOWN不重放。动态发布/事件源尚无受控端口，不宣称可用。
- 原Core收发/权限/媒体机制按历史受控范围继承；本C开发验收见evidence，不升级整个工程First-Life/Beta。

## 历史后继开发候选（2026-11-15；状态以现役能力表为准）

QQ 官方 Bot 增加独立的 `qq.official` 适配器、原生 opaque 身份与单次 REST 请求路径，AstrBot 宿主插件默认停用。宿主须明确配置账号、独占路由、专用 HMAC、适配器 vault，并在真实授权后运行；botpy 登录会话由宿主维护，插件只转发有限字段与短期令牌。官方 C2C/群没有已资格独立回读，ACK 后 Core 保持 UNKNOWN，不自动重发；不要使用 AstrBot 的自动重试发送接口。旧版配置不含 backend 时仍是 OneBot；旧版 reader 使用前须移除 official 配置。

BFF 新增默认关闭的 `allow_platform_login`，宿主同时启用平台配置及隔离 vault 才能由管理用户在手机上发起 B站扫码；核对账号后经现有 vault 原子保存 cookie 与 CSRF，入口仍暂停。二维码和临时凭据保存在受限 RAM，不进入操作账本。浏览器和 Android 均增加路由，但旧 APK 没有新路由，需要重新构建，实机未验收。QQ 官方走已有宿主登录。

连接器管理只接受宿主批准且已安装的版本；支持停用、离线替换、回退、移除与恢复，默认不下载包。侧车启动时指定 `--management-state` 为私有目录文件可持久保存版本与暂停状态；未指定则仅本次运行有效。异常结果需刷新核对，不重试。连接器管理不授予消息权限。当前随侧车内置目录仅含当前版本，其他版本必须由宿主明确提供工厂与固定版本。

B站订阅动态的私人来源归因和 QQ 非文本行动尚需原主体契约；详见 [最小提案](CONTRACT_EXTENSIONS.md)。此候选仅完成源码与合成测试，真实账号、外发、实机、生产及长期成本仍未验收。

### 私人动态与媒体后继开发

宿主可显式设置 `nanalink_bilibili_dynamics` 为已绑定渠道列表，原事件 worker 每300秒请求原 owner；必须同时配置原账号读取、私人读取、私人保留同意、canonical activation 和预算。源机会使用原 PERSONAL 证据、记忆和撤回闭包，不直接命令主体。当前只读取首20条且未具备平台删除／取消关注的完整变更流；这些情况下不能仅凭事件缺席自动撤回。授权撤销或账号解绑须完成 owner refresh/restart 和撤回核验。

旧版 reader 未知 `CONSENTED_PLATFORM` 来源。回退旧二进制前先使用新版撤回所有相关私人来源并验证原 Store 和备份边界；不要直接让旧版读取含新来源的数据。QQ 可选媒体候选暂不等于媒体已可发送；当前返回 UNSUPPORTED，原文字行为保持。


QQ 官方宿主令牌过期时，控制台显示需要重新登录或更新授权；图片/表情发送在原 C 媒体行动接通前显示不可用，连接健康和收件健康仍独立。隔离开发机可用 Android SDK 35、JDK 21 和仓库固定的 Gradle 8.11.1 生成 debug APK；测试包不是签署发布包，也不能替代实机或账号验收。
