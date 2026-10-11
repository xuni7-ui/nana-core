# -*- coding: utf-8 -*-
"""Nana Shadow Observer — 纯逻辑核心（无 astrbot 依赖，便于离线测试）。

设计目标（硬性边界，任一不满足即 fail-closed）：
  * 无消息正文 / 无附件 / 无画像 / 无历史 / 无记忆正文
  * 无回复 / 不 yield / 不改 event / 不改 prompt
  * 不写 Iris / 不调模型 / 不联网 / 不注册工具
  * 无生产 Action / Grant / Budget
  * 任何异常一律吞掉，绝不外抛到 AstrBot 主链

本模块只做两件事：
  1. build_lifecycle_record() —— 从生命周期 metadata 构造「零正文」观测记录
  2. emit_record()             —— 追加写 JSONL；失败返回 False，从不抛异常

数据最小化原则：任意字符串主体（插件名等）一律 scoped-hash 后再落盘，
记录里只保留 枚举/布尔/长度/哈希/时间戳 这几类字段。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Mapping

SCHEMA = "nana.shadow.observer/1"
HASH_SCOPE = "nana-shadow-observer"

# 唯一允许写入证据的字段（白名单，其余一律丢弃）
ALLOWED_OUTPUT_FIELDS = frozenset(
    {
        "schema",
        "kind",
        "observed_at_ms",
        "source",
        "synthetic",
        "binding_proof",
        "dispatcher_class",
        "no_plaintext",
        "subject",
    }
)

# 命中即视为「可能夹带正文」的字段名片段（防御性检查，不参与构造）
_FORBIDDEN_FRAGMENTS = (
    "content",
    "text",
    "message",
    "msg",
    "prompt",
    "profile",
    "history",
    "memory",
    "attachment",
    "image",
    "file",
    "token",
    "secret",
    "password",
    "jwt",
    "apikey",
    "api_key",
    "credential",
)

DEFAULT_EVIDENCE_ENV = "NANA_SHADOW_EVIDENCE"
DEFAULT_EVIDENCE_PATH = "/tmp/nana_shadow/observer_evidence.jsonl"


def scoped_hash(value: Any, scope: str = HASH_SCOPE) -> str | None:
    """把任意主体字符串做 scoped SHA-256 摘要，永不返回原文。"""
    if value is None:
        return None
    try:
        raw = str(value)
    except Exception:
        return None
    return hashlib.sha256(f"{scope}:{raw}".encode("utf-8", "replace")).hexdigest()[:16]


def _safe_len(value: Any) -> int | None:
    try:
        return len(str(value))
    except Exception:
        return None


def build_lifecycle_record(
    kind: str,
    metadata: Any = None,
    *,
    source: str = "astrbot_internal_lifecycle",
    dispatcher_class: str = "plugin_manager_direct_registry_loop",
    now_ms: int | None = None,
) -> dict:
    """构造一条「零正文」生命周期观测记录。

    metadata 只用于提取 名称哈希 / 长度 / 版本 / reserved 布尔，
    绝不复制其任意字符串正文到输出。
    """
    subject: dict[str, Any] = {}
    subject["name_hash"] = scoped_hash(getattr(metadata, "name", None))
    subject["name_len"] = _safe_len(getattr(metadata, "name", None))
    version = getattr(metadata, "version", None)
    # 版本号是受控短标识，允许保留（非私人正文）
    if isinstance(version, (str, int, float)) and _safe_len(version) is not None and len(str(version)) <= 32:
        subject["version"] = str(version)
    if hasattr(metadata, "reserved"):
        subject["reserved"] = bool(getattr(metadata, "reserved"))

    record = {
        "schema": SCHEMA,
        "kind": kind,
        "observed_at_ms": int(now_ms if now_ms is not None else time.time() * 1000),
        "source": source,
        "synthetic": True,
        "binding_proof": True,
        "dispatcher_class": dispatcher_class,
        "no_plaintext": True,
        "subject": subject,
    }
    # 白名单过滤：任何非白名单字段一律剔除
    return {k: v for k, v in record.items() if k in ALLOWED_OUTPUT_FIELDS}


# subject 内部允许的字段
SUBJECT_ALLOWED_FIELDS = frozenset({"name_hash", "name_len", "version", "reserved"})
# 任何字符串值超过该长度即视为疑似正文
VALUE_MAX_LEN = 64


def looks_plaintext(record: Mapping[str, Any]) -> bool:
    """防御性自检：记录是否可能夹带正文。

    规则（任一命中即 True）：
      1. 顶层出现白名单以外的键
      2. subject 不是 dict，或含 SUBJECT_ALLOWED_FIELDS 以外的键
      3. 任意字符串值长度 > VALUE_MAX_LEN
    因为输出由白名单构造，正常记录永远为 False。
    """
    try:
        if not set(record).issubset(ALLOWED_OUTPUT_FIELDS):
            return True
        subject = record.get("subject") or {}
        if not isinstance(subject, Mapping):
            return True
        if not set(subject).issubset(SUBJECT_ALLOWED_FIELDS):
            return True

        def _suspicious(value: Any) -> bool:
            return isinstance(value, str) and len(value) > VALUE_MAX_LEN

        for key, value in record.items():
            if key == "subject":
                continue
            if _suspicious(value):
                return True
        for value in subject.values():
            if _suspicious(value):
                return True
    except Exception:
        # 自检本身出错 → 保守判定为可疑（fail-closed）
        return True
    return False


def resolve_evidence_path() -> str:
    """证据落盘路径：环境变量可覆盖，默认进程私有临时目录。"""
    path = os.environ.get(DEFAULT_EVIDENCE_ENV)
    if path:
        return path
    return DEFAULT_EVIDENCE_PATH


def emit_record(record: Mapping[str, Any], path: str | None = None) -> bool:
    """追加写一行 JSONL。失败返回 False —— 永不抛异常（fail-closed）。"""
    try:
        target = path or resolve_evidence_path()
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        line = json.dumps(dict(record), ensure_ascii=False, sort_keys=True)
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return True
    except Exception:
        return False
