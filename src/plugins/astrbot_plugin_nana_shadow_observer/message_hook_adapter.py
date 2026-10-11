# -*- coding: utf-8 -*-
"""Nana Shadow · AstrBot 4.28.0 message-hook adapter —— **最薄**一层（DEV COPY，未安装）。

SAFE hook（源码级核实，见 `docs/nana_shadow_message_observer_audit_20261011.md`）：

    EventType.OnDecoratingResultEvent
      enum       astrbot/core/star/star_handler.py:234
      register   astrbot/core/star/register/star_handler.py:730  filter.on_decorating_result()
      call site  astrbot/core/pipeline/result_decorate/stage.py:158-189
      dispatch   EventBus.dispatch() (core/event_bus.py:39)
                 -> PipelineScheduler.execute() (core/pipeline/scheduler.py:82)
                 -> STAGES_ORDER[7] (core/pipeline/stage_order.py:11)

为什么 SAFE（三条，缺一不可）：
  1. `stage.py:173` `await handler.handler(event)` —— **返回值被丢弃**，
     因此本 handler 返回 None 不可能改变消息处理结果；
     与 `context_utils.call_handler()`（会 `event.set_result(ret)`）**语义完全不同**。
  2. `stage.py:181-182` `except BaseException: logger.error(traceback.format_exc())`
     —— handler 抛错被**局部吞掉**，只记日志，不 re-raise，不产生 AstrBot 默认错误回复。
  3. `stage.py:184-189` 只有在 handler 自己 `event.stop_event()` 时才 `return`；
     本 adapter **永不**调用 stop_event。

⚠️ 它是 **result-path** observer：只在「本条消息产生了要发送的结果」时触发。
   **不存在**「每条消息到达即安全观察」的 hook（SAFE early all-message observer = NOT_AVAILABLE）。

硬边界（任一条被破坏即视为实现失败）：
  * AstrMessageEvent 对象**永不**跨入 Core —— 只交出一个 9 键的纯 dict；
  * 只经**白名单取值器**抽取 8 个标量字段，绝不 `str()/repr()/format()` 事件、
    message_obj、message chain、result、attachments、profile、history、prompt；
  * 不改 event、不 `set_result()`、不 `yield`、不 `stop_event()`；
  * 不调模型 / 网络 / tool / Iris，不写 Iris；
  * 永远 `return None`；任何失败 fail-closed；
  * `asyncio.CancelledError` **原样上抛**（不吞取消信号，最小化对主链行为的影响）。

复用（不另造第二套）：
  sanitize.MetadataSanitizer / observer.ShadowObserver / core_sink.MetadataCoreSink。
  本模块只负责「真实 hook → 白名单 metadata」这一段。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

# ── 来源标记 ────────────────────────────────────────────────────────────────
# 真实 AstrBot 事件：与 Codex sanitizer 的 operator_probe 门**刻意不同**。
# 这保证真实流量**不会**被冒充成内部 probe（fail-closed，见 §real ingress）。
REAL_SOURCE = "astrbot_on_decorating_result"
PROBE_SOURCE = "operator_probe"

MODES = ("real", "operator_probe")

# 交给 sanitizer 的键集合（严格固定，多一个都不行）
PAYLOAD_KEYS = (
    "platform",
    "type",
    "event_id",
    "timestamp",
    "conversation_id",
    "sender_id",
    "event_source",
    "synthetic",
    "probe_id",
)


def _only_str(value):
    """只放行**内建 str**。绝不 `str()` / `repr()` / `format()` 任何对象。"""
    return value if type(value) is str else None


def _normalize_timestamp(value):
    """epoch(int/float, 秒或毫秒) 或带时区的 ISO 字符串 → UTC ISO；其余 → None。"""
    try:
        if type(value) in (int, float):
            seconds = value / 1000.0 if abs(value) > 1e11 else float(value)
            return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
        if type(value) is str and 0 < len(value) <= 40:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return None
            return parsed.astimezone(timezone.utc).isoformat()
    except BaseException:
        return None
    return None


class MessageHookAdapter:
    """把 `OnDecoratingResultEvent` 变成「白名单 metadata → Codex 链」的最薄接线。

    mode="real"            → event_source=REAL_SOURCE, synthetic=False
                              （真实流量；由 Codex sanitizer 的 probe 门 fail-closed 挡下，
                                这是**正确**行为，见 README/审计 §real ingress）
    mode="operator_probe"  → 需要 **显式** 本地 permit（`issue_local_permit`），
                              仅用于离线/内部探针，用来证明整条链能走到 SHADOW_BLOCKED。
    """

    def __init__(self, *, sanitizer, observer, mode="real", probe_id=None, logger=None):
        if mode not in MODES:
            raise ValueError("INVALID_ADAPTER_MODE")
        if sanitizer is None or observer is None:
            raise ValueError("SANITIZER_AND_OBSERVER_REQUIRED")
        if mode == "operator_probe" and (type(probe_id) is not str or not probe_id):
            raise ValueError("PROBE_ID_REQUIRED")
        self.sanitizer = sanitizer
        self.observer = observer
        self.mode = mode
        self.probe_id = probe_id
        self._logger = logger
        # 仅 operator_probe 模式持有 permit；real 模式恒为 None。
        self._permit = (
            observer.issue_local_permit(probe_id) if mode == "operator_probe" else None
        )
        self._active = True
        self.last_status = "IDLE"

    # ── 观测面 ──────────────────────────────────────────────────────────────
    def extract(self, event):
        """只经白名单取值器抽取标量。任何异常 → None（fail-closed）。"""
        try:
            message_obj = getattr(event, "message_obj", None)  # 不 repr / 不遍历
            return {
                "platform": _only_str(_safe_call(event, "get_platform_id")),
                "type": _only_str(type(event).__name__),
                "event_id": _only_str(getattr(message_obj, "message_id", None)),
                "timestamp": _normalize_timestamp(
                    getattr(message_obj, "timestamp", None)
                ),
                "conversation_id": _only_str(
                    getattr(event, "unified_msg_origin", None)
                ),
                "sender_id": _only_str(_safe_call(event, "get_sender_id")),
            }
        except BaseException:
            return None

    def build_payload(self, event):
        """抽取 + 打上来源标记。返回严格 9 键 dict；抽取失败返回 None。"""
        raw = self.extract(event)
        if raw is None:
            return None
        if self.mode == "operator_probe":
            raw["event_source"] = PROBE_SOURCE
            raw["synthetic"] = True
            raw["probe_id"] = self.probe_id
        else:
            raw["event_source"] = REAL_SOURCE
            raw["synthetic"] = False
            raw["probe_id"] = ""
        return {key: raw.get(key) for key in PAYLOAD_KEYS}

    # ── hook 本体 ───────────────────────────────────────────────────────────
    async def on_decorating_result(self, event):
        """`OnDecoratingResultEvent` handler。恒返回 None。"""
        try:
            if not self._active:
                return None
            payload = self.build_payload(event)
            if payload is None:
                self._note("DROP_EXTRACT")
                return None
            await self.observer.callback(payload, permit=self._permit)
        except asyncio.CancelledError:
            # 取消信号原样上抛：吞掉会延后 pipeline task 的取消。
            raise
        except BaseException:
            self._note("DROP_ADAPTER_FAILURE")
        return None

    # ── 状态 / 收口 ─────────────────────────────────────────────────────────
    def _note(self, code):
        self.last_status = code
        try:
            if self._logger is not None:
                self._logger(code)  # 只传固定 code，绝不带 event/异常文本
        except BaseException:
            pass

    def observation_summary(self):
        return {
            "mode": self.mode,
            "payload_keys": list(PAYLOAD_KEYS),
            "adapter_status": self.last_status,
            "observer_status": dict(self.observer.last_result),
            "real_binding": False,
            "probe_class": "C",
        }

    def arm(self):
        """显式武装（只对 operator_probe 有意义）。"""
        if self.mode != "operator_probe":
            raise ValueError("REAL_MODE_IS_NOT_ARMABLE")
        if self._permit is None:
            self._permit = self.observer.issue_local_permit(self.probe_id)
        return True

    def disarm(self):
        self._permit = None

    async def close(self):
        self._active = False
        self._permit = None
        await self.observer.close()

    def __repr__(self):  # 永远不泄漏内容
        return f"<MessageHookAdapter mode={self.mode} active={self._active}>"


def _safe_call(obj, name):
    """只调用无参白名单方法；不存在/不可调用 → None。"""
    try:
        func = getattr(obj, name, None)
        return func() if callable(func) else None
    except BaseException:
        return None
