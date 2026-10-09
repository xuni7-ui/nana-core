#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C.4 第一阶段 · B站事件源（**只读**）

只做三件事：
  1) 只读拉取「回复」「@」两类事件（msgfeed/reply、msgfeed/at），各取最新一页
  2) 归一化成统一事件结构
  3) 给出**稳定唯一 ID**：B站真实 ID 组合  business_id + source_id(rpid)
     —— 不用时间戳猜测 / 不用正文 hash / 不用 LLM / 不用"上次看到的内容"

不做：不去重（去重是 pump 的事）、不调写接口、不碰主聊天 memory、不建新存储。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

CH_REPLY = "reply"
CH_AT = "at"
CHANNELS = (CH_REPLY, CH_AT)

_BV = re.compile(r"/video/(BV[0-9A-Za-z]+)")


def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


async def fetch_channel(cred, channel: str) -> Dict[str, Any]:
    """只读拉取一个通道的原始事件。

    返回 {"ok": bool, "error": str|None, "items": [...]}
    ★ ok=False 表示**这次没看见**，不代表"没有事件" —— 调用方必须停下，不许推断。
    """
    from bilibili_api import session as S

    try:
        if channel == CH_AT:
            resp = await S.get_at(cred)
        else:
            resp = await S.get_replies(cred)
    except Exception as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e), "items": []}

    if not isinstance(resp, dict):
        return {"ok": False, "error": "回包结构异常(非 dict)", "items": []}
    items = resp.get("items")
    if not isinstance(items, list):
        return {"ok": False, "error": "回包缺少 items 列表", "items": []}
    return {"ok": True, "error": None, "items": items,
            "cursor": resp.get("cursor"), "last_view_at": resp.get("last_view_at")}


def normalize(channel: str, item: Dict[str, Any], *,
              my_mid: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """把一个 msgfeed item 归一化成事件。

    ★ 关键字段（business_id / source_id / bvid）缺任何一个 → 返回 None，
      **绝不猜**（宁可不处理，也不乱发）。
    """
    if not isinstance(item, dict):
        return None
    it = item.get("item")
    if not isinstance(it, dict):
        return None

    business_id = _as_int(it.get("business_id"))
    source_id = _as_int(it.get("source_id"))        # ★ B站真实评论 rpid
    root_id = _as_int(it.get("root_id")) or 0
    if business_id is None or not source_id:
        return None

    uri = it.get("uri") or ""
    m = _BV.search(uri)
    if not m:
        return None
    bvid = m.group(1)

    user = item.get("user") or {}
    author_mid = _as_int(user.get("mid"))

    return {
        # ★ 稳定唯一 ID：B站真实 ID 组合（business_type=channel/business_id + rpid）
        "eid": "%s:%s:%s" % (channel, business_id, source_id),
        "channel": channel,
        "business_id": business_id,
        "source_id": source_id,        # 要回的评论 rpid（全局唯一）
        "root_id": root_id,            # 顶层祖先（0=自身即顶层）
        "msgfeed_id": _as_int(item.get("id")),
        "bvid": bvid,
        "aid": _as_int(it.get("subject_id")),
        "author_mid": author_mid,
        "author_name": user.get("nickname") or user.get("uname") or "",
        "message": it.get("source_content") or "",
        "ctype": it.get("type") or "",
        "ctime": _as_int(item.get("reply_time") or item.get("at_time")),
        # 是否自己发的事件（确定性规则，不问 LLM）
        "is_mine": (author_mid is not None and my_mid is not None
                    and int(author_mid) == int(my_mid)),
    }


def target_comment_id(ev: Dict[str, Any]) -> int:
    return int(ev["source_id"])


def target_root(ev: Dict[str, Any]) -> Optional[int]:
    r = int(ev.get("root_id") or 0)
    return r if r and r != int(ev["source_id"]) else None


def collect(raw_by_channel: Dict[str, Dict[str, Any]], *,
            my_mid: Optional[int] = None) -> Dict[str, Any]:
    """把"各通道原始回包"归一化成事件列表 + 坏事件清单。

    返回 {"ok":bool, "errors":[...], "events":[...], "bad":[...]}
    ok=False = 至少一个通道没读到 → 调用方必须停止本轮（不许把"没看见"当"没有"）。
    """
    errors: List[str] = []
    events: List[Dict[str, Any]] = []
    bad: List[Dict[str, Any]] = []

    for ch in CHANNELS:
        r = raw_by_channel.get(ch) or {}
        if not r.get("ok"):
            errors.append("%s: %s" % (ch, r.get("error") or "读取失败"))
            continue
        for raw in (r.get("items") or []):
            ev = normalize(ch, raw, my_mid=my_mid)
            if ev is None:
                bad.append({"channel": ch,
                            "item_keys": sorted((raw.get("item") or {}).keys())
                            if isinstance(raw, dict) else [],
                            "id": raw.get("id") if isinstance(raw, dict) else None})
            else:
                events.append(ev)

    return {"ok": not errors, "errors": errors, "events": events, "bad": bad}
