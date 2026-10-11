# -*- coding: utf-8 -*-
"""Nana Shadow Observer — 离线测试（不加载 AstrBot，不触网，不写生产路径）。

覆盖：
  T1 零正文：记录中不含正文类字段
  T2 scoped hash 稳定且不可逆（不出现原文）
  T3 白名单：非白名单字段被剔除
  T4 fail-closed：坏路径写入返回 False 且不抛异常
  T5 handler 返回 None（无 reply / 无 yield）
  T6 handler 在 metadata 畸形时仍不抛异常
  T7 落盘内容为合法 JSONL 且可解析
  T8 证据路径默认落在临时目录（不在 /AstrBot 下）
"""
from __future__ import annotations

import builtins
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
PLUGIN_DIR = REPO / "src" / "plugins" / "astrbot_plugin_nana_shadow_observer"

if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import nana_observe_core as core  # noqa: E402


class _FakeMeta:
    def __init__(self, name="astrbot_plugin_demo", version="1.2.3", reserved=False):
        self.name = name
        self.version = version
        self.reserved = reserved
        # 故意塞入正文类属性，验证不会被带出
        self.content = "SECRET-PLAINTEXT-SHOULD-NOT-LEAK"
        self.message_text = "SECRET-MSG"
        self.user_profile = {"name": "SECRET-PROFILE"}


def _load_main():
    """加载 main.py，并**强制**走无 AstrBot 的降级分支。

    本仓库的离线测试**不允许** import 真实 astrbot：那会在仓库 cwd 生成
    AstrBot 运行时目录（`data/`），污染工作区。故此处屏蔽 astrbot 导入。
    """
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
            "nana_shadow_observer_main", PLUGIN_DIR / "main.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
    finally:
        builtins.__import__ = real_import
        sys.modules.update(saved)
    return module


def test_t1_no_plaintext_fields():
    rec = core.build_lifecycle_record("lifecycle.on_plugin_loaded", _FakeMeta())
    assert core.looks_plaintext(rec) is False
    blob = json.dumps(rec, ensure_ascii=False)
    assert "SECRET" not in blob
    assert "content" not in rec
    assert "text" not in rec


def test_t2_scoped_hash_stable_and_irreversible():
    h1 = core.scoped_hash("astrbot_plugin_demo")
    h2 = core.scoped_hash("astrbot_plugin_demo")
    h3 = core.scoped_hash("astrbot_plugin_demo", scope="other")
    assert h1 == h2 and len(h1) == 16
    assert h1 != h3
    assert "astrbot_plugin_demo" not in h1
    assert core.scoped_hash(None) is None


def test_t3_whitelist_drops_unknown_fields():
    rec = core.build_lifecycle_record("lifecycle.on_plugin_loaded", _FakeMeta())
    assert set(rec).issubset(core.ALLOWED_OUTPUT_FIELDS)
    assert rec["no_plaintext"] is True
    assert rec["synthetic"] is True
    assert rec["binding_proof"] is True
    assert rec["kind"] == "lifecycle.on_plugin_loaded"


def test_t4_emit_fail_closed_on_bad_path():
    rec = core.build_lifecycle_record("lifecycle.on_plugin_loaded", _FakeMeta())
    assert core.emit_record(rec, path="/proc/definitely/not/writable/x.jsonl") is False


def test_t5_handler_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv(core.DEFAULT_EVIDENCE_ENV, str(tmp_path / "ev.jsonl"))
    main = _load_main()
    import asyncio

    out = asyncio.run(main.nana_shadow_on_plugin_loaded(_FakeMeta()))
    assert out is None


def test_t6_handler_survives_malformed_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv(core.DEFAULT_EVIDENCE_ENV, str(tmp_path / "ev.jsonl"))
    main = _load_main()
    import asyncio

    class _Exploding:
        @property
        def name(self):
            raise RuntimeError("boom")

    out = asyncio.run(main.nana_shadow_on_plugin_loaded(_Exploding()))
    assert out is None


def test_t7_evidence_is_valid_jsonl(tmp_path):
    path = tmp_path / "ev.jsonl"
    for kind in ("lifecycle.on_plugin_loaded", "lifecycle.on_plugin_unloaded"):
        rec = core.build_lifecycle_record(kind, _FakeMeta())
        assert core.emit_record(rec, path=str(path)) is True
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert parsed["schema"] == core.SCHEMA
        assert core.looks_plaintext(parsed) is False


def test_t8_default_evidence_path_is_not_production():
    monkeypatch_env = os.environ.pop(core.DEFAULT_EVIDENCE_ENV, None)
    try:
        assert core.resolve_evidence_path() == core.DEFAULT_EVIDENCE_PATH
        assert not core.resolve_evidence_path().startswith("/AstrBot")
    finally:
        if monkeypatch_env is not None:
            os.environ[core.DEFAULT_EVIDENCE_ENV] = monkeypatch_env


def test_t9_no_astrbot_scoped_handlers_registration_in_repo_copy():
    """开发副本不得出现在生产插件目录。"""
    assert not Path("/AstrBot/data/plugins/astrbot_plugin_nana_shadow_observer").exists()
