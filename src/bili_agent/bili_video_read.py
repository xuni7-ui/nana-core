#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C.5 第一阶段 · B站视频只读理解最小闭环

    当前 @ 事件  →  当前视频 BVID  →  视频信息 / 字幕  →  理解

只走这一条链，做完就停：
  * 单视频、串行、一次性；不循环、不爬取、不扩大请求
  * **不写 L2 / 不落记忆 / 不建新层 / 不碰发送与状态机**
  * 不写 bili_event_state.json、不写 bili_comment_log.jsonl、不写 Ledger
  * 全程只读；无字幕就如实报"无字幕"，绝不编造字幕内容

用法：
    python3 bili_video_read.py                       # 自动取「最新一条 @ 事件」的 BVID
    python3 bili_video_read.py --bvid BV1xxxxxxxxx    # 指定视频
    python3 bili_video_read.py --event-key at:1:123   # 指定去重表里的事件键
    python3 bili_video_read.py --no-llm               # 只抓素材，不调 LLM
    python3 bili_video_read.py --json                 # 只输出结果 JSON
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time

sys.path.insert(0, "/root/.nana_secrets")
import bili_send_core as core            # noqa: E402  复用凭据读取（同源，不另造）

STATE_PATH = "/root/.nana_secrets/bili_event_state.json"
EVENT_LOG = "/root/.nana_secrets/bili_event_log.jsonl"
SUBTITLE_MAX_CHARS = 4000                # 字幕正文截断上限（防上下文膨胀）
OVERALL_TIMEOUT = 90                     # 整体硬超时（秒）
FETCH_HEADERS = {"Referer": "https://www.bilibili.com/"}

# --- C.5 第二阶段：无字幕时的最小证据兜底（单视频 · 单次 · 不翻页） ---
DANMAKU_MAX = 200                        # 弹幕最多取几条（仅第0段，前6分钟）
DANMAKU_ITEM_CHARS = 40                  # 单条弹幕截断
COMMENT_MAX = 20                         # 热门评论最多取几条（仅首页）
COMMENT_ITEM_CHARS = 80                  # 单条评论截断

# LLM 只允许写这 3 个白名单字段
READ_KEYS = ("summary", "keywords", "evidence")
EVIDENCE_OK = ("sufficient", "insufficient")


# ------------------------------------------------------------
#  1) 事件 → BVID（只读去重表，不写）
# ------------------------------------------------------------
def pick_event(state_path: str, event_key: str | None) -> dict:
    with open(state_path, encoding="utf-8") as f:
        st = json.load(f)
    seen, order = st.get("seen") or {}, st.get("order") or []
    if event_key:
        rec = seen.get(event_key)
        if not rec:
            raise SystemExit("找不到事件键：%s" % event_key)
        return {"eid": event_key, **rec}
    # 默认：order 里最后一条 at 通道事件（即"当前 @ 事件"）
    for eid in reversed(order):
        rec = seen.get(eid) or {}
        if rec.get("channel") == "at":
            return {"eid": eid, **rec}
    for eid in reversed(order):        # 没有 at 就退回最新任意事件
        return {"eid": eid, **(seen.get(eid) or {})}
    raise SystemExit("去重表里没有任何事件")


# ------------------------------------------------------------
#  2) 视频信息 + 字幕（只读）
# ------------------------------------------------------------
def message_from_log(eid: str) -> str:
    """从事件流水里回捞这条事件的评论正文（只读；流水里 kind=event 的记录带 message）。"""
    try:
        with open(EVENT_LOG, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-400:]
    except Exception:
        return ""
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("kind") == "event" and rec.get("eid") == eid:
            return (rec.get("message") or "").strip()
    return ""


async def read_video(bvid: str) -> dict:
    from bilibili_api import video
    from bilibili_api.utils.network import Api

    cred, _ck = core.load_cred()
    v = video.Video(bvid=bvid, credential=cred)

    info = await v.get_info() or {}
    pages = info.get("pages") or []
    cid = (pages[0].get("cid") if pages else None) or info.get("cid")

    out = {
        "bvid": bvid,
        "aid": info.get("aid"),
        "cid": cid,
        "title": (info.get("title") or "").strip(),
        "up": ((info.get("owner") or {}).get("name") or "").strip(),
        "duration": info.get("duration"),
        "tname": (info.get("tname") or "").strip(),
        "pubdate": info.get("pubdate"),
        "desc": (info.get("desc") or "").strip()[:500],
        "stat": {k: (info.get("stat") or {}).get(k)
                 for k in ("view", "like", "reply", "danmaku")},
        "subtitle_lan": None,
        "subtitle_text": "",
        "subtitle_note": "",
    }

    # ---- 字幕：有就抓，没有就如实记"无" ----
    if not cid:
        out["subtitle_note"] = "拿不到 cid → 跳过字幕"
        return out
    try:
        pi = await v.get_player_info(cid=cid) or {}
        subs = ((pi.get("subtitle") or {}).get("subtitles") or [])
    except Exception as e:
        out["subtitle_note"] = "字幕列表读取失败：%s: %s" % (type(e).__name__, e)
        return out

    if not subs:
        out["subtitle_note"] = "该视频无字幕（CC/AI 字幕列表为空）"
        return out

    s0 = subs[0] or {}
    url = (s0.get("subtitle_url") or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    out["subtitle_lan"] = s0.get("lan_doc") or s0.get("lan")
    if not url:
        out["subtitle_note"] = "字幕条目存在但无 subtitle_url"
        return out
    try:
        raw = await Api(url=url, method="GET").request(raw=True)
        body = (raw or {}).get("body") or []
        text = "".join((seg.get("content") or "") for seg in body if isinstance(seg, dict))
        text = re.sub(r"\s+", "", text)
        if len(text) > SUBTITLE_MAX_CHARS:
            text = text[:SUBTITLE_MAX_CHARS] + "……(已截断)"
        out["subtitle_text"] = text
        out["subtitle_note"] = "已抓取字幕 %d 字" % len(text)
    except Exception as e:
        out["subtitle_note"] = "字幕正文拉取失败：%s: %s" % (type(e).__name__, e)
    return out


# ------------------------------------------------------------
#  2.5) C.5 第二阶段 · 无字幕兜底素材（弹幕 + 热门评论，均绑定当前 cid/aid）
#       规则：单视频、单次、串行；每源只发一次请求、不翻页；空就是空。
# ------------------------------------------------------------
async def fetch_fallback_material(bvid: str, aid, cid) -> dict:
    """字幕为空时，取当前视频的有限公开文本素材。返回结构自带归属信息，便于校验。"""
    from bilibili_api import video, comment

    out = {"bvid": bvid, "aid": aid, "cid": cid,
           "danmaku": [], "comments": [], "note": "", "requests": 0}
    # 归属校验：素材只能挂在当前视频的 aid/cid 上，否则宁可不要
    if not aid or not cid:
        out["note"] = "缺少 aid/cid，无法确认素材归属 → 放弃兜底"
        return out

    cred, _ck = core.load_cred()
    v = video.Video(bvid=bvid, credential=cred)

    # --- 弹幕：显式锁定第 0 段（前 6 分钟），绝不遍历全部分段 ---
    try:
        dms = await v.get_danmakus(cid=cid, from_seg=0, to_seg=0) or []
        out["requests"] += 1
        seen, texts = set(), []
        for d in dms:
            t = re.sub(r"\s+", "", getattr(d, "text", "") or "")
            if not t or t in seen:
                continue
            seen.add(t)
            texts.append(t[:DANMAKU_ITEM_CHARS])
            if len(texts) >= DANMAKU_MAX:
                break
        out["danmaku"] = texts
    except Exception as e:
        out["note"] += "弹幕读取失败：%s: %s；" % (type(e).__name__, e)

    # --- 热门评论：只取首页（order=LIKE），不翻页 ---
    try:
        page = await comment.get_comments(
            aid, comment.CommentResourceType.VIDEO, page_index=1,
            order=comment.OrderType.LIKE, credential=cred) or {}
        out["requests"] += 1
        seen, texts = set(), []
        for r in (page.get("replies") or []):
            t = re.sub(r"\s+", "", ((r.get("content") or {}).get("message") or ""))
            if not t or t in seen:
                continue
            seen.add(t)
            texts.append(t[:COMMENT_ITEM_CHARS])
            if len(texts) >= COMMENT_MAX:
                break
        out["comments"] = texts
    except Exception as e:
        out["note"] += "评论读取失败：%s: %s；" % (type(e).__name__, e)

    if not out["danmaku"] and not out["comments"]:
        out["note"] = (out["note"] or "") + "兜底素材为空（弹幕与评论都没取到）"
    return out


# ------------------------------------------------------------
#  3) 理解（单次 LLM，严格校验；异常 → 明确失败，不编）
# ------------------------------------------------------------
READ_SYSTEM = (
    "你是奈奈的B站视频理解模块。你只做理解，不执行任何操作，"
    "也绝不声称自己看过视频画面（你看不到画面，只能看到标题、简介、字幕文本、"
    "弹幕样本和热门评论样本）。\n"
    "只输出一个 JSON 对象，且只含这 3 个字段：\n"
    '{"summary": 60字以内的中文概括，说明这条视频在讲什么, '
    '"keywords": [3 个关键词], '
    '"evidence": "sufficient" 或 "insufficient"}\n'
    "证据判定规则：\n"
    "1) 只有素材里存在能说明视频内容的实质线索（标题/简介/字幕/弹幕/评论中能看出主题），"
    "evidence 才可为 \"sufficient\"。\n"
    "2) 若素材零散、只有打招呼灌水、与视频内容无关或互相矛盾，evidence 必须为 "
    "\"insufficient\"，且 summary 必须以「证据不足」开头并说明缺什么。\n"
    "3) 严禁在证据不足时编造视频内容。禁止输出任何其他字段。"
)


def _fmt_list(items, empty_txt):
    return " / ".join(items) if items else empty_txt


def build_user_prompt(m: dict, trigger: str = "") -> str:
    dur = m.get("duration") or 0
    try:
        dur_txt = "%d分%d秒" % (int(dur) // 60, int(dur) % 60)
    except Exception:
        dur_txt = str(dur)
    fb = m.get("fallback") or {}
    dms = (fb.get("danmaku") or [])[:DANMAKU_MAX]
    cms = (fb.get("comments") or [])[:COMMENT_MAX]
    return (
        "触发本次理解的评论（姐姐的 @）：%s\n"
        "视频标题：%s\n"
        "UP主：%s\n"
        "时长：%s\n"
        "分区：%s\n"
        "简介：%s\n"
        "字幕（可能为空）：%s\n"
        "弹幕样本（可能为空，共%d条）：%s\n"
        "热门评论样本（可能为空，共%d条）：%s"
    ) % (trigger or "（无）", m.get("title") or "无", m.get("up") or "未知", dur_txt,
         m.get("tname") or "未知", m.get("desc") or "无",
         m.get("subtitle_text") or "（无字幕）",
         len(dms), _fmt_list(dms, "（无）"),
         len(cms), _fmt_list(cms, "（无）"))


def parse_read(text: str) -> dict:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        obj = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            raise ValueError("LLM 输出不含 JSON 对象：%r" % (text or "")[:120])
        obj = json.loads(m.group(0))
    if not isinstance(obj, dict) or not isinstance(obj.get("summary"), str):
        raise ValueError("理解结果结构不合规：%s" % sorted(obj) if isinstance(obj, dict) else obj)
    ev = str(obj.get("evidence") or "").strip().lower()
    if ev not in EVIDENCE_OK:
        raise ValueError("evidence 字段不合规（须为 %s，实为 %r）" % (EVIDENCE_OK, obj.get("evidence")))
    kw = obj.get("keywords")
    if not isinstance(kw, list):
        kw = []
    return {"summary": obj["summary"].strip(),
            "keywords": [str(x) for x in kw][:3],
            "evidence": ev}


# ------------------------------------------------------------
#  主流程
# ------------------------------------------------------------
async def run(bvid: str | None, event_key: str | None, use_llm: bool,
              use_fallback: bool = True) -> dict:
    t0 = time.time()
    ev = {}
    if not bvid:
        ev = pick_event(STATE_PATH, event_key)
        bvid = ev.get("bvid")
        if not bvid:
            raise SystemExit("事件 %s 里没有 bvid" % ev.get("eid"))
    if not re.fullmatch(r"BV[0-9A-Za-z]+", bvid):
        raise SystemExit("BVID 形状不合法：%r" % bvid)

    result = {"ok": False, "event": {k: ev.get(k) for k in
              ("eid", "channel", "author_name", "message", "status", "ctime")} if ev else None,
              "bvid": bvid}
    if ev and not result["event"].get("message"):
        result["event"]["message"] = message_from_log(ev.get("eid") or "")

    try:
        material = await read_video(bvid)
    except Exception as e:
        result["error"] = "视频信息读取失败：%s: %s" % (type(e).__name__, e)
        return result

    # ---- C.5 第二阶段：字幕为空 → 单次兜底素材（弹幕+热评，绑定当前 aid/cid）----
    if use_fallback and not (material.get("subtitle_text") or "").strip():
        try:
            material["fallback"] = await fetch_fallback_material(
                bvid, material.get("aid"), material.get("cid"))
        except Exception as e:
            material["fallback"] = {"bvid": bvid, "danmaku": [], "comments": [],
                                    "note": "兜底素材抓取异常：%s: %s" % (type(e).__name__, e)}

    result["material"] = {k: v for k, v in material.items()}
    result["understanding"] = None
    result["understand_error"] = None

    if use_llm:
        try:
            import bili_event_pump as pump      # 复用同一套 LLM 配置（不另造）
            llm = pump._real_llm_factory()
            out = llm(READ_SYSTEM, build_user_prompt(
                material, (result.get("event") or {}).get("message") or ""))
            if asyncio.iscoroutine(out):
                out = await out
            result["understanding"] = parse_read(out)
        except Exception as e:
            result["understand_error"] = "%s: %s" % (type(e).__name__, e)

    result["ok"] = True
    result["elapsed"] = round(time.time() - t0, 2)
    return result


def pretty(r: dict) -> str:
    m = r.get("material") or {}
    lines = []
    lines.append("【C.5 第一阶段 · 视频只读理解】")
    if r.get("event"):
        ev = r["event"]
        lines.append("事件        ：%s（%s · %s）" % (ev.get("eid"), ev.get("channel"),
                                                    ev.get("status")))
        lines.append("触发评论    ：%s" % (ev.get("message") or "（空）"))
    lines.append("BVID        ：%s" % r.get("bvid"))
    if r.get("error"):
        lines.append("✗ 失败      ：%s" % r["error"])
        return "\n".join(lines)
    lines.append("标题        ：%s" % (m.get("title") or "无"))
    lines.append("UP主        ：%s" % (m.get("up") or "未知"))
    lines.append("时长/分区   ：%ss / %s" % (m.get("duration"), m.get("tname") or "无"))
    lines.append("简介        ：%s" % (m.get("desc") or "无"))
    lines.append("播放/点赞   ：%s / %s" % (m.get("stat", {}).get("view"),
                                            m.get("stat", {}).get("like")))
    lines.append("字幕        ：%s" % (m.get("subtitle_note") or "无"))
    fb = m.get("fallback")
    if fb is not None:
        lines.append("兜底素材    ：弹幕%d条 / 热评%d条%s" % (
            len(fb.get("danmaku") or []), len(fb.get("comments") or []),
            ("· " + fb["note"]) if fb.get("note") else ""))
        lines.append("素材归属    ：bvid=%s aid=%s cid=%s" % (fb.get("bvid"), fb.get("aid"), fb.get("cid")))
    u = r.get("understanding")
    if u:
        lines.append("证据等级    ：%s" % u.get("evidence"))
        lines.append("理解        ：%s" % u.get("summary"))
        lines.append("关键词      ：%s" % "、".join(u.get("keywords") or []))
    elif r.get("understand_error"):
        lines.append("✗ 理解失败  ：%s" % r["understand_error"])
    else:
        lines.append("理解        ：（--no-llm，跳过）")
    lines.append("耗时        ：%ss" % r.get("elapsed"))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="C.5 第一阶段：@ 事件 → 视频 → 信息/字幕 → 理解（只读）")
    ap.add_argument("--bvid", default=None)
    ap.add_argument("--event-key", default=None)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-fallback", action="store_true",
                    help="禁用无字幕兜底素材")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=float, default=OVERALL_TIMEOUT)
    args = ap.parse_args()

    try:
        r = asyncio.run(asyncio.wait_for(
            run(args.bvid, args.event_key, not args.no_llm,
                not args.no_fallback), timeout=args.timeout))
    except asyncio.TimeoutError:
        print("ERROR=timeout（%ss）→ 停，不重试" % args.timeout)
        return 3

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(pretty(r))
    return 0 if r.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())
