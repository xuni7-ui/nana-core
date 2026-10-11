# Nana Shadow Observer — 开发副本 · 测试 · 打包 · 安装 Runbook（M2 + P14·R02）

- 时间：2026-10-11 (CST) · 执行者：奈奈（宿主侧执行者）
- 基线分支：`dev/nana-core-v1-astrbot-shadow-bind` @ `c3ada9b09faa8a2683f98d5c8bafec24779cfd71`
- **当前状态：开发副本 only —— 未安装 / 未加载 / 未注册 / probe 未跑**

---

## 1. 交付物清单

| # | 产物 | 路径 |
|---|---|---|
| 1 | 插件源码（开发副本） | `src/plugins/astrbot_plugin_nana_shadow_observer/{main.py,metadata.yaml,nana_observe_core.py}` |
| 2 | 离线测试 | `tests/nana_shadow/test_observer_offline.py`（9 例） |
| 3 | 指纹清单 | `manifests/nana_shadow_observer_fingerprints.json` |
| 4 | 确定性打包 | `artifacts/nana-shadow-observer/nana_shadow_observer-0.0.1-dev.tar.gz` |
| 5 | 本文（安装/验证/回滚 runbook） | `docs/nana_shadow_observer_dev_20261011.md` |

### 指纹（逐文件 sha256）

| 文件 | sha256 |
|---|---|
| `src/.../main.py` | `07386a32f0140372b0bc4a458df6853d7023c602bbd004236e51aeba79930a93` |
| `src/.../metadata.yaml` | `954d011f8e0781f0655e043e97806af078278796c10b79eb1c4a0a0ed8cf14a5` |
| `src/.../nana_observe_core.py` | `06697836c4277e5947876b766c7c99fe0b22938b73ad4d53a1e648079d5e9734` |
| `artifacts/…/nana_shadow_observer-0.0.1-dev.tar.gz` | `27fc75d98388d0890c4b7eeca67671b4b475f885c85938a958e0b1e9245e66fa` |

打包确定性已复算验证（`deterministic: true`）：GNU tar + 排序条目 + `mtime=0` + `uid/gid=0` + `gzip mtime=0`。

---

## 2. 设计：为什么这样写

**注册面**（真实 API，已源码核实）：

```python
from astrbot.api.event import filter      # astrbot/api/event/filter/__init__.py:30-31
@filter.on_plugin_loaded()                # → register_on_plugin_loaded
@filter.on_plugin_unloaded()              # → register_on_plugin_unloaded
```

**硬性边界（逐条落地方式）**：

| 要求 | 落地 |
|---|---|
| no message plaintext | handler 签名只收 `metadata`（`StarMetadata`），**结构上拿不到 `AstrMessageEvent`** |
| no attachment/profile/history/memory plaintext | 记录字段来自**白名单**；主体字符串一律 scoped-hash（`scoped_hash()`） |
| no reply | handler 是纯 coroutine，**返回 `None`**（无 `MessageEventResult`/无 `yield`） |
| no yield response | 非 async generator |
| no event mutation | 手上无 message event |
| no prompt mutation | 不接触 `OnLLMRequestEvent` |
| no Iris write | 不 import 任何 Iris 模块、不开 Iris 路径 |
| no model / no network / no tool | 不 import provider / requests / socket；不注册 `llm_tool` |
| no production Action/Grant/Budget | 证据只写自有 JSONL，路径默认 `/tmp/nana_shadow/…` |
| fail-closed | `_observe()` 全程 `try/except BaseException`；`emit_record()` 失败返回 `False` 不外抛 |

**记录 schema**（`nana.shadow.observer/1`）：

```json
{"binding_proof": true, "dispatcher_class": "plugin_manager_direct_registry_loop",
 "kind": "lifecycle.on_plugin_loaded", "no_plaintext": true,
 "observed_at_ms": 0, "schema": "nana.shadow.observer/1", "source": "astrbot_internal_lifecycle",
 "subject": {"name_hash": "<sha256[:16]>", "name_len": 33, "version": "0.0.1", "reserved": false},
 "synthetic": true}
```

---

## 3. 离线测试结果

命令：
```bash
cd /root/nana_dev/nana-core && python3 -m pytest tests/nana_shadow -q
```
结果：**`9 passed`**（Python 3.12.14 / pytest 9.1.1）

| 用例 | 断言 |
|---|---|
| T1 | 记录不含正文类字段（`SECRET…` 不出现） |
| T2 | scoped hash 稳定、长度 16、不同 scope 不同、不可逆 |
| T3 | 顶层键 ⊆ 白名单；`kind/synthetic/binding_proof/no_plaintext` 正确 |
| T4 | 不可写路径 → `emit_record` 返回 `False` 且不抛异常 |
| T5 | handler 返回 `None`（无 reply / 无 yield） |
| T6 | metadata 属性炸异常时 handler 仍返回 `None` |
| T7 | 落盘为合法 JSONL 且通过 plaintext 守卫 |
| T8 | 默认证据路径在临时目录、**不在 `/AstrBot` 下** |
| T9 | 生产插件目录**不存在**该插件（防误装） |

> 已知非阻塞告警：`register_star` 装饰器在 4.28.0 已 `DeprecationWarning`
> （`astrbot/core/star/register/star.py`：v3.5.19 起继承 `Star` 的子类会被自动识别）。
> 保留装饰器只为兼容旧版；不影响加载。

---

## 4. 全量回归的**既有**环境门槛（非本轮引入）

```bash
python3 -m pytest -q     # → 65 failed, 171 passed, 1 skipped, 82 errors
```
**全部失败/错误**均为 `nana_core.contracts.CoreError: SQLITE_VERSION_UNSUPPORTED`
（`src/nana_core/storage/sqlite_store.py:78`：要求 `sqlite3.sqlite_version_info >= (3,51,3)`）。

宿主实测解释器 **无一达标**：

| 解释器 | Python | SQLite |
|---|---|---|
| `/usr/local/bin/python3.12` | 3.12.14 | **3.46.1** ❌ |
| `/usr/bin/python3.13` | 3.13.5 | **3.46.1** ❌ |
| `/hostroot/usr/bin/python3.12`（宿主） | 3.12.3 | **3.46.1** ❌ |

⇒ nana_core 全量套件必须在**隔离 shadow runtime**（私有静态链接 SQLite 3.51.3）内跑；
这与 R02 之前记录的门槛**完全一致**，**本轮观察器改动不引入任何回归**（观察器 9/9 独立通过，
且全量失败点全部落在 `Store.__init__` 的 SQLite 版本闸门）。

隔离包完整性已核：`artifacts/shadow-bootstrap/nana-shadow-bootstrap-host3123-cd2e8a302a6d.tar.gz`
sha256 = `c793991badd5efeaaa4676730278c2cdf3f2e01ee5ccafd1626edc4819b49c88`
= 与 `manifests/nana_shadow_host_compat_fingerprints.json` 记录值**一致** ✅

---

## 5. 安装路径与动态加载路径（**均未执行**）

| 项 | 值 |
|---|---|
| 目标安装路径 | `/AstrBot/data/plugins/astrbot_plugin_nana_shadow_observer/`（**全新目录，绝不覆盖**） |
| 安装动作 | 解包 `artifacts/nana-shadow-observer/nana_shadow_observer-0.0.1-dev.tar.gz` 到该目录 |
| 动态加载路径（当前唯一免重启） | Dashboard `POST /api/plugin/reload`（需 JWT）→ `PluginService.reload_plugin()`（`dashboard/services/plugin_service.py:154`）→ `PluginManager.reload(name)`（`star_manager.py:1010`）→ `load()`（`:1068`） |
| ⚠️ 注意 | `reload(name)` **只对已注册插件生效**；**全新目录**需先让 `load()` 扫盘（全量 load 或重启）。见 M3 §2-C1。 |
| 备选（零点击） | watcher 自动加载 —— **需 `ASTRBOT_RELOAD=1`，本轮不启用** |
| 明确不做的 | ❌ 复制到生产插件目录 ❌ 调 Dashboard reload ❌ 重启 AstrBot |

---

## 6. Runbook（**留给姐姐执行**，奈奈现在一步不做）

### 6.0 最小动作（下一次只需要姐姐做这一件事）

> **在你已经登录的 AstrBot Dashboard 里，把插件目录放好之后，手动点一次「重载插件 / reload」。**
> 全程奈奈不读 JWT、不碰 secret、不重启，只在事后做**只读取证**。

前置（姐姐或授权后由奈奈执行）：
1. 解包 → `/AstrBot/data/plugins/astrbot_plugin_nana_shadow_observer/`
2. 校验 `metadata.yaml` 的 `name` 与目录名一致

### 6.1 Pre-load Checklist（加载前）

- [ ] 解包目录 sha256 与 §1 指纹一致
- [ ] `metadata.yaml.name == 目录名 == astrbot_plugin_nana_shadow_observer`
- [ ] 该目录在安装前**不存在**（防覆盖既有插件）
- [ ] 证据目录 `/tmp/nana_shadow/` 可写（或已设 `NANA_SHADOW_EVIDENCE`）
- [ ] 记录加载前基线：`git status`、插件目录清单 md5、`data_v4.db` sha256
- [ ] 确认**无** `ASTRBOT_RELOAD` 持久化改动

### 6.2 Load

在 Dashboard 点 reload（或按 M3 §2 通道 2）。**不重启。**

### 6.3 Post-load Verification Checklist（加载后，全部只读）

- [ ] `star_registry` 出现 `astrbot_plugin_nana_shadow_observer`
- [ ] `star_map` 出现对应 `module_path = data.plugins.astrbot_plugin_nana_shadow_observer.main`
- [ ] `star_handlers_registry.get_handlers_by_module_name("data.plugins.astrbot_plugin_nana_shadow_observer.main")`
      返回 **2** 个 handler（`nana_shadow_on_plugin_loaded` / `nana_shadow_on_plugin_unloaded`）
- [ ] 证据文件 `/tmp/nana_shadow/observer_evidence.jsonl` 出现记录，且 `looks_plaintext == False`
- [ ] 记录条数 == 加载期间发生的生命周期事件数（含 observer 自身加载）
- [ ] `AstrBot health = PASS`（无新 error 日志、无异常回显）
- [ ] `external message sent = 0` / `production Action = 0` / `Iris write = 0`

> ⚠️ **证据等级声明**：以上证明的是 **「AstrBot runtime → real registry → observer callback」**，即
> **registry binding**。**不构成**真实消息 dispatcher traversal。见 M3。

### 6.4 Unregister Checklist（卸载）

- [ ] 备份证据 JSONL
- [ ] 通过 Dashboard 卸载/禁用，或删除插件目录后 reload
- [ ] 确认 `star_registry` / `star_map` / `star_handlers_registry` 均不再含该模块
- [ ] **Registry-removal proof method（精确）**：
  ```python
  from astrbot.core.star.star_handler import star_handlers_registry as r
  mod = "data.plugins.astrbot_plugin_nana_shadow_observer.main"
  assert r.get_handlers_by_module_name(mod) == []          # 调用链 star_manager.py:1894 → star_handler.py:205
  assert not [k for k in r.star_handlers_map if k.startswith(mod)]  # star_manager.py:1907-1912
  ```
- [ ] 卸载后再点一次 reload，证据条数**不再增长**

### 6.5 Rollback Package

| 项 | 内容 |
|---|---|
| 回滚动作 | `rm -rf /AstrBot/data/plugins/astrbot_plugin_nana_shadow_observer/` |
| 证据处理 | `/tmp/nana_shadow/observer_evidence.jsonl` 可留档（零正文），亦可删 |
| 生产影响面 | 仅新增一个插件目录；**不触碰** AstrBot/核心/其它插件/Iris |
| 回滚验证 | 6.4 的三个断言全部成立 |

### 6.6 Zero-drift Checklist（每轮收口必查）

| 项 | 目标 |
|---|---|
| `existing production files modified` | 0 |
| `existing Iris files modified` | 0 |
| `existing config modified` | 0 |
| `AstrBot restarted` | false |
| `external messages` | 0 |
| `secret reads` | 0 |
| `private plaintext reads` | 0 |
| `new production plugin dir` | 0（安装前） |

---

## 7. 当前状态（收口）

| 状态键 | 值 |
|---|---|
| `observer implemented (dev copy)` | **YES** |
| `observer offline tests` | **9/9 PASS** |
| `observer packaged + fingerprinted` | **YES** |
| `observer installed` | **NO** |
| `observer loaded` | **NO** |
| `observer registered` | **NO** |
| `host_binding` | **UNVERIFIED** |
