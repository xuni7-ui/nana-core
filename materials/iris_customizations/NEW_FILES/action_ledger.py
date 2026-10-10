"""Iris Chat Memory - 动作账本（Action Ledger, v1）

设计目标（对应「方案② 中档」）：
    日志记的是「发生过什么」，账本记的是「现在是什么」。
    按 **资源键** 覆盖（upsert），同一个键永远只留最新一行，
    保证任何时候翻账都能直接拿到「最新状态」，而不是一堆要自己排序的流水。

三层存储：
    ledger.json   —— 物化的当前状态（按 key 索引，原子写入）
    ledger.jsonl  —— append-only 流水（审计 / 可重建 ledger.json）
    backups/      —— 每次写入前的滚动备份（保留最近 N 份）

安全护栏：
    * 单键 upsert，最大 MAX_KEYS 个键，超出的老键淘汰
    * journal 单文件超过 JOURNAL_MAX_BYTES 就轮转，最多留 JOURNAL_KEEP 份
    * 原子写（tmp + fsync + os.replace），中途崩掉不会留下半个坏文件
    * 本模块 **不被任何现有代码 import**，纯外挂，零行为变更

用法（CLI）：
    python3 action_ledger.py list
    python3 action_ledger.py get semantic_gate_enable
    python3 action_ledger.py set semantic_gate_enable true --op 开闸 --verify "决策日志 18:10 起落盘"
    python3 action_ledger.py rebuild
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

LEDGER_VERSION = 1
CST = timezone(timedelta(hours=8))

MAX_KEYS = 200
JOURNAL_MAX_BYTES = 5 * 1024 * 1024
JOURNAL_KEEP = 8
BACKUP_KEEP = 20


def _default_dir() -> Path:
    """定位账本目录：优先环境变量，其次按插件相对路径推导。"""
    env = os.environ.get("NANA_LEDGER_DIR")
    if env:
        return Path(env)
    # iris_memory/core/action_ledger.py -> parents[2] = 插件根目录
    plugin_root = Path(__file__).resolve().parents[2]
    return plugin_root.parent.parent / "plugin_data" / "astrbot_plugin_iris_chat_memory" / "action_ledger"


LEDGER_DIR = _default_dir()
LEDGER_FILE = LEDGER_DIR / "ledger.json"
JOURNAL_FILE = LEDGER_DIR / "ledger.jsonl"
BACKUP_DIR = LEDGER_DIR / "backups"


def _now_iso() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S+08:00")


def _ensure_dirs() -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_ledger() -> Dict[str, Any]:
    if not LEDGER_FILE.exists():
        return {"version": LEDGER_VERSION, "updated_at": None, "keys": {}}
    try:
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "keys" not in data:
            raise ValueError("bad ledger shape")
        return data
    except Exception:
        # 坏了就从流水重建，不抛异常打断调用方
        return rebuild_from_journal(silent=True)


def _backup() -> None:
    if not LEDGER_FILE.exists():
        return
    stamp = datetime.now(CST).strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"ledger.json.bak_{stamp}"
    try:
        dst.write_bytes(LEDGER_FILE.read_bytes())
    except Exception:
        return
    olds = sorted(BACKUP_DIR.glob("ledger.json.bak_*"))
    for old in olds[:-BACKUP_KEEP]:
        try:
            old.unlink()
        except Exception:
            pass


def _append_journal(record: Dict[str, Any]) -> None:
    _ensure_dirs()
    if JOURNAL_FILE.exists() and JOURNAL_FILE.stat().st_size >= JOURNAL_MAX_BYTES:
        stamp = datetime.now(CST).strftime("%Y%m%d_%H%M%S")
        JOURNAL_FILE.rename(JOURNAL_DIR_ROTATED(stamp))
        olds = sorted(LEDGER_DIR.glob("ledger.*.jsonl"))
        for old in olds[:-JOURNAL_KEEP]:
            try:
                old.unlink()
            except Exception:
                pass
    with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def JOURNAL_DIR_ROTATED(stamp: str) -> Path:
    return LEDGER_DIR / f"ledger.{stamp}.jsonl"


def upsert(
    key: str,
    state: Any,
    *,
    op: Optional[str] = None,
    verify: Optional[str] = None,
    note: Optional[str] = None,
    actor: str = "nana",
    ts: Optional[str] = None,
) -> Dict[str, Any]:
    """按资源键写入/覆盖一条状态。返回这条账目。"""
    _ensure_dirs()
    data = _read_ledger()
    keys: Dict[str, Any] = data.get("keys", {})
    now = ts or _now_iso()

    old = keys.get(key)
    entry = {
        "key": key,
        "state": state,
        "updated_at": now,
        "op": op,
        "verify": verify,
        "note": note,
        "actor": actor,
        "first_at": (old or {}).get("first_at", now),
        "revision": int((old or {}).get("revision", 0)) + 1,
    }
    keys[key] = entry

    # 超量淘汰：按 updated_at 从旧到新砍掉多余的键
    if len(keys) > MAX_KEYS:
        order = sorted(keys.items(), key=lambda kv: str(kv[1].get("updated_at", "")))
        for k, _ in order[: len(keys) - MAX_KEYS]:
            keys.pop(k, None)

    data = {"version": LEDGER_VERSION, "updated_at": _now_iso(), "keys": keys}
    _backup()
    _atomic_write_json(LEDGER_FILE, data)
    _append_journal({"t": now, "actor": actor, "event": "upsert", **entry})
    return entry


def get(key: str) -> Optional[Dict[str, Any]]:
    e = _read_ledger().get("keys", {}).get(key)
    return _normalize_entry(e) if isinstance(e, dict) else e


def _normalize_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    """兼容旧条目：缺 updated_at 的用 first_at 兜底（防 list 崩）。"""
    if not e.get("updated_at"):
        e = dict(e)
        e["updated_at"] = e.get("first_at")
    return e


def snapshot(limit: Optional[int] = None) -> Dict[str, Any]:
    keys = _read_ledger().get("keys", {})
    items = [_normalize_entry(e) for e in keys.values()]
    items.sort(key=lambda e: str(e.get("updated_at") or ""), reverse=True)
    if limit:
        items = items[:limit]
    return {"count": len(keys), "items": items}


def rebuild_from_journal(silent: bool = False) -> Dict[str, Any]:
    """从流水重放重建当前状态（账本损坏时的兜底）。"""
    keys: Dict[str, Any] = {}
    if JOURNAL_FILE.exists():
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("event") != "upsert" or not rec.get("key"):
                    continue
                rec.pop("event", None)
                keys[rec["key"]] = rec
    data = {"version": LEDGER_VERSION, "updated_at": _now_iso(), "keys": keys}
    if not silent:
        _ensure_dirs()
        _atomic_write_json(LEDGER_FILE, data)
    return data


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _main() -> None:
    ap = argparse.ArgumentParser(description="奈奈的动作账本")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出全部账目（按更新时间倒序）")
    p_get = sub.add_parser("get", help="查一个资源键")
    p_get.add_argument("key")
    p_set = sub.add_parser("set", help="写入/覆盖一个资源键")
    p_set.add_argument("key")
    p_set.add_argument("state", help="状态值（自动尝试 JSON 解析，失败按字符串存）")
    p_set.add_argument("--op", default=None)
    p_set.add_argument("--verify", default=None)
    p_set.add_argument("--note", default=None)
    p_set.add_argument("--actor", default="nana")
    p_set.add_argument("--ts", default=None)
    sub.add_parser("rebuild", help="从流水重建账本")
    sub.add_parser("where", help="打印账本目录")

    args = ap.parse_args()

    if args.cmd == "where":
        print(LEDGER_DIR)
    elif args.cmd == "list":
        snap = snapshot()
        print(f"共 {snap['count']} 条 | 目录 {LEDGER_DIR}")
        for e in snap["items"]:
            print(f"  {e.get('updated_at')}  {e['key']} = {json.dumps(e['state'], ensure_ascii=False)}"
                  f"{'  # ' + e['op'] if e.get('op') else ''}")
    elif args.cmd == "get":
        e = get(args.key)
        print(json.dumps(e, ensure_ascii=False, indent=2) if e else f"(无此键: {args.key})")
    elif args.cmd == "set":
        try:
            state = json.loads(args.state)
        except Exception:
            state = args.state
        e = upsert(args.key, state, op=args.op, verify=args.verify,
                   note=args.note, actor=args.actor, ts=args.ts)
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif args.cmd == "rebuild":
        data = rebuild_from_journal()
        print(f"重建完成：{len(data['keys'])} 条 → {LEDGER_FILE}")


if __name__ == "__main__":
    _main()
