"""裁决决策日志（JSONL 落盘 · 4G 小服务器护栏版）

落盘目标：`tests/` 无关，正式落点 `iris_memory/core/decision_log.py`
数据落点：`<插件数据目录>/decision_log/YYYYMMDD.jsonl`（一天一个文件，一行一轮）

为什么单独一个模块：
    `semantic_gate.py` 的底线是「纯函数、零副作用、零网络」，
    落盘这种事不能塞进去——否则单测就会真的碰磁盘。所以护栏写在这里，
    gate 只出纯数据，接线层负责调用。

三条护栏（宁可丢日志，不许撑爆小服务器）：
    ① 单文件封顶 5MB —— 超了就把当天文件滚成 `YYYYMMDD.1.jsonl`；
       若当天已滚过一次，则**直接放弃写**（不无限滚）。
    ② 只留 7 天 —— 启动/写入时顺手清掉超期文件。
    ③ 目录里最多 8 个文件（**含当天正在写的那个**）—— 兜底防呆，再多就删最旧的。

安全承诺：
    - 任何异常都被吞掉并返回 None，**绝不让主链路挂掉**
    - 不联网、不 import 重库、只碰 stdlib
    - 每行超过 200 字的字段会被截断，避免单行撑爆
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Mapping, Optional

from iris_memory.utils import timeutil

# ============================================================================
# 护栏常量（要改就改这里，别散在函数里）
# ============================================================================

DECISION_LOG_DIRNAME: str = "decision_log"
MAX_FILE_BYTES: int = 5 * 1024 * 1024      # 单文件封顶 5MB
KEEP_DAYS: int = 7                          # 只留 7 天
MAX_FILES: int = 8                          # 目录内最多 8 个文件
MAX_FIELD_CHARS: int = 200                  # 单字段截断长度
ENABLE_KEY: str = "l2_memory.decision_log_enable"
GATE_KEY: str = "l2_memory.semantic_gate_enable"   # 总闸：关＝不落任何行

_lock = threading.Lock()


# ============================================================================
# 路径与清理
# ============================================================================


def log_dir(data_dir: Any) -> Optional[Path]:
    """`<插件数据目录>/decision_log`；拿不到数据目录就返回 None（宁可不写）。"""
    if not data_dir:
        return None
    try:
        d = Path(data_dir) / DECISION_LOG_DIRNAME
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        return None


def _prune(
    directory: Path,
    keep_days: int = KEEP_DAYS,
    max_files: int = MAX_FILES,
    reserve: int = 1,
) -> int:
    """清掉超期文件 + 超量文件（按修改时间从旧到新删）。返回删了几个。

    `reserve`：给「马上要写的那一个文件」预留的名额，
    这样「目录内最多 8 个」是**写完之后的**总数，不是写之前的。
    """
    removed = 0
    try:
        files = sorted(
            (p for p in directory.glob("*.jsonl") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
    except Exception:
        return 0

    # P0-A：文件清理改用 epoch（时区无关），不再用 naive 本地时间比较
    deadline_epoch = timeutil.epoch() - max(1, int(keep_days)) * 86400
    alive = []
    for p in files:
        try:
            too_old = p.stat().st_mtime < deadline_epoch
        except Exception:
            too_old = False
        if too_old:
            try:
                p.unlink()
                removed += 1
                continue
            except Exception:
                pass
        alive.append(p)

    cap = max(1, int(max_files) - max(0, int(reserve)))
    overflow = len(alive) - cap
    for p in alive[:max(0, overflow)]:
        try:
            p.unlink()
            removed += 1
        except Exception:
            pass
    return removed


def _rotate_if_needed(path: Path, max_bytes: int = MAX_FILE_BYTES) -> Optional[Path]:
    """单文件超 5MB → 滚成 `<YYYYMMDD>.1.jsonl`；当天已滚过就返回 None（放弃写）。"""
    try:
        if (not path.exists()) or path.stat().st_size < max_bytes:
            return path
        rolled = path.with_name(path.stem + ".1" + path.suffix)
        if rolled.exists():
            return None                      # 一天只滚一次，剩下的宁可丢
        path.rename(rolled)
        return path
    except Exception:
        return None


# ============================================================================
# 记录构造
# ============================================================================


def _clip(value: Any, limit: int = MAX_FIELD_CHARS) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ").replace("\r", " ").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def make_record(
    tier: str,
    reason: str = "",
    query: Any = "",
    top_k: int = 0,
    hits: int = 0,
    route: str = "",
    soft_confirm: bool = False,
    window: Any = None,
    elapsed_ms: Any = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict:
    """一轮裁决的日志记录（纯函数，方便单测）。"""
    record = {
        "t": timeutil.cst_full(),        # 北京时间（人类可读，带 +08:00）
        "t_utc": timeutil.iso_utc(),     # aware UTC ISO8601（机器口径）
        "tier": _clip(tier, 32),
        "reason": _clip(reason),
        "query": _clip(query),
        "top_k": int(top_k or 0),
        "hits": int(hits or 0),
        "route": _clip(route, 32),
        "soft_confirm": bool(soft_confirm),
    }
    if window is not None:
        record["window"] = _clip(window, 64)
    if elapsed_ms is not None:
        try:
            record["ms"] = int(elapsed_ms)
        except Exception:
            pass
    if extra:
        for k, v in extra.items():
            key = _clip(k, 24)
            if key and key not in record:
                record[key] = _clip(v)
    return record


# ============================================================================
# 落盘入口：唯一的对外副作用函数（永不抛异常）
# ============================================================================


def write_decision(
    record: Mapping[str, Any],
    data_dir: Any,
    max_bytes: int = MAX_FILE_BYTES,
    keep_days: int = KEEP_DAYS,
    max_files: int = MAX_FILES,
) -> Optional[Path]:
    """追加一行 JSONL。返回落盘的路径；任何异常/被拒都返回 None。

    Args:
        record: `make_record()` 产出的字典
        data_dir: 插件数据目录（`config.data_dir`），取不到就不写
    """
    try:
        directory = log_dir(data_dir)
        if directory is None or not record:
            return None

        with _lock:
            _prune(directory, keep_days, max_files, reserve=1)
            path = directory / f"{timeutil.daykey_cst()}.jsonl"
            target = _rotate_if_needed(path, max_bytes)
            if target is None:
                return None
            line = json.dumps(dict(record), ensure_ascii=False)
            with open(target, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            return target
    except Exception:
        return None


def emit(
    event: Any,
    data_dir: Any,
    tier: str,
    reason: str = "",
    query: Any = "",
    top_k: int = 0,
    hits: int = 0,
    route: str = "",
    soft_confirm: bool = False,
    window: Any = None,
    elapsed_ms: Any = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Optional[Path]:
    """接线层用的顺手版：自己拼记录 + 落盘 + 顺带把结论挂到 event 上（便于 L3 读）。"""
    try:
        record = make_record(
            tier=tier, reason=reason, query=query, top_k=top_k, hits=hits,
            route=route, soft_confirm=soft_confirm, window=window,
            elapsed_ms=elapsed_ms, extra=extra,
        )
        if event is not None:
            try:
                setattr(event, "_iris_decision", record)
            except Exception:
                pass
        return write_decision(record, data_dir)
    except Exception:
        return None


def should_log(config: Any, default: bool = False) -> bool:
    """日志是否该落盘。**两道门都要开**：

    ① `l2_memory.decision_log_enable`（日志自己的开关，缺省关）
    ② `l2_memory.semantic_gate_enable`（语意裁决总闸，缺省关）

    为什么要第二道：总闸关时行为要与 v1 逐字节一致，**包括不写盘**。
    读配置异常一律当「不写」处理（宁可丢日志，不撑磁盘）。
    """
    try:
        if not bool(config.get(GATE_KEY, False)):
            return False
        return bool(config.get(ENABLE_KEY, default))
    except Exception:
        return False
