# NanaLink · C 开发入口

当前任务/分支/下一项以 [PROJECT_BRAIN/09_STATE](../../PROJECT_BRAIN/09_STATE.md#c-workstream--nana-link-01) 为准；[继承与取舍](INHERITANCE.md) 保留旧QQ Gateway、A/B及SnowLuma许可边界。本目录不是第二本项目账本。

NanaLink是原Core周围的通信基础设施：QQ与B站复用同一`Event`/`OperationReceipt`契约，仍由原`LifeApplication → SubjectLoop → Manager/Grant → ActionKernel → Verify`决定、执行并保存。RSS/Atom证明新增源不改Core；网页出版物经原记忆来源成为WORLD_EVENT机会，不能作为用户指令。未定义另一个Subject/Store/Memory/认知调度器。

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

OneBot 路径可在显式注入本会话 `MediaCache` 时，由原 C 从当前原感知记录选择图片，经过原 Manager、Grant、ActionKernel 和侧车发送一个不超过 8192 字节的内嵌图片。缓存按原记忆 ID 与源字节 SHA256 精确绑定，执行前及账号检查后重核来源；来源撤回、字节变化或缺少权限时拒绝发送。适配器不推断图片或收件人。平台无法独立证明图片字节时回执为 UNKNOWN，不重发。该路径已用 owned HTTP/WS 假平台测试；生产宿主的缓存供给、真实 OneBot 兼容性和真实账号尚未验收，默认管理界面仍标示未支持。QQ 官方 Bot 和表情仍不可用。

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

## 尚未完成的资格/能力

- 真实QQ/B站账号、对外发送、Android实机、生产、长期驻留：NOT_RUN。真实模型费用/每次有效认知成本：未资格；本地基础设施测量不是Token效率收益证明。
- QQ官方后端继承AstrBot适配/原补丁，尚无新的原Core官方Bot闭环；手机有明确说明，不能用OneBot测试代替。Native仅研究边界，当前受限源码/许可原文404，不分发组件。
- 媒体支持统一段、惰性引用和流式缓存；原QQ行动端口仍只发送文字。编辑/撤回/动态发布等没有原权限端口时返回UNSUPPORTED，不能将类型存在说成真实动作已可用。
- B站评论/私信包装原工作流；字幕/采帧/自主视频阅读保留原`BilibiliLife`。C.4通知复用旧纯normalize的可核对分发快照（`tools/nanalink_sync_c4.py --check`），不启动旧Agent/pump/LLM。可选BFF `nanalink_bilibili_sources:["channel-id"]` 复用原事件worker请求原owner的`bilibili-notifications`；每300秒最多3次来源读取、12轮/小时，必须原channel enabled/read/private-read/activation均许可。消息再经原工作流独立回读及原C决定，历史UNKNOWN不重放。动态发布/事件源尚无受控端口，不宣称可用。
- 原Core收发/权限/媒体机制按历史受控范围继承；本C开发验收见evidence，不升级整个工程First-Life/Beta。

## 后继开发候选（2026-11-15）

QQ 官方 Bot 增加独立的 `qq.official` 适配器、原生 opaque 身份与单次 REST 请求路径，AstrBot 宿主插件默认停用。宿主须明确配置账号、独占路由、专用 HMAC、适配器 vault，并在真实授权后运行；botpy 登录会话由宿主维护，插件只转发有限字段与短期令牌。官方 C2C/群没有已资格独立回读，ACK 后 Core 保持 UNKNOWN，不自动重发；不要使用 AstrBot 的自动重试发送接口。旧版配置不含 backend 时仍是 OneBot；旧版 reader 使用前须移除 official 配置。

BFF 新增默认关闭的 `allow_platform_login`，宿主同时启用平台配置及隔离 vault 才能由管理用户在手机上发起 B站扫码；核对账号后经现有 vault 原子保存 cookie 与 CSRF，入口仍暂停。二维码和临时凭据保存在受限 RAM，不进入操作账本。浏览器和 Android 均增加路由，但旧 APK 没有新路由，需要重新构建，实机未验收。QQ 官方走已有宿主登录。

连接器管理只接受宿主批准且已安装的版本；支持停用、离线替换、回退、移除与恢复，默认不下载包。侧车启动时指定 `--management-state` 为私有目录文件可持久保存版本与暂停状态；未指定则仅本次运行有效。异常结果需刷新核对，不重试。连接器管理不授予消息权限。当前随侧车内置目录仅含当前版本，其他版本必须由宿主明确提供工厂与固定版本。

B站订阅动态的私人来源归因和 QQ 非文本行动尚需原主体契约；详见 [最小提案](CONTRACT_EXTENSIONS.md)。此候选仅完成源码与合成测试，真实账号、外发、实机、生产及长期成本仍未验收。

### 私人动态与媒体后继开发

宿主可显式设置 `nanalink_bilibili_dynamics` 为已绑定渠道列表，原事件 worker 每300秒请求原 owner；必须同时配置原账号读取、私人读取、私人保留同意、canonical activation 和预算。源机会使用原 PERSONAL 证据、记忆和撤回闭包，不直接命令主体。当前只读取首20条且未具备平台删除／取消关注的完整变更流；这些情况下不能仅凭事件缺席自动撤回。授权撤销或账号解绑须完成 owner refresh/restart 和撤回核验。

旧版 reader 未知 `CONSENTED_PLATFORM` 来源。回退旧二进制前先使用新版撤回所有相关私人来源并验证原 Store 和备份边界；不要直接让旧版读取含新来源的数据。QQ 可选媒体候选暂不等于媒体已可发送；当前返回 UNSUPPORTED，原文字行为保持。


QQ 官方宿主令牌过期时，控制台显示需要重新登录或更新授权；图片/表情发送在原 C 媒体行动接通前显示不可用，连接健康和收件健康仍独立。隔离开发机可用 Android SDK 35、JDK 21 和仓库固定的 Gradle 8.11.1 生成 debug APK；测试包不是签署发布包，也不能替代实机或账号验收。
