# Execution Context Awareness & Host Target Routing

GLOBAL_STAGE H · Advanced Growth · S4/S5/S7 + Governance/Surface axes.
基线：`7a1bce994d7640389b48202e8de27be7c715eb97`；独立开发，不更改 Master、63 条 Foundation、主体、schema13/43表、Provider 或 CotEX UI。

## 实际缺口和修复

| 原代码/缺口 | 实际修复 | 验证范围 |
|---|---|---|
| `host_probe.py` 的 root/systemd/path 来自当前进程，缺环境绑定 | 明确 current user/mount namespace，缺路径只证明此环境缺失；Docker daemon 来源单独标 UNKNOWN | 实际开发进程 + subprocess CLI；不是云宿主 |
| Hands 检查 UID/PID/inode，缺 mount/user namespace 和 dev | 构造时 pin 本地内核 context，调用时重新检查；IPC peer 必须同 user/mount namespace；证据附 dev/inode/context/time | 原 C/Hands/Learning/Manager 相关套件及本轮新测试 |
| 普通绝对路径可能被误当成全局资源 | `ResourceBinding` 将原 capability URI 映射到明确 target 和 canonical path，按 context/dev/inode 区分 | 独立 Kernel 实际本地文件效果 + 合成跨 namespace 场景 |
| 宿主通道未提供时容易退回容器执行 | 只选已显式注入、匹配 pin 的通道；HOST_OPERATOR 优先 SSH；无通道阻断，无隐式 Docker/SSH/credential discovery | 合成 channel selection；真实远端 NOT_RUN |
| UNKNOWN 可能被环境修复理由触发重发 | 原 Kernel 保留状态；prepare 原子记录 pin，dispatch durable claim，恢复只独立 Verify，不切通道 | 实际本地效果丢回执、重新打开同 Store、核验且调用次数不增加 |

## 模块与信任来源

`src/nana_core/execution_context/contracts.py`, `probe.py`, `routing.py`, `port.py`。

`LocalContextProbe` 只读有限内核元数据、目录句柄和 stat，不读正文、环境变量、账户数据库或 credential。采集：numeric UID/GID/supplementary groups；user/mount/pid namespace；父层 uid_map/gid_map；capset、NoNewPrivs、Seccomp；根 dev/inode；mount table fingerprint；容器信号。Namespace ID、boot 摘要、权限或 mount table 改变时 context pin 改变。

账户显示名不参与判断。UID999 的权限含义只在其 user namespace 内成立；父层映射不自动等于物理宿主 UID。capset/UID/可见文件 mode **不是**某操作一定获准的证明，LSM、网络和操作级权限仍须由实际执行层及原治理检查。

容器 marker 是线索；没有 marker 不证明 HOST。`ContextBinding.scope`/target 名字是受信任应用配置声明，不是内核远端身份证明。HOST_OPERATOR/SSH 对端必须先由宿主现有可信通道认证，再交出 peer-side probe/port；模型文本、网页或 JSON 自报不能注册通道。当前仓库没有实际启用的此类宿主连接，本轮也未创建连接。

mountinfo 可说明 overlay/subtree、挂载点、只读标志和 filesystem root；不读取 overlay lowerdir/upperdir，不将 source/options 原文输出。SUBTREE **不证明** bind 来源、宿主持久化或两个路径相同。跨环境路径翻译仍须 operator 提供经过核验的映射，本组件不会猜 `/opt`→`/srv` 或自动操作另一个根目录。

## 执行与恢复

1. 可信宿主应用构造固定 `TargetBinding`、`ExecutionChannel`、`ResourceBinding`；配置不来自模型。
2. 原 Kernel 在 Grant 检查后、原预算事务内，对精确 `ContextBoundPort` 调用 `reserve_context`。保存 action-specific route/path observation 到现有 `core_meta`，不新增表、Subject Memory 或配置权威。
3. 当前 source/target 必须有完整、≤5秒且非未来的 observation；证据同时绑定 target、channel、path、context、time。
4. 写操作须绑定已存在的受控文件/目录锚点。创建新文件时绑定其现有 owned directory，缺失锚点阻断；不会对“另一个环境里可能存在”的路径写入。
5. dispatch 重查原 invocation/action/attempt、Grant/预算和 exact route，先写不可重复 dispatch claim，再调用已有 CapabilityPort；绝不生成 Grant 或 shell。
6. 原 CapabilityPort 独立 Verify 决定 MATCH/失败/UNKNOWN，router 不自判成功。合法原子替换文件允许 inode 改变，Verify 仍检查同 context/path/channel；效果正确性由原 verifier 判断。
7. UNKNOWN、崩溃或过时 pin 不重试、不切到另一个宿主。环境修复仍是原 C 提出、原 Manager/Grant/Kernel 执行和 Verify；这里不新增 repair executor 或用户逐步批准门。

action pin/claim 是历史执行来源，不是可携带的宿主权限。恢复/迁移保留原 lineage、Grant 撤销和 ownership 约束；新环境需要重新绑定。不存在旧 pin 的旧 action 不会被此 decorator 自动补造或重放。

## 集成边界

原 `ActionKernel` 只新增精确 decorator 的 preparation hook。已有 port/registry、预算、Manager 空气墙和 SubjectLoop 不变。原 Hands 的 local namespace hardening 默认生效，原 C 自主任务走的仍是同一个 Hands。

新的通用 decorator 需要宿主应用显式接线；**没有放宽** `GovernedRealization`/shadow 的四种 sealed port 白名单。远端系统修复尚未接进 autonomous production capability；不能把本地 fixture 核验冒充已具备任意宿主控制。现有合法自主目标、兴趣、学习与自扩展没有默认关闭。

前端 API/DTO/native allowlist 未变；Nana Space 不获得 host routing 配置权。旧 standalone `host_probe.py` 现在需要对应新版已安装 Core 包；运行时目录必须显式绑定到合格 release，不能拿旧包缺模块当作云宿主不存在。新 portable allowlist 包含全部5个组件模块。

## 资格等级

- 当前：实际本地 metadata/Kernel/文件效果、原 Hands 兼容，以及合成跨环境路由离线资格。
- HOST_DEPLOYED / REAL_HOST_ROUTING / ANDROID_CONNECTED：NOT_RUN。
- 无真实 provider/private/social/生产操作；正式 Genesis、手机部署由既有主线继续，不以本组件为新前置门。
- First-Life/Beta 和 Human Naturalness 历史状态不升级。

最新实际测试、源码 pin、失败修复和 package 验证见 `evidence/qualification.json` 与原输出；不将测试总数当作开放环境能力证明。
