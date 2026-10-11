# -*- coding: utf-8 -*-
"""Nana Shadow Observer — 临时只读观察器（DEV COPY，**未安装**）。

⚠️ 本文件位于仓库 `src/plugins/` 开发副本中。
   它 **不在** `/AstrBot/data/plugins/`，未被 AstrBot 加载，也未注册任何 hook。

硬性边界（任一条被破坏即视为实现失败）：
  no message plaintext        —— 只处理生命周期 metadata，不接触 AstrMessageEvent
  no attachment/profile/history/memory plaintext
  no reply                    —— 不返回 MessageEventResult，不 set_result
  no yield response           —— handler 是纯 coroutine，返回 None
  no event mutation           —— 手头没有 message event，无从修改
  no prompt mutation
  no Iris write
  no model / no network / no tool
  no production Action/Grant/Budget
  fail-closed                 —— 任何异常吞掉，绝不外抛到 AstrBot 主链

注册方式（真实 API，已源码核实）：
  astrbot/api/event/filter/__init__.py:30-31
    register_on_plugin_loaded / register_on_plugin_unloaded
  派发方：PluginManager（star_manager.py:1421 / 2044）直接遍历
  star_handlers_registry.get_handlers_by_event_type(...) 并 await。
  → 这是 **plugin manager 直调 registry**，不是 EventBus 消息派发器（见审计文档）。
"""
from __future__ import annotations

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


@_register(
    "astrbot_plugin_nana_shadow_observer",
    "nana-core",
    "只读 fail-closed 临时观察器（开发副本）",
    "0.0.1",
)
class NanaShadowObserver(Star):  # type: ignore[misc,valid-type]
    """空壳 Star：不注册任何消息 handler、不持有任何资源、terminate() 无副作用。"""

    def __init__(self, context=None, config=None):
        try:
            super().__init__(context, config)  # type: ignore[misc]
        except Exception:
            pass

    async def terminate(self):  # noqa: D102 - 卸载钩子，必须无副作用
        return None
