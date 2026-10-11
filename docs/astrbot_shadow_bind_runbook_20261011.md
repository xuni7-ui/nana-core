# AstrBot Shadow Bind — Runbook & BLOCKED Report (R01, 2026-10-11)

## 0. 状态判定

| 项 | 值 |
|---|---|
| REAL_ASTRBOT_RUNTIME_FOUND | YES（container，PID1=python main.py） |
| AstrBot actual version | 4.28.0 |
| AstrBot execution location | CONTAINER |
| AstrBot dynamic hook supported | YES（源码级） |
| Restart required | **YES（当前配置下，事实）** |
| Internal synthetic dispatch available | UNKNOWN（无安全非重启路径） |
| Observer registered in real runtime | NO |
| Probe traversed real AstrBot dispatcher | NO |
| Nana Core received real-dispatch probe | NO |
| host_binding | **UNVERIFIED**（保持） |
| FIRST_REAL_ASTRBOT_SHADOW | **BLOCKED_RESTART_REQUIRED** |
| Observer removed | N/A（未安装） |
| AstrBot health afterward | PASS（未触碰） |

**BLOCKED 原因**：载入“全新” observer 插件的唯一非重启通道是 Dashboard `/api/plugin/reload`（需 JWT，secret 禁读）；文件 watcher 未开启（`ASTRBOT_RELOAD` 缺省）；`reload(name)` 不载入新目录。→ 遵守边界，**不重启、不读 secret**。

## 1. 推荐观察接法（方案 C：生命周期真实派发）

observer 只注册 **生命周期 hook**（`OnPluginLoadedEvent` / `OnPluginUnloadedEvent`），由 AstrBot 真实 `load()` 内的真实 `star_handlers_registry.get_handlers_by_event_type()` + `await handler.handler(...)` 派发（`star_manager.py:1422-1434`、`2045-2056`）。全程不触消息链、不调 LLM、不发消息、不改 event。

## 2. DRAFT Observer 插件（严格只读 / fail-closed）

安装路径（**全新目录，绝不覆盖**）：`/AstrBot/data/plugins/astrbot_plugin_nana_shadow_observer/`

```
astrbot_plugin_nana_shadow_observer/
├── metadata.yaml
└── main.py
```

`metadata.yaml`
```yaml
name: astrbot_plugin_nana_shadow_observer
display_name: Nana Shadow Observer (temp)
desc: 只读、fail-closed 的临时观察插件，仅用于真实 hook 绑定验证。无回复/无外部网络/无 Iris 写。
version: 0.0.1
author: nana-core
```

`main.py`
```python
"""Nana Shadow Observer — 临时只读观察器（fail-closed）。"""
from __future__ import annotations
import hashlib, time, json, os
from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Star

SCRATCH = "/root/nana_dev/nana-core/bridge/receipts/nana_shadow_evidence.jsonl"

def _scoped_hash(v: str | None, scope: str) -> str | None:
    if v is None:
        return None
    return hashlib.sha256(f"{scope}:{v}".encode()).hexdigest()[:16]

def _sanitize(kind: str, *, source: str, probe_id: str | None = None, **extra) -> dict:
    # 数据最小化：仅允许白名单字段，绝无正文/附件/画像/记忆
    rec = {
        "platform/type": kind,
        "timestamp": int(time.time() * 1000),
        "event_source": source,
        "synthetic": kind.startswith("synthetic"),
        "probe_id": probe_id,
        "binding_proof": True,
    }
    rec.update({k: v for k, v in extra.items() if k in ("plugin_name", "plugin_version")})
    return rec

def _emit(rec: dict) -> None:
    try:
        os.makedirs(os.path.dirname(SCRATCH), exist_ok=True)
        with open(SCRATCH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        logger.warning("[nana_shadow] evidence write failed (dropped)")

class NanaShadowObserver(Star):
    """只观察，不改动，不回复。任何异常立即放弃当前 event。"""

    @filter.on_plugin_loaded()
    async def _on_loaded(self, metadata):
        try:
            rec = _sanitize(
                "synthetic/lifecycle:on_plugin_loaded",
                source="astrbot_internal_probe",
                probe_id="nana-shadow-r01",
                plugin_name=getattr(metadata, "name", None),
                plugin_version=getattr(metadata, "version", None),
            )
            _emit(rec)
        except Exception:
            logger.warning("[nana_shadow] on_loaded dropped (fail-closed)")
        return None  # 绝不 yield / 绝不 set_result

    @filter.on_plugin_unloaded()
    async def _on_unloaded(self, metadata):
        try:
            rec = _sanitize(
                "synthetic/lifecycle:on_plugin_unloaded",
                source="astrbot_internal_probe",
                probe_id="nana-shadow-r01",
                plugin_name=getattr(metadata, "name", None),
            )
            _emit(rec)
        except Exception:
            logger.warning("[nana_shadow] on_unloaded dropped (fail-closed)")
        return None
```

> 注：装饰器名以真实 `register/star_handler.py` 中的 `register_on_plugin_loaded` / `register_on_plugin_unloaded` 为准；`filter.on_plugin_loaded` 的对外别名需在加载前用真实 `astrbot.api` 复核（**复核未完成前不得安装**）。

## 3. Binding Proof 清单（P7，安装后须逐条取证）

1. observer 被真实 runtime 注册（`star_registry` 出现该 star）
2. `star_handlers_registry.get_handlers_by_module_name(...)` 命中 callback
3. 生命周期事件经 `star_manager.py` 真实派发
4. callback 实收事件（evidence 文件出现记录）
5. `event id`/`timestamp`/`source` 对账
6. duplicate probe 不产生重复 Observation
7. observer 卸载后 registry 不再含 callback
8. 卸载后同 probe 不能再进 Shadow
9. production Action=0 / Iris write=0 / external message=0

## 4. Restart-before/after Checklist（仅当姐姐显式授权重启时）

**Before**：记录 `data_v4.db` sha256、`plugins.json` sha256、`md5sum` 全插件清单、`git status`（dev 副本）；备份 `cmd_config.json`。
**Then**：`ASTRBOT_RELOAD=1` 仅对本次启动生效（不做持久化改动）。
**After**：核对 sha256 未变、`existing production files modified=0`、observer 证据落盘、`AstrBot health=PASS`。

## 5. Rollback 包

- 卸载：删除整个 `/AstrBot/data/plugins/astrbot_plugin_nana_shadow_observer/` 目录。
- 删除 evidence：`bridge/receipts/nana_shadow_evidence.jsonl`（可留档，不含正文）。
- Shadow DB / evidence **不得删**（P12）。

## 6. 下一步显式授权指令（唯一选择）

姐姐二选一，奈奈才动：

1. **授权重启接入**：姐姐说“**授权重启**”，奈奈按 §4 走（会短暂掉线）。
2. **走 Dashboard 手动 reload**：姐姐在控制台手动点一次插件 reload（奈奈不读 secret），奈奈随后只做只读取证。

在姐姐明确授权前，observer **不安装、不加载、probe 不运行**。
