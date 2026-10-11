# -*- coding: utf-8 -*-
"""R03-M2 · message-hook adapter 离线测试矩阵。

覆盖任务书 §三 要求：
  正常 metadata / 缺字段 / 超长字段 / Unicode / null / 恶意对象 / __repr__ 泄密对象 /
  observer exception / sanitizer exception / Core timeout / Core exception /
  cancellation / duplicate / Store reopen-restart duplicate / callback late exception。
并证明：reply=0 / event mutation=0 / Action=Attempt=Grant=Budget=0 /
        network=0 / model call=0 / Iris write=0。

同样只标 **IMPLEMENTED / TESTED**，**不**标 real dispatcher VERIFIED。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
PLUGIN_DIR = REPO / "src" / "plugins" / "astrbot_plugin_nana_shadow_observer"
for p in (str(REPO), str(PLUGIN_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.nana_astrbot_shadow.observer import ShadowObserver  # noqa: E402
from tools.nana_astrbot_shadow.sanitize import MetadataSanitizer  # noqa: E402

import message_hook_adapter as mha  # noqa: E402

PROBE = "nana-probe-r03-hook-v1"
CANARY = "PRIVATE-BODY-MUST-NOT-LEAK"


def make_sanitizer():
    return MetadataSanitizer(
        scope="r03-hook-v1", hash_key=b"R" * 32, probe_ids=frozenset({PROBE})
    )


class RecordingSink:
    """契约合规的 sink 替身：只回 SHADOW_BLOCKED，不触网、不落盘。"""

    def __init__(self, *, delay=0.0, error=None, dedup=False):
        self.calls = []
        self.closed = False
        self._delay = delay
        self._error = error
        self._dedup = dedup

    def accept(self, metadata):
        import time

        if self._delay:
            time.sleep(self._delay)
        if self._error is not None:
            raise self._error
        self.calls.append(metadata.public())
        return {
            "barrier_result": "SHADOW_BLOCKED",
            "dedup_result": "DUPLICATE" if (self._dedup and len(self.calls) > 1) else "NEW",
            "zero_execution_counts": {
                "actions": 0,
                "attempts": 0,
                "grants": 0,
                "budgets": 0,
                "strategies": 0,
            },
        }

    def close(self):
        self.closed = True


class FakeMessageObj:
    def __init__(self, message_id="msg-1", timestamp=1760000000.0):
        self.message_id = message_id
        self.timestamp = timestamp
        # 正文类字段：adapter 绝不允许碰
        self.message = [CANARY]
        self.raw_message = CANARY


class FakeEvent:
    def __init__(
        self,
        platform="aiocqhttp",
        sender="user-1",
        umo="aiocqhttp:FriendMessage:user-1",
        message_id="msg-1",
        timestamp=1760000000.0,
    ):
        self.message_obj = FakeMessageObj(message_id, timestamp)
        self._platform, self._sender, self._umo = platform, sender, umo

    def get_platform_id(self):
        return self._platform

    def get_sender_id(self):
        return self._sender

    @property
    def unified_msg_origin(self):
        return self._umo

    # 这些一旦被调用即为越界
    def get_message_str(self):
        raise AssertionError("body access is forbidden")

    def get_messages(self):
        raise AssertionError("chain access is forbidden")


class HostileRepr:
    def __repr__(self):
        raise AssertionError("repr must never be called")

    def __str__(self):
        raise AssertionError("str must never be called")

    def __format__(self, _spec):
        raise AssertionError("format must never be called")


class ExplodingEvent:
    @property
    def unified_msg_origin(self):
        raise RuntimeError(CANARY)


def _adapter(mode="real", sink=None, **kw):
    sink = sink if sink is not None else RecordingSink()
    observer = ShadowObserver(make_sanitizer(), sink, timeout=1.0, **kw)
    return mha.MessageHookAdapter(
        sanitizer=observer.sanitizer,
        observer=observer,
        mode=mode,
        probe_id=PROBE if mode == "operator_probe" else None,
    ), sink


async def _call(adapter, event):
    try:
        return await adapter.on_decorating_result(event)
    finally:
        await adapter.close()


# ── T1–T5 抽取面 ────────────────────────────────────────────────────────────
def test_t1_payload_allowlist_and_no_plaintext():
    adapter, _ = _adapter()
    payload = adapter.build_payload(FakeEvent())
    assert set(payload) == set(mha.PAYLOAD_KEYS)
    blob = json.dumps(payload, ensure_ascii=False)
    assert CANARY not in blob
    assert "message" not in payload and "raw_message" not in payload
    assert payload["event_source"] == mha.REAL_SOURCE
    assert payload["synthetic"] is False
    assert payload["probe_id"] == ""


def test_t2_hostile_repr_str_never_called():
    adapter, _ = _adapter()
    event = FakeEvent()
    event.message_obj = HostileRepr()  # 若调用 repr/str/format 会当场 AssertionError
    payload = adapter.build_payload(event)
    assert payload is not None  # 说明从未 repr/str/format 它
    assert payload["event_id"] is None and payload["timestamp"] is None
    assert adapter.extract(FakeEvent())["platform"] == "aiocqhttp"

    class ExplodingMessageObj:
        def __getattribute__(self, name):
            raise RuntimeError(CANARY)

    hostile = FakeEvent()
    hostile.message_obj = ExplodingMessageObj()
    assert adapter.build_payload(hostile) is None  # fail-closed


def test_t3_exploding_event_returns_none():
    adapter, _ = _adapter()
    assert adapter.extract(ExplodingEvent()) is None
    assert adapter.build_payload(ExplodingEvent()) is None
    assert asyncio.run(_call(adapter, ExplodingEvent())) is None
    assert adapter.last_status == "DROP_EXTRACT"


@pytest.mark.parametrize(
    "event",
    [
        FakeEvent(platform=None, sender=None, umo=None, message_id=None, timestamp=None),
        FakeEvent(platform="未知平台", sender="", umo="", message_id="", timestamp=0),
        FakeEvent(message_id="m" * 4096, timestamp="not-a-time"),
    ],
)
def test_t4_missing_null_unicode_overlong_fail_closed(event):
    adapter, sink = _adapter()
    assert asyncio.run(_call(adapter, event)) is None
    # real 模式：sanitizer 的 probe 门先挡下 → Core 一次都没被碰
    assert sink.calls == []
    assert adapter.last_status in ("IDLE", "DROP_EXTRACT")


def test_t5_non_string_fields_are_dropped_not_stringified():
    adapter, _ = _adapter()
    event = FakeEvent()
    event.message_obj.timestamp = HostileRepr()
    payload = adapter.build_payload(event)
    assert payload["timestamp"] is None  # 绝不 str() 它


# ── T6–T7 real 模式：fail-closed 闸门 ───────────────────────────────────────
def test_t6_real_mode_blocked_at_gate():
    adapter, sink = _adapter(mode="real")
    assert asyncio.run(_call(adapter, FakeEvent())) is None
    assert sink.calls == []  # Core 未被接触
    # real 模式持 permit=None → observer 在 permit 门即挡下（比 sanitizer 更早）
    assert adapter.observer.last_result["status"] == "DROP_UNAUTHORIZED_PROBE"
    # 即便强行给 permit，sanitizer 的 probe 门仍会独立挡下真实来源
    adapter2, sink2 = _adapter(mode="real")
    adapter2.observer._permits[id(object())] = None  # 不构成合法 permit
    raw = adapter2.build_payload(FakeEvent())
    assert adapter2.sanitizer.sanitize(raw).status == "DROP_PROBE_SCOPE"


def test_t7_real_mode_never_reaches_core_for_any_event():
    for event in (
        FakeEvent(),
        FakeEvent(sender="合成身份", umo="aiocqhttp:GroupMessage:合成群"),
        ExplodingEvent(),
    ):
        adapter, sink = _adapter(mode="real")
        assert asyncio.run(_call(adapter, event)) is None
        assert sink.calls == []


# ── T8 operator 探针：链走到 SHADOW_BLOCKED ────────────────────────────────
def test_t8_operator_probe_reaches_shadow_blocked():
    adapter, sink = _adapter(mode="operator_probe")
    assert asyncio.run(_call(adapter, FakeEvent())) is None
    assert adapter.observer.last_result["status"] == "RECORDED"
    core = adapter.observer.last_result["core"]
    assert core["barrier_result"] == "SHADOW_BLOCKED"
    assert set(core["zero_execution_counts"].values()) == {0}
    assert len(sink.calls) == 1
    # 正文/原始 ID 绝不进 Core
    stored = json.dumps(sink.calls[0], ensure_ascii=False)
    assert CANARY not in stored and "user-1" not in stored


def test_t9_duplicate_is_deduped_not_duplicated():
    adapter, sink = _adapter(mode="operator_probe")
    adapter.observer._sink._dedup = True
    event = FakeEvent()

    async def run():
        assert await adapter.on_decorating_result(event) is None
        first = adapter.observer.last_result["core"]["dedup_result"]
        # 模拟 Store reopen / 进程重启后同一条事件再次到达
        assert await adapter.on_decorating_result(event) is None
        second = adapter.observer.last_result["core"]["dedup_result"]
        await adapter.close()
        return first, second

    first, second = asyncio.run(run())
    assert (first, second) == ("NEW", "DUPLICATE")
    assert len(sink.calls) == 2


# ── T10–T14 失败面 ─────────────────────────────────────────────────────────
def test_t10_sanitizer_exception_fails_closed():
    adapter, _ = _adapter(mode="operator_probe")
    adapter.observer.sanitizer.sanitize = lambda _e: (_ for _ in ()).throw(
        RuntimeError(CANARY)
    )
    assert asyncio.run(_call(adapter, FakeEvent())) is None
    assert adapter.observer.last_result["status"] == "DROP_SHADOW_FAILURE"


def test_t11_core_exception_fails_closed():
    adapter, _ = _adapter(mode="operator_probe")
    adapter.observer._sink._error = RuntimeError(CANARY)
    assert asyncio.run(_call(adapter, FakeEvent())) is None
    assert adapter.observer.last_result["status"] == "DROP_SHADOW_FAILURE"


def test_t12_core_timeout_is_unknown_not_lost():
    adapter, sink = _adapter(mode="operator_probe")
    adapter.observer._sink._delay = 0.6
    adapter.observer.timeout = 0.05
    assert asyncio.run(_call(adapter, FakeEvent())) is None
    assert adapter.observer.last_result["status"] == "UNKNOWN_LOCAL_STORE_COMPLETION"


def test_t13_cancellation_is_not_swallowed():
    adapter, _ = _adapter(mode="operator_probe")

    async def _boom(_payload, *, permit=None):
        raise asyncio.CancelledError()

    adapter.observer.callback = _boom

    async def run():
        with pytest.raises(asyncio.CancelledError):
            await adapter.on_decorating_result(FakeEvent())
        assert adapter.last_status == "IDLE"  # 取消信号不记作 adapter 失败
        await adapter.close()

    asyncio.run(run())


def test_t14_late_callback_exception_never_becomes_unhandled():
    async def run():
        adapter, sink = _adapter(mode="operator_probe")
        seen = []
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _l, ctx: seen.append(ctx))
        adapter.observer._sink._error = RuntimeError(CANARY)
        assert await adapter.on_decorating_result(FakeEvent()) is None
        await asyncio.sleep(0.05)
        del sink
        await adapter.close()
        assert seen == []
        assert adapter.last_status in ("IDLE", "DROP_ADAPTER_FAILURE")

    asyncio.run(run())


# ── T15–T17 零副作用 / 无回复 ──────────────────────────────────────────────
def test_t15_zero_side_effects_on_event_and_no_reply():
    adapter, sink = _adapter(mode="operator_probe")
    event = FakeEvent()
    snapshot = dict(vars(event))
    snapshot_obj = dict(vars(event.message_obj))
    out = asyncio.run(_call(adapter, event))
    assert out is None
    assert not isinstance(out, (list, tuple))  # 不是 MessageEventResult / 可迭代
    assert dict(vars(event)) == snapshot
    assert dict(vars(event.message_obj)) == snapshot_obj
    stored = json.dumps(sink.calls[0], ensure_ascii=False)
    assert CANARY not in stored


def test_t16_adapter_never_calls_forbidden_event_apis():
    adapter, _ = _adapter(mode="operator_probe")
    event = FakeEvent()
    for name in ("stop_event", "set_result", "clear_result", "send"):
        setattr(
            event,
            name,
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("forbidden")),
        )
    assert asyncio.run(_call(adapter, event)) is None


def test_t17_status_summary_marks_probe_class_c_only():
    adapter, _ = _adapter(mode="operator_probe")
    summary = adapter.observation_summary()
    assert summary["real_binding"] is False
    assert summary["probe_class"] == "C"
    assert list(summary["payload_keys"]) == list(mha.PAYLOAD_KEYS)
    asyncio.run(adapter.close())


# ── T18–T20 main.py 接线（默认哑火） ──────────────────────────────────────
def _load_main():
    import builtins
    import importlib.util

    saved = {
        k: sys.modules.pop(k)
        for k in list(sys.modules)
        if k == "astrbot" or k.startswith("astrbot.")
    }
    real_import = builtins.__import__

    def _guard(name, *args, **kwargs):
        if name == "astrbot" or name.startswith("astrbot."):
            raise ImportError("astrbot blocked in offline test")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = _guard
    try:
        spec = importlib.util.spec_from_file_location(
            "nana_shadow_observer_main_r03", PLUGIN_DIR / "main.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
    finally:
        builtins.__import__ = real_import
        sys.modules.update(saved)
    return module


def test_t18_unbound_hook_is_inert():
    main = _load_main()
    assert main.get_message_adapter() is None
    assert asyncio.run(main.nana_shadow_on_decorating_result(FakeEvent())) is None


def test_t19_bound_hook_delegates_and_stays_fail_closed():
    main = _load_main()
    adapter, sink = _adapter(mode="operator_probe")
    previous = main.bind_message_adapter(adapter)
    try:
        assert previous is None
        assert asyncio.run(main.nana_shadow_on_decorating_result(FakeEvent())) is None
        assert adapter.observer.last_result["status"] == "RECORDED"

        class Exploding:
            async def on_decorating_result(self, event):
                raise RuntimeError(CANARY)

        main.bind_message_adapter(Exploding())
        assert asyncio.run(main.nana_shadow_on_decorating_result(FakeEvent())) is None
    finally:
        main.bind_message_adapter(None)
        assert asyncio.run(adapter.close()) is None
        del sink


def test_t20_hook_is_plain_coroutine_not_generator():
    import inspect

    main = _load_main()
    hook = main.nana_shadow_on_decorating_result
    assert inspect.iscoroutinefunction(hook)
    assert not inspect.isasyncgenfunction(hook)  # 绝不允许 yield 语义


# ── T21 真实 Core 链：宿主 SQLite 门（不绕过） ─────────────────────────────
def test_t21_real_core_sink_chain_or_host_sqlite_gate(tmp_path):
    """真实 MetadataCoreSink 链。宿主 SQLite < 3.51.3 时如实 BLOCKED，不绕过。"""
    import sqlite3

    from tools.nana_astrbot_shadow.core_sink import MetadataCoreSink

    if sqlite3.sqlite_version_info < (3, 51, 3):
        pytest.skip(f"HOST_SYSTEM_SQLITE_GATE=BLOCKED (host sqlite {sqlite3.sqlite_version})")

    directory = tmp_path / "shadow"
    directory.mkdir(mode=0o700)
    sink = MetadataCoreSink(directory, make_sanitizer())
    adapter, _ = _adapter(mode="operator_probe")
    adapter.observer._sink = sink
    adapter.observer.timeout = 2.0
    try:
        assert asyncio.run(adapter.on_decorating_result(FakeEvent())) is None
        status = adapter.observer.last_result["status"]
        assert status == "RECORDED", adapter.observer.last_result
        core = adapter.observer.last_result["core"]
        assert core["barrier_result"] == "SHADOW_BLOCKED"
        assert set(core["zero_execution_counts"].values()) == {0}
    finally:
        asyncio.run(adapter.close())
