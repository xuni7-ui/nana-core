"""Generated ORIGINAL Nana C.4 normalize compatibility snapshot.
Source: src/bili_agent/bili_event_source.py; regenerate with tools/nanalink_sync_c4.py.
No legacy Agent/pump/network execution is included.
"""
import re
from typing import Any, Dict, Optional

SOURCE_SHA256 = "fa77313968a580d3ea98a95f3dfbee27fc082a93825ed8659c13ca6348e3d3c1"
_BV = re.compile(r"/video/(BV[0-9A-Za-z]+)")

def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None

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
