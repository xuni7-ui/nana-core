# Nana Space — 真实开发 Core 接入

## 本轮完成的范围

从 `87f73d235d593a0d852bca409b0e73e0ef67cc5e`（Precision V2 revision31，限定工程资格通过）建立独立 `dev/nana-space-core-integration-v1-codex`。沿用 V1 前端；所有新改动仅位于 apps/nana-space，不修改 Core、冻结框架、主线状态或 staging。

现在有两条明确分开的入口：

- Demo：原 V1 的固定示例、流式、记忆和生活故事。
- DEV CORE：实际隔离开发进程、原 Subject 身份、现存 Inspector V1 元数据和原 Core 返回的对话。断线不使用 Demo 补齐。

这不是生产奈奈。测试创建全新开发 home；同一 home 跨进程恢复仍沿用该开发 Subject ID，不复制或接管用户主体。浏览器没有 SubjectLoop、Store 或 Grant。

## 启动（Linux，Python 3.12+，Node 22+）

必须检出完整集成分支，保留它对应的 Core 源码；单独的 V1 静态压缩包不包含 Core。

```bash
git clone --single-branch --branch dev/nana-space-core-integration-v1-codex https://github.com/xuni7-ui/nana-core.git
cd nana-core/apps/nana-space
npm ci
npm run build
python3 -m venv .venv
.venv/bin/pip install -r gateway/requirements.txt
.venv/bin/python gateway/dev_instance.py init --home /absolute/new-owned-nana-space-dev
```

init 仅接受尚不存在的目录，打印新开发 Subject ID。配置禁止付费 Provider、自动材料任务、技能和执行 Grant，绑定固定 nana.space Surface；不会导入私人历史。失败后的部分目录应先由操作员检查，不自动清空。

终端 A，复制刚打印的 Subject ID：

```bash
.venv/bin/python gateway/dev_instance.py run \
  --home /absolute/new-owned-nana-space-dev \
  --subject-id YOUR_DEVELOPMENT_SUBJECT_ID --seconds 3600
```

终端 B：

```bash
.venv/bin/python gateway/server.py \
  --home /absolute/new-owned-nana-space-dev \
  --subject-id YOUR_DEVELOPMENT_SUBJECT_ID --port 4174
```

网关通过隐藏输入提示获取 12–128 字符的本机会话口令，仅内存保留；不要填写 Provider Key。脚本化场景可用 --auth-fd 从已安全准备的 FD 读取，不能把口令放在 argv、URL、VITE_* 或配置文件中。

打开 `http://127.0.0.1:4174/?source=core`，填写同一个开发 Subject ID 和会话口令。登录后口令清空，会话由 HttpOnly / SameSite=Strict Cookie 持有。--read-only 可关闭 SEND_INPUT。

只有网关提供真实 API；npm run dev 或 npm run preview 仍是前端/Demo 预览，不自动获得 Core 连接。服务器仅监听 127.0.0.1，不提供公共托管或直接 Android 局域网服务。手机实机远程接入、TLS/多用户认证属于后续生产部署边界。

退出可在各自终端按 Ctrl-C：先停网关，再停自己启动的开发 owner。网关不会启动/停止已有 Core。重启同一开发 home 的 owner 保持身份；重启网关会更换会话 generation，旧 UNKNOWN 不能重发。

## 数据与权限边界

`gateway/server.py` 不构造 Subject/Store，不写 SQL。读取使用现成 Inspector（PUBLIC/PROJECT、有界、只读）及原 ControlServer 的 view/status；消息固定走 surface/SurfaceObservation → 原 owner safe point → app.chat → 原 C 判断。Core 的 lease、PID/UID/inode、隐私和 Grant/Manager 验证保持原样。

Inspector 内部可能更新 SQLite 临时 SHM 读协调标记；这不构成第二权威 Store，也不声称逐字节无读标记。

只公布有限 section，丢弃 self_view/advanced_life/私人意图/任意字典、OS 路径与凭据。只有 ID/状态时不编造目标标题、记忆正文、情绪或长期共同生活史。完整记忆正文、Provider 配置、感知捕获、设备执行、删除/备份/权限修改均未开放。

当前 Provider 为 OFFLINE_NO_PROVIDER；回复可能是 Core 的离线受限固定表达。浏览器显示 provider_state/render_state/judgment/intention 与消息引用，不把它说成真实语言模型生成或外部动作成功。需要付费模型时仍需独立的宿主授权与安全资源绑定。

原 Core 对话文本限制 2048 字，PROJECT classification，不启用 retain_shared_life。用户正文只在原 owner 瞬态处理与当前浏览器会话中保留；Core 按原逻辑保留输入元数据、来源与判断记录。此输入会真实改变开发主体状态，不是只改浏览器。

## HTTP 契约 nana-space-live/v1

同源固定路径 /api/nana-space/v1/；无浏览器配置的 URL、home、SQL、scope 或控制命令。Host 和 Origin 固定，拒绝跨源、重复 JSON key、未知字段和过大请求，无 CORS；HTTP 日志不记录消息/口令。

| 路径 | 行为 |
| --- | --- |
| POST session | 本机会话口令 + 预期 subject_id；一小时 Cookie，单一本机浏览器会话；最多 5 次失败/分钟 |
| GET snapshot | 当前 owner 状态 + Inspector 投影，身份/版本/realm 核对；能力声明 read_only 仅指投影，send_input 单独表示是否允许 PROJECT 输入 |
| POST messages | message_id/text/run_id；固定 SurfaceBinding，输入最多 2048 字；返回原 Core receipt |
| GET receipts/{id} | 核验已有结果，绝不重发原消息 |

成功 envelope 含 contract/subject_id/realm/run_id/as_of_us/execution_authority=false/data。read_only 的投影不会获得执行权；SEND_INPUT 也不是 Grant。

消息接收、原 Core 审阅、模型措辞、外部送达和已验证动作分别表达。相同 message_id + 相同摘要返回既有回执，不再次 dispatch；改正文复用 ID 拒绝。已经 dispatch 后的失败保守为 UNKNOWN，UI 只有核验。网关 generation 不匹配拒绝回放。

回执仅在网关进程内有界缓存 128 项，聊天只保留当前页面最多32轮，不是另一份主体历史；满额后拒绝新增，需操作员结束会话，不自动清空授权或重新发送。重启网关不能恢复未知回执。只读轮询每10秒刷新投影，可取消，不驱动主体意志。

## 验证

```bash
.venv/bin/pip install -r gateway/requirements-test.txt
.venv/bin/python -m pytest gateway_tests -q
npm test
NANA_PYTHON=.venv/bin/python npm run test:live
npm run test:e2e
```

live 测试脚本只为资格测试创建临时实例；qualification-only-access 是公开测试 fixture，不是服务/Provider 凭据，不能用于部署口令。结束时清理它启动的 owner 和临时 home。

真实过程检查覆盖：会话和主体拒绝、原 owner 输入与实际元数据引用、重复消息不重发、实际发送后丢失回复→GET回执恢复、SIGKILL→原身份恢复、断线清除数据、设备/配置/控制接口拒绝、只读模式、桌面/手机视口。

模拟视口不等于 Android 实机。没有声明自然语言模型、人体相处、长期驻留、生产或真实设备资格。具体实测见 STATUS.md 与 validation 下记录。
