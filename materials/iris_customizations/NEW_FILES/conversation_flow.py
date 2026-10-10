"""对话流水（只增不改的原文 JSONL · 重启后仍读得回）

为什么单独一个模块：
    L1 Buffer 住在内存里，一重启就空 —— 这正是「根本问题」的存储侧。
    本模块把每轮原文 append 到磁盘 JSONL，**只增不改**，
    重启后还能把原话读回来（兜底用）。

落点（按天分文件 · **日期 key 按北京时间**）：
    <AstrBot workspaces>/<会话净化名>/对话流水/YYYYMMDD.jsonl

时间口径（P0-A）：
    - `ts`     = aware UTC ISO8601（统一存储表示）
    - `ts_cst` = 北京时间镜像（人类可读，明确带 +08:00）
    - 文件日期 key = 北京时间（`timeutil.daykey_cst`），修「UTC 跨日错位」
    - 历史 naive 行按 UTC 解释（见 `iris_memory.utils.timeutil`）

护栏（照抄 decision_log.py 的尺度 · 宁可丢，不撑爆 4G 小服务器）：
    ① 单文件封顶 5MB —— 超了滚成 `<YYYYMMDD>.1.jsonl`；当天已滚过就放弃写
    ② 只留 30 天
    ③ 目录内最多 8 个文件（含当天正在写的那个）
    ④ 单字段截断 4000 字，避免单行撑爆

安全承诺：
    - 任何异常都被吞掉并返回 None，**绝不让主链路挂掉**
    - 不联网、不 import 重库、只碰 stdlib
    - 只以 "a" 模式追加，**永不重写 / 永不删除历史行**
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any, Optional

from iris_memory.utils import timeutil

# ============================================================================
# 护栏常量（要改就改这里）
# ============================================================================

FLOW_DIRNAME: str = "对话流水"
MAX_FILE_BYTES: int = 5 * 1024 * 1024      # 单文件封顶 5MB
KEEP_DAYS: int = 30                        # 只留 30 天
MAX_FILES: int = 8                         # 目录内最多 8 个文件
MAX_FIELD_CHARS: int = 4000                # 单字段截断长度
ENABLE_KEY: str = "l2_memory.conversation_flow_enable"

_lock = threading.Lock()


# ============================================================================
# 总开关 / 路径
# ============================================================================


def enabled(config: Any) -> bool:
    """读不到配置就一律当「不写」（宁可丢流水，不撑磁盘）。"""
    try:
        return bool(config.get(ENABLE_KEY, True))
    except Exception:
        return False


def _safe_umo(umo: str) -> str:
    """把 unified_msg_origin 净化成目录名（与 AstrBot 官方换算同风格）。"""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", (umo or "").strip())
    return safe.strip("_.-") or "unknown"


def _flow_dir(umo: str, create: bool) -> Optional[Path]:
    """`<会话工作区>/对话流水`；拿不到就返回 None（宁可不写）。

    create=False 时只解析路径、绝不建目录（回读侧专用）。
    """
    umo = (umo or "").strip()
    if not umo:
        return None
    base: Optional[Path] = None
    try:  # ① 优先用 AstrBot 官方换算（与奈奈平时操作的工作区同一处）
        from astrbot.core.workspace import default_workspace_root

        base = Path(default_workspace_root(umo))
    except Exception:
        try:  # ② 兜底：自己拼 workspaces 根 + 净化名
            from astrbot.core.utils.astrbot_path import get_astrbot_workspaces_path

            base = Path(get_astrbot_workspaces_path()) / _safe_umo(umo)
        except Exception:
            return None
    d = base / FLOW_DIRNAME
    if not create:
        return d
    try:
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        return None


def workspace_flow_dir(umo: str) -> Optional[Path]:
    """`<会话工作区>/对话流水`（写侧入口，会建目录）；拿不到就返回 None。"""
    return _flow_dir(umo, create=True)


def read_recent(umo: str, limit: int = 12) -> list[dict]:
    """只读：回读最近 limit 条流水（按时间正序）。

    回读侧的铁律：**只看、不摸**——不建目录、不写盘、不删文件。
    任何异常一律吞掉返回 []，绝不让主链路挂掉。
    """
    try:
        if limit <= 0:
            return []
        directory = _flow_dir(umo, create=False)
        if directory is None or not directory.is_dir():
            return []
        try:
            files = sorted(
                (p for p in directory.glob("*.jsonl") if p.is_file()),
                key=lambda p: p.stat().st_mtime,
            )
        except Exception:
            return []

        rows: list[dict] = []
        for path in reversed(files):  # 从最新文件往回凑，够数就停
            chunk: list[dict] = []
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        if isinstance(rec, dict):
                            chunk.append(rec)
            except Exception:
                continue
            rows = chunk + rows
            if len(rows) >= limit:
                break
        return rows[-limit:]
    except Exception:
        return []


def _prune(
    directory: Path,
    keep_days: int = KEEP_DAYS,
    max_files: int = MAX_FILES,
    reserve: int = 1,
) -> int:
    """清掉超期文件 + 超量文件（按修改时间从旧到新删）。返回删了几个。"""
    removed = 0
    try:
        files = sorted(
            (p for p in directory.glob("*.jsonl") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
    except Exception:
        return 0

    # TTL 一律用 epoch（时区无关），不再用本地 naive 时间做比较
    deadline = timeutil.epoch() - max(1, int(keep_days)) * 86400
    for p in list(files):
        try:
            if p.stat().st_mtime < deadline:
                p.unlink()
                files.remove(p)
                removed += 1
        except Exception:
            continue

    overflow = len(files) - (max_files - reserve)
    for p in files[: max(0, overflow)]:
        try:
            p.unlink()
            removed += 1
        except Exception:
            continue
    return removed


# ============================================================================
# 追加（唯一对外写入口）
# ============================================================================


def _clip(value: Any) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= MAX_FIELD_CHARS else text[:MAX_FIELD_CHARS] + "…(截断)"


def append_turn(
    umo: str,
    role: str,
    content: Any,
    sender_id: str = "",
    sender_name: str = "",
    extra: Any = None,
) -> Optional[Path]:
    """只增不改地追加一行流水。**永不抛异常**，失败返回 None。"""
    try:
        if not content:
            return None
        try:
            from iris_memory.config import get_config

            config = get_config()
        except Exception:
            config = None
        if config is not None and not enabled(config):
            return None

        directory = workspace_flow_dir(umo)
        if directory is None:
            return None

        now = timeutil.now_utc()
        record = {
            # ts：统一存储表示（aware UTC ISO8601）
            "ts": timeutil.iso_utc(now),
            # ts_cst：人类可读的北京时间镜像（明确带 +08:00），方便姐姐直接看
            "ts_cst": timeutil.cst_full(now),
            "umo": _clip(umo),
            "role": _clip(role) or "unknown",
            "sender_id": _clip(sender_id),
            "sender_name": _clip(sender_name),
            "text": _clip(content),
        }
        if extra is not None:
            record["extra"] = _clip(extra)
        line = json.dumps(record, ensure_ascii=False) + "\n"

        # 文件日期 key 必须按【北京时间】生成（修跨日错位）：
        # 北京时间 00:50 的消息要落在「北京时间那一天」的文件里，
        # 而不是容器 UTC 的昨天（旧实现 datetime.now()=UTC 会错位一天）。
        daykey = timeutil.daykey_cst(now)
        with _lock:
            _prune(directory)
            path = directory / f"{daykey}.jsonl"
            try:
                if path.exists() and path.stat().st_size >= MAX_FILE_BYTES:
                    rolled = directory / f"{daykey}.1.jsonl"
                    if rolled.exists():   # 当天已滚过 → 直接放弃写
                        return None
                    path = rolled
            except Exception:
                pass
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
        _log_first_write(path)
        return path
    except Exception as e:
        _log_first_error(e)
        return None


_first_write_logged = False
_first_error_logged = False


def _lazy_logger():
    try:
        from iris_memory.core.logger import get_logger

        return get_logger("conversation_flow")
    except Exception:
        return None


def _log_first_write(path: Path) -> None:
    """进程内一次性自检：确认流水真的开始落盘（治「以为写了其实没写」）。"""
    global _first_write_logged
    if _first_write_logged:
        return
    _first_write_logged = True
    lg = _lazy_logger()
    if lg:
        lg.info(f"对话流水已开始落盘（进程内首次）：{path}")


def _log_first_error(err: BaseException) -> None:
    """进程内一次性自检：流水写入失败原因必须留痕，不许静默吞掉。"""
    global _first_error_logged
    if _first_error_logged:
        return
    _first_error_logged = True
    lg = _lazy_logger()
    if lg:
        lg.warning(f"对话流水写入失败（进程内首次）：{type(err).__name__}: {err}")


def append_event(event: Any, role: str, content: Any, extra: Any = None) -> Optional[Path]:
    """从事件里取 umo / 发送者，再追加一行。同样**永不抛异常**。"""
    try:
        umo = getattr(event, "unified_msg_origin", "") or ""
        sender_id = ""
        sender_name = ""
        try:
            sender_id = str(
                event.get_sender_id() if hasattr(event, "get_sender_id") else ""
            )
        except Exception:
            pass
        try:
            sender_name = str(
                event.get_sender_name() if hasattr(event, "get_sender_name") else ""
            )
        except Exception:
            pass
        return append_turn(
            umo=umo,
            role=role,
            content=content,
            sender_id=sender_id,
            sender_name=sender_name,
            extra=extra,
        )
    except Exception:
        return None
