# Operator / Core integration

只接到现有可信应用；不修改正在运行的 Host Operator/云服务、QQ、Iris 或 CotEX。

## 本地只读诊断

```sh
PYTHONPATH=/absolute/qualified-release/src /absolute/qualified-python/bin/python -B tools/nana_execution_context/diagnose.py --local-target core-container --path /opt/nana-core/data
```

此命令不会初始化身份，也不会将 scope 从 UNKNOWN 升为 HOST。若请求 `--target host` 而宿主没有向 router 注入此通道，返回 `EXECUTION_TARGET_UNBOUND`，不能解释成宿主文件不存在。工具必须和新 release 一起使用；不要将其命名为 `inspect.py` 遮蔽标准库。

## 原能力接线示例

```python
from nana_core.execution_context.contracts import ContextBinding
from nana_core.execution_context.probe import LocalContextProbe
from nana_core.execution_context.routing import (
    ExecutionChannel, ExecutionContextRouter, ResourceBinding, TargetBinding,
)
from nana_core.execution_context.port import ContextBoundPort
from nana_core.actions import ActionKernel

# All arguments below belong to the existing trusted host application.
probe = LocalContextProbe(ContextBinding(
    target_id="core-container", scope="CONTAINER", binding_id="core.runtime",
))
observed = probe.capture()
router = ExecutionContextRouter(probe,
    targets=(TargetBinding(target_id="core-container", scope="CONTAINER",
        context_id=observed.context_id, channel_ids=("core.local",)),),
    channels=(ExecutionChannel("core.local", "LOCAL", probe, existing_port),),
    resources=(ResourceBinding(resource=existing_resource_uri,
        target_id="core-container", path=existing_owned_directory,
        capabilities=existing_allowed_capabilities),),
)
port = ContextBoundPort(existing_store, router, existing_operator_authority,
                        registry=existing_registry)
kernel = ActionKernel(existing_store, port, existing_operator_authority,
                      registry=existing_registry)
# No Grant or budget is minted here. Original application/governance must admit
# the operation and provide its ordinary Grant before kernel.prepare/dispatch.
```

单进程包装不是对不可信 Python adapter 的沙箱；trusted port 必须真实执行其绑定资源。不得把路径声明当隔离或绕过旧 owned-target/peer/allowlist 检查。

远端 channel 由既有、明确授权且经过认证的 host operator 或 SSH binding 注入；peer 的 probe 与 capability 必须在同一 pin 对应环境内执行，peer 必须在实际 effect 前再次检查 pin。不要仅把 client-side probe 当成宿主 probe。当前没有此绑定，不能提供真实远端资格。

## 错误与行动

| 错误 | 含义 / 正确下一步 |
|---|---|
| EXECUTION_TARGET_UNBOUND / CHANNEL_UNAVAILABLE | 未绑定目标或可用通道；只请求/检查既有通道状态，不检查容器路径代替宿主 |
| TARGET_CONTEXT_MISMATCH / LOCAL_TARGET_MISMATCH | 通道返回错误环境；不写入，核对既有绑定 |
| CONTEXT_UNKNOWN / CONTEXT_STALE | 元数据缺失或过时；通过同一明确通道做新只读诊断 |
| WRITE_ANCHOR_REQUIRED / FILESYSTEM_IDENTITY_CHANGED | 缺受控写入锚点或目录被替换；不自动创建/搬迁身份 |
| ALREADY_DISPATCHED_VERIFY_ONLY | 旧动作可能执行过；只走原 Verify/UNKNOWN 处理 |
| 原 AUTH/Manager/privacy/budget 错误 | 原治理仍决定权限；环境识别不扩大授权 |

低风险已获授权操作不需要新增人工逐步批准。涉及正式身份、私人数据、不可逆/生产操作继续执行原治理；本组件不执行这些动作。
