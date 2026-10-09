#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站发送动作可靠性核心（C.2）

统一状态机：  precheck → send → result → verify → record

设计原则（对齐 Harness：「能用代码卡住的事，别只写在提示词里」）：
  * 绝不盲目重发 —— 发送回包不明确时，先查 B站 真实状态再定性。
  * 幂等真相源 = B站自己（precheck 直接查评论列表），不是本地记账。
  * PENDING_VERIFY（未决态）绝不自动重试。
  * 复用现有账本，不另造：bili_comment_log.jsonl（流水） + Action Ledger（当前状态）。

状态定义（对外唯一词汇表）：
  PRE_EXIST       发前已存在同文评论 → 未发送，幂等命中，视为成功
  VERIFIED        已确认 B站 上真实存在（拿到 rpid）
  RETRYABLE       服务端明确答复失败、且确认无副作用 → 可安全重试
  PENDING_VERIFY  状态不明（回包残缺/读不到 code / 网络异常 / 12051 但查不到） → 禁止自动重试
  DRY_RUN         空跑，未发送

退出码： 0=VERIFIED/PRE_EXIST   1=RETRYABLE   2=PENDING_VERIFY   3=DRY_RUN
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

CRED_PATH = "/root/.nana_secrets/bilibili_credential.json"
LOG_PATH = "/root/.nana_secrets/bili_comment_log.jsonl"
LEDGER_DIR = "/AstrBot/data/plugins/astrbot_plugin_iris_chat_memory/iris_memory/core"

# ---- 状态常量 ----
PRE_EXIST = "PRE_EXIST"
VERIFIED = "VERIFIED"
RETRYABLE = "RETRYABLE"
PENDING_VERIFY = "PENDING_VERIFY"
DRY_RUN = "DRY_RUN"

# 明确"重复评论"的码：说明服务端认为同文已存在 → 必须去核实，不能当失败重发
CODE_DUPLICATE = 12051

EXIT_CODE = {PRE_EXIST: 0, VERIFIED: 0, RETRYABLE: 1, PENDING_VERIFY: 2, DRY_RUN: 3}


# ============ 基础工具 ============

def load_cred():
    from bilibili_api.utils.network import Credential
    ck = json.load(open(CRED_PATH, encoding="utf-8"))
    return Credential(
        sessdata=ck.get("sessdata") or "",
        bili_jct=ck.get("bili_jct") or "",
        buvid3=ck.get("buvid3") or "",
        buvid4=ck.get("buvid4") or "",
        dedeuserid=ck.get("dedeuserid") or "",
        ac_time_value=ck.get("ac_time_value") or "",
    ), ck


def _norm(s: str) -> str:
    """去空白 + 去零宽字符，用于比对正文（B站渲染 @ 时会插空格）。"""
    s = s or ""
    s = re.sub(r"[\u200b-\u200f\ufeff]", "", s)
    return re.sub(r"\s+", "", s)


def text_matches(candidate: str, target: str, head: int = 16) -> bool:
    """判断列表里的评论正文是否就是我们要发的那条。

    @ 渲染 / 首尾空白会造成差异，故取**前 head 字**做包含匹配（默认 16 字）。
    """
    a, b = _norm(candidate), _norm(target)
    if not a or not b:
        return False
    if a == b or b in a:
        return True
    return b[:head] in a


def text_fingerprint(text: str) -> str:
    return hashlib.sha1(_norm(text).encode("utf-8")).hexdigest()[:12]


# ============ Action Ledger 接入（复用现有账本） ============

def ledger_upsert(key: str, state: Any, *, op: str = None, verify: str = None, note: str = None):
    """写 Action Ledger 当前状态。账本失败绝不影响发送主流程。"""
    try:
        if LEDGER_DIR not in sys.path:
            sys.path.insert(0, LEDGER_DIR)
        import action_ledger  # noqa
        return action_ledger.upsert(key, state, op=op, verify=verify, note=note, actor="nana")
    except Exception as e:  # 账本是状态镜像，不是主账，失败只提醒
        print("[warn] ledger_upsert 失败：%s: %s" % (type(e).__name__, e), flush=True)
        return None


def ledger_record(kind: str, bvid: str, status: str, *, rpid=None, note=None, root=None):
    """把'当前是什么状态'写进账本（两个键，不膨胀）。"""
    verify_txt = "bili_comment_log.jsonl 末行 + B站列表核实"
    ledger_upsert(
        "bili_comment_last_action", status,
        op="发评论:%s" % kind,
        verify=verify_txt,
        note="%s%s rpid=%s %s" % (bvid, (" root=%s" % root) if root else "", rpid, note or ""),
    )
    if status == PENDING_VERIFY:
        ledger_upsert(
            "bili_comment_pending_verify",
            json.dumps({"kind": kind, "bvid": bvid, "root": root, "rpid": rpid},
                       ensure_ascii=False),
            op="未决：禁止自动重试",
            verify="需下一轮 verify 复核",
            note=("等待复核 " + (note or "")),
        )
    elif status in (VERIFIED, PRE_EXIST):
        cur = None
        try:
            if LEDGER_DIR not in sys.path:
                sys.path.insert(0, LEDGER_DIR)
            import action_ledger  # noqa
            cur = action_ledger.get("bili_comment_pending_verify")
        except Exception:
            cur = None
        if cur and str(cur.get("state", "")).strip() not in ("", "none"):
            ledger_upsert("bili_comment_pending_verify", "none",
                          op="未决已消解", verify="B站列表已核实存在", note="%s rpid=%s" % (bvid, rpid))


# ============ 账本流水（沿用原 bili_comment_log.jsonl） ============

def log_append(record: Dict[str, Any]):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print("[warn] 流水写入失败：%s" % e, flush=True)


# ============ B站 查询 ============

def _mid_eq(a, b) -> bool:
    """mid 类型不稳定：B站 有时回 str 有时回 int，统一按字符串比。"""
    if a is None or b is None:
        return False
    return str(a).strip() == str(b).strip()


def _extract_my_replies(resp: Dict[str, Any], text: str, my_mid: int) -> List[Dict[str, Any]]:
    """从评论列表回包里，捞出'我发的、正文匹配'的评论。"""
    out = []
    if not isinstance(resp, dict):
        return out
    pool = []
    pool += (resp.get("replies") or [])
    for top in (resp.get("top_replies") or []):
        pool.append(top)
        pool += (top.get("replies") or [])
    for r in pool:
        if not isinstance(r, dict):
            continue
        mid = (r.get("member") or {}).get("mid")
        msg = ((r.get("content") or {}).get("message")) or ""
        if _mid_eq(mid, my_mid) and text_matches(msg, text):
            out.append(r)
    return out


async def fetch_top_replies(aid: int, cred, text: str, my_mid: int):
    """顶层评论：按时间倒序拉第一页，找我的同文评论。"""
    from bilibili_api import comment
    from bilibili_api.comment import CommentResourceType, OrderType
    resp = await comment.get_comments(
        oid=aid, type_=CommentResourceType.VIDEO, page_index=1,
        order=OrderType.TIME, credential=cred,
    )
    return _extract_my_replies(resp, text, my_mid)


async def fetch_sub_replies(aid: int, root: int, cred, text: str, my_mid: int, page_size: int = 20):
    """楼中楼：拉 root 下子评论，找我的同文回复。"""
    from bilibili_api import comment
    from bilibili_api.comment import CommentResourceType
    c = comment.Comment(aid, CommentResourceType.VIDEO, root, credential=cred)
    resp = await c.get_sub_comments(page_index=1, page_size=page_size)
    return _extract_my_replies(resp, text, my_mid)


async def lookup(kind: str, aid: int, text: str, cred, my_mid: int, root: Optional[int] = None):
    """统一查询入口。返回 (found_reply | None, query_ok: bool)。

    query_ok=False 表示**查询本身**没成功（网络/接口异常）——此时不能推断'不存在'。
    """
    try:
        if kind == "reply" and root:
            hits = await fetch_sub_replies(aid, root, cred, text, my_mid)
        else:
            hits = await fetch_top_replies(aid, cred, text, my_mid)
        return (hits[0] if hits else None), True
    except Exception as e:
        print("[warn] verify 查询异常：%s: %s" % (type(e).__name__, e), flush=True)
        return None, False


async def verify_with_retry(kind, aid, text, cred, my_mid, root=None,
                            attempts: int = 2, delay: float = 2.5, looker=None):
    """复核：给 B站 列表一点同步时间，最多查 attempts 次。

    返回 (found_reply | None, query_ok: bool)
    query_ok=False 只在**所有**尝试都异常时成立。
    """
    looker = looker or lookup
    last_ok = False
    for i in range(attempts):
        if i > 0 and delay > 0:
            await asyncio.sleep(delay)
        hit, ok = await looker(kind, aid, text, cred, my_mid, root)
        if hit:
            return hit, True
        last_ok = last_ok or ok
    return None, last_ok


# ============ 主流程 ============

async def run_send(kind: str, bvid: str, text: str, root: Optional[int] = None,
                   dry: bool = False, verify_attempts: int = 2, verify_delay: float = 2.5,
                   sender=None, looker=None) -> Dict[str, Any]:
    """执行一次完整的发送动作。

    sender / looker 可注入（测试用）；默认走真实 bilibili_api。
    """
    from bilibili_api import comment, video
    from bilibili_api.comment import CommentResourceType

    cred, ck = load_cred()
    my_mid = int(ck.get("dedeuserid") or 0)

    v = video.Video(bvid=bvid, credential=cred)
    aid = v.get_aid()
    if hasattr(aid, "__await__"):
        aid = await aid

    result: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "bvid": bvid, "aid": str(aid), "mode": kind, "root": root,
        "text": text, "text_fp": text_fingerprint(text),
        "rpid": None, "code": None, "state": None,
        "parsed_mentions": [], "status": None,
        "note": "", "attempts": 0, "verify": "",
    }

    # ---------- 1) precheck：真相源是 B站 自己 ----------
    looker = looker or lookup
    pre_hit, pre_ok = await looker(kind, aid, text, cred, my_mid, root)

    result["precheck_ok"] = pre_ok
    if pre_hit:
        result["rpid"] = pre_hit.get("rpid")
        result["status"] = PRE_EXIST
        result["note"] = "precheck 命中：B站 已存在同文评论，未发送（幂等）"
        result["verify"] = "precheck 列表核实"
        return _finish(result, dry=dry)

    if dry:
        result["status"] = DRY_RUN
        result["note"] = "DRY_RUN：precheck 未命中，未发送"
        return _finish(result, dry=True)

    # ---------- 2) 写账（先记后做） ----------
    ledger_upsert("bili_comment_last_action", "INTENT",
                  op="发评论:%s" % kind, verify="待回填",
                  note="%s%s fp=%s" % (bvid, (" root=%s" % root) if root else "", result["text_fp"]))

    # ---------- 3) send ----------
    send_error = None
    resp = None
    try:
        if sender is None:
            resp = await comment.send_comment(
                text=text, oid=aid, type_=CommentResourceType.VIDEO,
                root=root, parent=None, credential=cred,
            )
        else:
            resp = await sender(text=text, oid=aid, type_=CommentResourceType.VIDEO,
                                root=root, parent=None, credential=cred)
    except Exception as e:
        send_error = "%s: %s" % (type(e).__name__, e)

    result["attempts"] = 1

    code = None
    rpid = None
    reply = {}
    members = []
    if isinstance(resp, dict):
        code = resp.get("code")
        data = resp.get("data") or {}
        if isinstance(data, dict):
            reply = data.get("reply") or {}
            if not isinstance(reply, dict):
                reply = {}
            rpid = data.get("rpid") or reply.get("rpid")
    result["code"] = code
    result["rpid"] = rpid
    result["state"] = reply.get("state") if isinstance(reply, dict) else None
    members = ((reply.get("content") or {}).get("members")) if isinstance(reply, dict) else []
    result["parsed_mentions"] = [m.get("uname") for m in (members or [])]

    # ---------- 4) 定性 ----------
    # 快路径：回包明确成功
    if code == 0 and rpid and result["state"] == 0:
        result["status"] = VERIFIED
        result["note"] = "send 回包明确成功"
        result["verify"] = "send 回包自证"
        return _finish(result)

    # 其余一律"存疑"→ 必须 verify，绝不盲发
    if send_error:
        result["note"] = "send 抛异常(%s)，请求可能已到达服务端" % send_error
    elif code is None:
        result["note"] = "send 未抛异常，但回包读不到 code（结果未知，不可当失败）"
    elif code == CODE_DUPLICATE:
        result["note"] = "send 回 12051 重复评论 → 说明同文已存在，需核实"
    elif code == 0:
        result["note"] = "send 回 code=0 但读不到 rpid（回包结构变动）"
    else:
        result["note"] = "send 明确返回失败 code=%s message=%s" % (code, (resp or {}).get("message"))

    hit, q_ok = await verify_with_retry(
        kind, aid, text, cred, my_mid, root,
        attempts=verify_attempts, delay=verify_delay, looker=looker,
    )
    # verify 的查询口径与 precheck 一致
    if hit:
        result["rpid"] = hit.get("rpid")
        result["status"] = VERIFIED
        result["verify"] = "verify 列表核实（首发回包异常，复核确认）"
        result["note"] = result["note"] + " → verify 已找到，判定 VERIFIED"
        return _finish(result)

    # verify 没找到：区分「明确失败」与「状态不明」
    if not q_ok:
        result["status"] = PENDING_VERIFY
        result["verify"] = "verify 查询失败，无法判定"
        result["note"] = result["note"] + " → verify 查询也失败，状态不明"
    elif send_error or code is None or code == 0 or code == CODE_DUPLICATE:
        result["status"] = PENDING_VERIFY
        result["verify"] = "verify 列表未见，但发送侧结果不明确"
        result["note"] = result["note"] + " → verify 未见，禁止盲重试"
    else:
        result["status"] = RETRYABLE
        result["verify"] = "verify 列表未见 + 服务端明确报错"
        result["note"] = result["note"] + " → 确认无副作用，可安全重试"
    return _finish(result)


def _finish(result: Dict[str, Any], dry: bool = False) -> Dict[str, Any]:
    """落账 + 返回。"""
    print("STATUS=%s code=%s rpid=%s" % (result["status"], result.get("code"), result.get("rpid")), flush=True)
    print("NOTE=%s" % result.get("note"), flush=True)
    if dry:
        print("(DRY_RUN：只读，未发送、未写账、未进流水)", flush=True)
    else:
        log_append(result)
        ledger_record(result["mode"], result["bvid"], result["status"],
                      rpid=result.get("rpid"), note=result.get("note"), root=result.get("root"))
        print("JSON=" + json.dumps(result, ensure_ascii=False), flush=True)
    return result


def exit_code(result: Dict[str, Any]) -> int:
    return EXIT_CODE.get(result.get("status"), 2)
