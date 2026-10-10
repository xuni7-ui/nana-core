"""Iris Chat Memory - 统一时间入口（timeutil）

一句话原则：
    **存储 / 计算层统一，展示层保持北京时间。**

    - 内部比较 / 排序 / TTL / updated_at  → UTC / epoch 等统一表示
    - 持久化时间                          → 明确、可解析、带时区（+00:00 / +08:00）
    - 用户可见时间 / L1 时间              → +08:00（北京时间）

为什么要有这个模块：
    改造前全仓有「四套口径」——
      ① 对话流水 / 决策日志：naive「本地时钟」字符串（实测容器 TZ=UTC，值=UTC 但没标）
      ② 动作账本：`...+08:00`（CST，有标）
      ③ L2/L3/dream 等 10+ 处 `datetime.now().isoformat()`（值=UTC，没标）
      ④ 展示层各自写手工补丁 `now + timedelta(hours=8)`
    结果是 naive-UTC 与 aware-CST 在字符串上无法区分，谁忘了 +8h 就静默错 8 小时。
    本模块把「唯一权威表示」收敛到一处：aware datetime / epoch。
    其它模块要么调这里，要么按这里的兼容规则 parse，**禁止再写手工 +8h 补丁**。

历史兼容（重要）：
    改造前落库的多数时间戳是 naive 字符串。容器 TZ 实测为 UTC，
    故这些 naive 值一律按 **UTC** 解释（assume="utc"），绝不猜本地时区。
    这样 `naive(值=UTC) 按 UTC 读` 结果正确，不会重复叠加 8 小时。

安全承诺：
    - 纯函数、零副作用、零网络、只碰 stdlib
    - 任何解析失败返回 None（不猜、不用当前时间冒充）
"""

from __future__ import annotations

import time as _time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# ============================================================================
# 常量
# ============================================================================

UTC = timezone.utc
CST = timezone(timedelta(hours=8))          # 北京时间（固定 +08:00，无夏令时）

WEEKDAY_CN = "一二三四五六日"

#: 存储 / 展示时最常用的机器可读格式
FMT_ISO = "%Y-%m-%dT%H:%M:%S%z"             # aware ISO8601，带偏移
FMT_SEC = "%Y-%m-%d %H:%M:%S"               # 秒级可读（不带时区，需先 display_*）
FMT_DAYKEY = "%Y%m%d"                       # 文件日期 key（必须按北京时间生成）
FMT_CST_FULL = "%Y-%m-%d %H:%M:%S+08:00"    # 北京时间全量（人类可读 + 明确带时区）


# ============================================================================
# 取当前时刻
# ============================================================================


def now_utc() -> datetime:
    """当前时刻（aware，UTC）。内部计算 / 存储的统一基准。"""
    return datetime.now(UTC)


def now_cst() -> datetime:
    """当前时刻（aware，北京时间 +08:00）。展示 / L1 时间锚用。"""
    return datetime.now(CST)


def epoch() -> float:
    """当前 Unix 时间戳（秒，float）。用于 TTL / 排序等纯数值比较。"""
    return _time.time()


# ============================================================================
# 归一化 / 解析
# ============================================================================


def ensure_aware(dt: datetime, assume: str = "utc") -> datetime:
    """把 datetime 归一成 aware。

    - 已带 tzinfo → 原样返回（保留其真实时区）
    - naive       → 按 `assume` 补上时区（默认 UTC，即历史兼容规则）

    绝不猜测：assume 只允许 "utc" / "cst"。
    """
    if dt is None:
        raise TypeError("ensure_aware() 不接受 None")
    if dt.tzinfo is not None:
        return dt
    if assume == "utc":
        return dt.replace(tzinfo=UTC)
    if assume == "cst":
        return dt.replace(tzinfo=CST)
    raise ValueError(f"未知的 assume 取值：{assume!r}（只允许 'utc' / 'cst'）")


def parse(value: Any, assume: str = "utc") -> Optional[datetime]:
    """把任意持久化时间解析成 aware datetime；解析不了返回 None（不猜）。

    支持：
      - datetime          → 归一化
      - int / float       → 视作 Unix 时间戳（秒）
      - 字符串 ISO8601    → 带偏移按原偏移；naive 按 `assume` 解释
      - "2026-10-06 16:50:26"（空格分隔）→ 兼容解析
      - "%Y%m%d" 日期 key → 当天 00:00（按 `assume`）

    历史兼容：naive 字符串默认按 UTC 解释（assume="utc"）。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_aware(value, assume)
    if isinstance(value, bool):          # bool 是 int 的子类，先挡掉
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except Exception:
            return None
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # 纯数字字符串 → 视作时间戳
    if s.isdigit() and len(s) >= 9:
        try:
            return datetime.fromtimestamp(float(s), tz=UTC)
        except Exception:
            pass

    # 8 位日期 key（YYYYMMDD）
    if len(s) == 8 and s.isdigit():
        try:
            return datetime.strptime(s, FMT_DAYKEY).replace(tzinfo=CST if assume == "cst" else UTC)
        except Exception:
            return None

    # Z 结尾（白名单，避免 fromisoformat 旧版本不认）
    normalized = s
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    for candidate in (normalized, normalized.replace(" ", "T", 1)):
        try:
            return ensure_aware(datetime.fromisoformat(candidate), assume)
        except Exception:
            continue
    return None


# ============================================================================
# 展示层（北京时间）
# ============================================================================


def display_cst(value: Any) -> Optional[datetime]:
    """把任意时间换算成「aware 的北京时间」。解析不了返回 None。"""
    dt = parse(value) if not isinstance(value, datetime) else ensure_aware(value)
    if dt is None:
        return None
    return dt.astimezone(CST)


def format_cst(value: Any, fmt: str = FMT_SEC) -> str:
    """格式化成北京时间字符串；解析不了返回空串（调用方自己兜底文案）。"""
    dt = display_cst(value)
    return dt.strftime(fmt) if dt is not None else ""


def cst_full(value: Any = None) -> str:
    """北京时间全量串 `YYYY-MM-DD HH:MM:SS+08:00`（人类可读 + 明确带时区）。"""
    dt = display_cst(value) if value is not None else now_cst()
    if dt is None:
        dt = now_cst()
    return dt.strftime("%Y-%m-%d %H:%M:%S") + "+08:00"


def daykey_cst(value: Any = None) -> str:
    """文件日期 key（**按北京时间** 生成 YYYYMMDD）。

    这是「跨日归档」的关键：北京时间 00:50 的消息必须写进「北京时间那一天」
    的文件，而不是容器 UTC 的昨天。
    """
    dt = display_cst(value) if value is not None else now_cst()
    if dt is None:
        dt = now_cst()
    return dt.strftime(FMT_DAYKEY)


def weekday_cn(value: Any = None) -> str:
    """北京时间对应的「周一/周二…」（返回单个汉字：一~日）。"""
    dt = display_cst(value) if value is not None else now_cst()
    if dt is None:
        dt = now_cst()
    return WEEKDAY_CN[dt.weekday()]


# ============================================================================
# 存储层（UTC / epoch）
# ============================================================================


def iso_utc(value: Any = None) -> str:
    """持久化用：aware ISO8601（UTC，带 +00:00）。`value=None` 表示当前时刻。"""
    dt = ensure_aware(value) if isinstance(value, datetime) else parse(value)
    if dt is None:
        dt = now_utc()
    return dt.astimezone(UTC).isoformat()


def iso_cst(value: Any = None) -> str:
    """持久化 / 展示两用：aware ISO8601（北京时间，带 +08:00）。"""
    dt = display_cst(value) if value is not None else now_cst()
    if dt is None:
        dt = now_cst()
    return dt.isoformat()


__all__ = [
    "UTC",
    "CST",
    "WEEKDAY_CN",
    "FMT_ISO",
    "FMT_SEC",
    "FMT_DAYKEY",
    "FMT_CST_FULL",
    "now_utc",
    "now_cst",
    "epoch",
    "ensure_aware",
    "parse",
    "display_cst",
    "format_cst",
    "cst_full",
    "daykey_cst",
    "weekday_cn",
    "iso_utc",
    "iso_cst",
]
