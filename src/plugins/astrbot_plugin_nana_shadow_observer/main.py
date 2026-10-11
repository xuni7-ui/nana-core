# -*- coding: utf-8 -*-
"""Nana Shadow Observer — 临时只读观察器（DEV COPY，**未安装**）。

⚠️ 本文件位于仓库 `src/plugins/` 开发副本中。
   它 **不在** `/AstrBot/data/plugins/`，未被 AstrBot 加载，也未注册任何**生效**的 hook
   （hook 函数已定义，但 message adapter 默认未绑定 = 完全哑火）。

硬性边界（任一条被破坏即视为实现失败）：
  no message plaintext        —— 生命周期只处理 metadata；message hook 只抽出 9 键标量 dict
  no attachment/profile/history/memory plaintext
  no reply                    —— 不返回 MessageEventResult，不 set_result
  no yield response           —— handler 是纯 coroutine，返回 None
  no event mutation           —— 不调用 stop_event / 不写 event 字段
  no prompt mutation
  no Iris write
  no model / no network / no tool
  no production Action/Grant/Budget
  fail-closed                 —— 任何异常吞掉，绝不外抛到 AstrBot 主链（取消信号除外）

注册方式（真实 API，已源码核实）：
  生命周期  astrbot/api/event/filter/__init__.py:30-31
           register_on_plugin_loaded / register_on_plugin_unloaded
           派发方：PluginManager（star_manager.py:1421 / 2044）直接遍历
           star_handlers_registry.get_handlers_by_event_type(...) 并 await。
           → **plugin manager 直调 registry**，不是 EventBus 消息派发器（见审计文档）。
  消息管道  filter.on_decorating_result()  →  EventType.OnDecoratingResultEvent
           astrbot/core/pipeline/result_decorate/stage.py:158-189
           → **真实** EventBus.dispatch() → PipelineScheduler 路径内（SAFE）
           详见 docs/nana_shadow_message_observer_audit_20261011.md
"""
from __future__ import annotations

import asyncio
import traceback

try:  # 真实 AstrBot 运行环境
    from astrbot.api import logger as _astrbot_logger
    from astrbot.api.event import filter as _filter
    from astrbot.api.star import Context, Star, register as _register

    ASTRBOT_AVAILABLE = True
except Exception:  # 离线/测试环境：降级为 no-op，保证模块可导入
    ASTRBOT_AVAILABLE = False
    _astrbot_logger = None
    _filter = None
    Context = object  # type: ignore[assignment]
    Star = object  # type: ignore[assignment]

    def _register(*_args, **_kwargs):  # type: ignore[misc]
        def _decorator(cls):
            return cls

        return _decorator

    def _noop_decorator(*_args, **_kwargs):  # type: ignore[misc]
        def _decorator(func):
            return func

        return _decorator

try:
    from .nana_observe_core import build_lifecycle_record, emit_record, looks_plaintext
except ImportError:  # 以文件方式加载时
    from nana_observe_core import (  # type: ignore[no-redef]
        build_lifecycle_record,
        emit_record,
        looks_plaintext,
    )


def _log_warning(message: str) -> None:
    """日志也要 fail-closed：日志本身出问题不能影响主链。"""
    try:
        if _astrbot_logger is not None:
            _astrbot_logger.warning(message)
    except Exception:
        pass


def _observe(kind: str, metadata) -> None:
    """构造并落盘一条观测记录。全程 try/except，绝不外抛。"""
    try:
        record = build_lifecycle_record(kind, metadata)
        if looks_plaintext(record):
            _log_warning("[nana_shadow] record rejected by plaintext guard")
            return
        ok = emit_record(record)
        if not ok:
            _log_warning("[nana_shadow] evidence write failed (dropped, fail-closed)")
    except BaseException:
        # 连 traceback 都再包一层，确保绝不外抛
        try:
            _log_warning("[nana_shadow] observe dropped (fail-closed)")
            del traceback
        except BaseException:
            pass


if ASTRBOT_AVAILABLE:

    @_filter.on_plugin_loaded()
    async def nana_shadow_on_plugin_loaded(metadata):
        """生命周期 hook：任意插件加载完成时触发。只观测，返回 None。"""
        _observe("lifecycle.on_plugin_loaded", metadata)
        return None

    @_filter.on_plugin_unloaded()
    async def nana_shadow_on_plugin_unloaded(metadata):
        """生命周期 hook：任意插件卸载完成时触发。只观测，返回 None。"""
        _observe("lifecycle.on_plugin_unloaded", metadata)
        return None

else:

    async def nana_shadow_on_plugin_loaded(metadata):  # type: ignore[misc]
        _observe("lifecycle.on_plugin_loaded", metadata)
        return None

    async def nana_shadow_on_plugin_unloaded(metadata):  # type: ignore[misc]
        _observe("lifecycle.on_plugin_unloaded", metadata)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# R03-M2：message pipeline 观察点（**惰性**接线，默认完全哑火）
#
# SAFE hook = EventType.OnDecoratingResultEvent
#   调用点 astrbot/core/pipeline/result_decorate/stage.py:158-189
#   遍历唯一入口 EventBus.dispatch() -> PipelineScheduler（stage_order.py:11）
#   返回值被丢弃（:173）→ 返回 None 不改变消息结果
#   异常被局部 except BaseException 吞掉（:181-182）→ 不会触发默认错误回复
#
# 边界：**未绑定 adapter 时本 hook 立即 return None**，不读正文、不写盘、不触网。
#      adapter 只能由操作者显式 `bind_message_adapter()` 注入（本轮不注入）。
# ─────────────────────────────────────────────────────────────────────────────
_MESSAGE_ADAPTER = None


def bind_message_adapter(adapter):
    """显式绑定 message adapter。返回前一个绑定。本轮无人调用。"""
    global _MESSAGE_ADAPTER
    previous = _MESSAGE_ADAPTER
    _MESSAGE_ADAPTER = adapter
    return previous


def get_message_adapter():
    return _MESSAGE_ADAPTER


async def _dispatch_decorating_result(event):
    """最薄转发：恒返回 None，异常绝不外抛（取消信号除外）。"""
    try:
        adapter = _MESSAGE_ADAPTER
        if adapter is None:
            return None
        return await adapter.on_decorating_result(event)
    except asyncio.CancelledError:
        raise  # 不吞取消信号
    except BaseException:
        pass
    return None


if ASTRBOT_AVAILABLE:

    @_filter.on_decorating_result()
    async def nana_shadow_on_decorating_result(event):
        """SAFE result-path 观察点。只转发，返回 None。"""
        return await _dispatch_decorating_result(event)

else:

    async def nana_shadow_on_decorating_result(event):  # type: ignore[misc]
        return await _dispatch_decorating_result(event)


@_register(
    "astrbot_plugin_nana_shadow_observer",
    "nana-core",
    "只读 fail-closed 临时观察器（开发副本）",
    "0.0.1",
)
class NanaShadowObserver(Star):  # type: ignore[misc,valid-type]
    """Star：生命周期 hook + 一个**默认哑火**的 message hook；terminate() 无副作用。"""

    def __init__(self, context=None, config=None):
        try:
            super().__init__(context, config)  # type: ignore[misc]
        except Exception:
            pass

    async def terminate(self):  # noqa: D102 - 卸载钩子，必须无副作用
        return None
