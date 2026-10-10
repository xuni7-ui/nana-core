# Nana Core V1 — 开发权限边界与真实能力验证准备

> [实测] 基线 `b2b5b99e69377d024bbb58c13d9f2564dccea9f5`；开发分支
> `dev/nana-core-v1-dev-validation`。本轮延续 S0—S6，不改变总体架构。
> 实际文件工具与真实 HTTP 协议已工程验收；真实模型推理和 E12 **NOT_RUN**。

## A：权限边界

本轮没有建立有效生产访问路径，也没有获得生产操作授权。不能据此断言所有可能的
技术访问都不存在；不可读目录和不可查的远端设置保留 UNKNOWN。

| 类别 | 本轮实测与范围 | 未验证部分 |
|---|---|---|
| 托管配置 | environment_status 当前一致；capabilities、secrets、runtime variables、outbound identities 均 0 | 不证明未知文件中没有凭据 |
| SSH/远程命令 | 无 SSH agent、SSH/部署类变量或 Git SSH override；未尝试登录 | `/root` 候选元信息被拒；生产主机网络/鉴权未探测 |
| 挂载 | 可见 mountinfo 无生产命名挂载；常见生产目录不存在 | 泛名挂载、不可读位置及卷来源无法全部排除 |
| 容器 | Docker socket 存在；默认沙箱只读 socket 请求 PermissionError，连接数 0 | 原脚本未记录异常阶段；不能确定在 socket 创建还是 connect；daemon/生产关联未知 |
| 凭据 | 只枚举变量名字；GH_TOKEN 为 GitHub 客户端的现有访问路径；OPENAI_CLUSTER 不是开发模型端点 | 不读取变量值或候选密钥内容，不核验生产凭据 |
| 本地部署 | 无活动 Git hooks、workflows 或部署配置 | 不能排除外部服务轮询 |
| GitHub | 私有、main 为默认、push 权限；Actions workflows 0；webhooks GET 返回 403 | 集成无 hooks 读取权限，推送 webhook/外部自动部署 UNKNOWN |

依据：[access_boundary.json](nana_core_development_evidence/access_boundary.json)。
仅进行了三次 GitHub 只读元数据请求（两次成功、一次 403），未读取 hook URL/secret 配置。
repo metadata 的 admin=true 不代表集成被授予 hooks API 权限。
开发测试通过单次命令的 network grant 创建回环服务器；未扩大 Docker 或生产权限。
未申请放开 Docker socket，不 list/exec/start 容器，不探测生产网络。

## B：代码与契约

新增 `src/nana_core/development/file_source.py` 实现既有 CapabilityPort 的
`reading.source.read` / `reading.source.locate`：

- Operator 提供固定 `source://synthetic/` → 相对路径/原始 blob SHA256 的绑定。
- SourceDocument 必须显式 synthetic_only=true；读取目录由实验新建，不接收模型给出的文件路径。
- 拒绝绝对路径、路径回退、非规范路径、符号链接、FIFO/非普通文件和超限文件；逐层 O_NOFOLLOW。
- 只读源文件；完整 hash 核对后才解析。源文件不得动态替换成未钉住内容。
- 执行返回 durable receipt；核验独立重新读取文件并核对原始 hash、内容和既有操作记录。
- 缺少 durable read receipt 或文件已变不能证明未执行，保持 INCONCLUSIVE/UNKNOWN，不重派发。

Receipt journal 复用独立 FakeWorld 的 operations/calls 表；源文件只读并不表示
实验没有本地账本写入。没有新增 Core 表或依赖。Notebook create 仍为 FakeWorld，
不宣称已经实现真实写工具或真实平台接入。

`development/lab.py` / `nana-development` 顺序重开 Store/ModelPort，复用身份、Grant、预算、
ActionKernel、S6 CapabilityRouter、经验和 PlanCompiler。两个阶段运行同一闭环：
真实文件读取 → 合成卡片 → 反馈/经验 → Store 重开 → 计划引用经验 → 实际定位 → 合成新卡片。
每个阶段重复输入五次，仍各只写一张卡片。可选 `--config` 复用 S5 RunConfig，
最多两个已授权开发 ModelPort 顺序运行；未提供端点则使用明确标记的 FixtureModel。

模型适配复用 S5 CompatibleModelPort/HTTPTransport/CallLedger，没有增加第二套模型 SDK。
本轮新增 Endpoint.service_kind：real_model / protocol_simulator / unverified（默认）。
只有 `real_http` **且 Operator 明确声明 real_model** 的调用可纳入 E12；
HTTP 成功、provider model 字符串或别名不能替代真实推理证据。
声明仍依赖 Operator 核实服务，系统不能凭 HTTP 元数据证明远端是否真的执行了模型推理。
历史未带此字段的配置需要明确声明后才能参与 E12，不暗中放宽验收。
协议模拟器必须 loopback；真实本地模型仍可声明 real_model。未核实 HTTP 服务的费用不能写 0。

本轮实现的是受信 Python 进程中的最小适配器边界，不是对任意恶意 Python 代码的 OS 沙箱。
没有读取生产源码之外的运行配置、数据库、私人记忆或凭据。

## 实际验收

- 新增 **31 tests passed / 0 failed / 0 skipped**。
- S0—S6 加本轮联合 **158 passed / 0 failed / 1 skipped**；唯一 skip 为真实模型 E12。
- 实际 CLI：两张合成卡片、五次能力执行/五次核验、三次实际文件执行读取/三次核验重读。
- Store 重开后同一身份和 Grant；源文件 byte hash 未变；重复输入无重复卡片。
- 第一阶段无定位，形成一条经验；第二阶段引用这条经验并新增真实定位读取。
- 若模型首次自行定位，后续累计定位不能冒充经验效应：必须存在新增策略、第二阶段引用和定位增量；
  无新增经验时 experience_effect=NOT_DEMONSTRATED、该实验 engineering_gate=FAIL。
- 新测试子进程在读工具 durable receipt 后实际 SIGKILL -9；恢复身份一致，零重新执行、一次核验重读。
- 7 个真实 socket/HTTP 测试的服务器均为确定性 protocol_simulator。
  最终一次回归实际发生 **8 次 loopback HTTP 请求**；连同先前专项运行，本轮共 **16 次**。
  这不是 16 次真实模型推理，不纳入 E12。
- 真 HTTP 覆盖成功解析、统一工具链、HTTP 重定向拒绝、伪造 success 拒绝、超大响应拒绝、
  断连 UNKNOWN、尝试预算耗尽、未决不重试；真实模型/公网工具/生产调用均为 0。

证据：[test_results.json](nana_core_development_evidence/test_results.json)、
[JUnit](nana_core_development_evidence/junit.xml)、
[实际测试输出](nana_core_development_test_output.txt)、
[CLI 证据](nana_core_development_evidence/development_report.json)、
[真实崩溃与 HTTP 证据](nana_core_development_evidence/integration_proof.json)。

早期运行如实保留口径：文件工具/受影响 S5 先 65 passed；默认沙箱运行 23 passed / 7 failed，
七项均在 socket 创建时 PermissionError，未发生 HTTP 请求。开发 network grant 下七项通过。
一次不带明确测试目录的 --development-report 命令在参数解析时 exit 4；明确四个目录后收集并通过。
经验效应误标风险由只读复核发现并修复，增加否定测试；没有削弱断言或以 mock 替代 wire 测试。

## 复现与真实模型门槛

```bash
.venv/bin/python -m nana_core.development.lab --output /tmp/nana-development-new
.venv/bin/python -m pytest tests/offline_continuity tests/semantic_migration tests/migration tests/development \
  --development-report /tmp/nana-development-tests.json
```

HTTP 测试需要允许本机回环 socket；测试 guard 拒绝非回环连接，服务器测试结束即关闭。
未安装新依赖。项目安装后 pyproject 新 CLI 生效；当前可直接使用 python -m。
所有运行目录必须是新的开发路径，DB/WAL/lock 不上传。

E12 在新冻结快照上实际运行 evaluate 的 readiness 路径，端点 0、调用 0、快照未变：
[semantic_report.json](nana_core_development_evidence/semantic_report.json)。
待提供两个明确 development / existing_quota（或真实 local_offline）端点、
`service_kind=real_model`、独立 NANA_S5_DEV_* 绑定及保守预算，再运行已有 nana-semantic
prepare/evaluate 的同快照、未见案例、消融对照与双模型顺序流程。
本 lab 即使未来使用真实端点，也不能替代这个 E12 门。

未验证：真实模型语义迁移、真实用户材料、公网只读工具、生产挂载/SSH 鉴权、不可查 webhooks/外部轮询、
真实写能力或生产迁移。外部模型费用 0；GitHub 保存本轮分支为明确授权，main 不合并、不部署。
本轮原创许可继续由所有者决定，没有复制第三方宿主派生实现。
