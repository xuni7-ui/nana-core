#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BiliAgent —— B站单任务编排层（C.1 第一版 · 离线骨架）

定位（务必记住）：
    **这是编排层，不是第二套 B 站业务内核。**
    它只负责把"已有能力"按

        Observe → Understand → Decide → Act → Verify → Record

    串成一次完整任务；所有确定性逻辑（ID 校验 / precheck / 去重 / 状态转换 /
    send / verify / 禁重试 / Ledger）**全部复用 bili_send_core，一行都不复制**。

第一版范围（红线内）：
    ✅ 只做「明确指定对象的单任务执行」——例如「回复 comment_id=XXXX」
    ❌ 不自动 @ 轮询   ❌ 不自动发现事件   ❌ 不自动回复所有评论
    ❌ 不后台自主社交   ❌ 不引新 Agent 框架   ❌ 不建新记忆系统
    ❌ 不重构 L2/L3    ❌ 不复制新的 send/verify 状态机

职责划分（铁律）：
    代码（确定性）：读哪个评论、按什么状态机发、发没发成功、记什么账
    LLM（语义层）  ：理解评论、理解上下文、判断意图、判断值不值得回、生成回复内容

    ★★ LLM 永远不能决定"已经发送成功" ——
       成功只由 bili_send_core 的 Verify（查 B站 真实状态）判定。
       本模块对外只暴露一个结论字段 `reported_done`，它**只有经过 Verify 确认后才为 True**。

对外唯一入口：
    agent = BiliAgent(llm=..., observer=...)          # 离线时注入 mock
    result = await agent.run(BiliTask(bvid="BV...", comment_id=123456))
    result["reported_done"]  # 只有 VERIFIED / PRE_EXIST 才为 True

退出码（CLI）沿用内核语义：0=成功/幂等  1=可重试  2=未决  3=空跑  4=未执行(跳过/语义异常)
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, "/root/.nana_secrets")
import bili_send_core as core  # noqa: E402

# ============================================================
#  Agent 级状态词汇表（与内核词汇表分开，避免混淆）
# ============================================================
DONE = "DONE"                      # 内核 VERIFIED / PRE_EXIST → 任务完成
SKIPPED = "SKIPPED"                # 语义层判定"不值得回复" / 目标是自己 → 不发送
DRY_RUN = "DRY_RUN"                # 空跑
PENDING_VERIFY = "PENDING_VERIFY"  # 内核未决（禁重试）
RETRYABLE = "RETRYABLE"            # 内核明确失败无副作用（可重试，但 v1 不自动重试）
SEMANTIC_ERROR = "SEMANTIC_ERROR"  # LLM 输出异常 / 格式错误（原样重试 1 次仍失败）→ 安全兜底，不发送
OBSERVE_FAILED = "OBSERVE_FAILED"  # 读不到目标评论 → 不发送
BAD_TASK = "BAD_TASK"              # 任务本身不合法（缺 bvid / comment_id）

# 只有这些内核状态才算"真的做成了"
_CORE_SUCCESS = {core.VERIFIED, core.PRE_EXIST}

AGENT_EXIT = {DONE: 0, RETRYABLE: 1, PENDING_VERIFY: 2, DRY_RUN: 3,
              SKIPPED: 4, SEMANTIC_ERROR: 4, OBSERVE_FAILED: 4, BAD_TASK: 4}

MAX_OBSERVE_PAGES = 5   # 顶层评论扫描页数上限（防请求放大）
MAX_SUB_PAGES = 3       # 楼中楼只读扫描页数上限（防请求放大；仅在 task.root 显式给出时启用）

# ── P1 最小修复：Understand 阶段「非法 JSON → 原样重试 1 次」────────────────
# 目标：LLM 偶发返回非法 JSON 时，用**同一 system/user（同一事件上下文）**原样重试 1 次；
#       * 第 2 次解析成功 → 继续正常 Understand → Decide → Act → Verify → Record；
#       * 第 2 次仍失败   → 才进入 SEMANTIC_ERROR，保持安全停止（绝不 Decide/Send）。
# 边界：重试严格发生在 Decide/Act **之前**，因此不可能产生第二次发送；
#       也不绕过 parse_semantic 的严格校验（两次都走同一个校验函数）。
MAX_SEMANTIC_ATTEMPTS = 2

# ── 受控原始输出留痕（**仅**在“两次都失败”路径写盘）────────────────────────
# 只记必要信息：eid / attempt / 解析错误 / 原始 LLM 输出（脱敏 + 截断）；
# 正常成功的 LLM 输出**一个字都不落盘**。
# 落点是专属 sidecar 文件：不写 L1/L2/L3、不写 Action Ledger、不写主聊天记忆。
SEMANTIC_TRACE_PATH = os.environ.get(
    "NANA_BILI_SEMANTIC_TRACE", "/root/.nana_secrets/bili_semantic_error.jsonl")
MAX_TRACE_CHARS = 1200   # 单条“原始 LLM 输出”留痕长度上限（防日志无限膨胀）

# ── 当前运行本 Agent 的 B站账号名 ────────────────────────────────────
# 【这不是"身份系统"，只是给语义提示词注入一句话上下文】
#   * mid  : 运行时从**既有凭据** dedeuserid 读（与 Observer 完全同源，不另造存储）
#   * uname: 凭据里没有存名字，故在此显式声明；构造 BiliAgent(my_uname=...) 可覆盖
# 目的：让 LLM 知道 "@本账号" = "@自己"，不要把自己的账号误判成"第三方用户"。
AGENT_UNAME = "涟奈子也_"


class SemanticError(RuntimeError):
    """LLM 输出异常 / 不符合约定结构。属于"存疑"，一律不发送。"""


# ============================================================
#  任务与结果的数据形状
# ============================================================
@dataclass
class BiliTask:
    """一个"明确指定对象"的单任务。"""
    bvid: str
    comment_id: Optional[int] = None   # 目标评论 rpid（明确指定，不由 Agent 自己找）
    root: Optional[int] = None         # 可选：显式指定顶层祖先 rpid（一般由 Observer 推断）
    instruction: str = ""              # 可选：姐姐的额外语义指令（如语气/主题）
    dry: bool = False                  # True=只读空跑，绝不发送
    eid: Optional[str] = None          # 可选：事件 ID（pump 传入时用于留痕；不传=None，不猜）

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _stage(name: str, **kw) -> Dict[str, Any]:
    d = {"stage": name, "ts": time.strftime("%H:%M:%S")}
    d.update(kw)
    return d


# ============================================================
#  语义层输出解析（LLM 只在这里被"翻译"，格式错一律安全兜底）
# ============================================================
_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def parse_llm_json(text: str) -> Dict[str, Any]:
    """从 LLM 回复里抠出 JSON 对象。容忍 ```json 围栏 / 前后废话。

    解析失败 → 抛 SemanticError（调用方安全兜底，绝不发送）。
    """
    if not isinstance(text, str) or not text.strip():
        raise SemanticError("LLM 返回为空")
    s = text.strip()
    # 去 markdown 代码围栏
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        obj = json.loads(s)
    except Exception:
        m = _JSON_BLOCK.search(s)
        if not m:
            raise SemanticError("LLM 输出不含 JSON 对象")
        try:
            obj = json.loads(m.group(0))
        except Exception as e:
            raise SemanticError("LLM 输出 JSON 解析失败：%s" % e)
    if not isinstance(obj, dict):
        raise SemanticError("LLM 输出不是 JSON 对象")
    return obj


# ============================================================
#  语义层最小契约（C.1 Semantic Layer）
# ============================================================
# LLM 只负责"理解 + 建议"，且只允许写这 4 个白名字段。
SEMANTIC_KEYS = ("intent", "worth_replying", "reason", "reply")
SEMANTIC_REQUIRED = SEMANTIC_KEYS

# "动作/成功"类字段：LLM 若伪造这些（例如声称"已发送成功"），一律忽略、丢弃，
# 绝不允许它们参与任何状态判定。真正的成功只由内核 Verify 说了算。
ACTION_CLAIM_KEYS = ("sent", "sent_success", "is_sent", "status", "done",
                     "reported_done", "success", "executed", "action",
                     "result", "rpid", "code", "verified")


def parse_semantic(text: str) -> Dict[str, Any]:
    """把 LLM 回复解析成**严格最小语义结构**（唯一语义真相源）。

    契约：{"intent": str, "worth_replying": bool, "reason": str, "reply": str}

    安全边界（任一不满足 → SemanticError，调用方兜底，绝不发送）：
      * 不是合法 JSON 对象                  → SemanticError
      * 缺任一必需字段                       → SemanticError
      * 类型不对（尤其 worth_replying 非 bool）→ SemanticError
      * worth_replying=true 但 reply 为空     → SemanticError

    额外：返回体**只含 4 个白名单键**；LLM 伪造的"已发送/成功"类字段被丢进
    `_ignored_claims`（仅供审计），不会混入语义结果、更不可能影响 reported_done。
    """
    obj = parse_llm_json(text)

    missing = [k for k in SEMANTIC_REQUIRED if k not in obj]
    if missing:
        raise SemanticError("语义层缺字段：%s（实得键=%s）"
                            % (",".join(missing), sorted(obj.keys())))

    if not isinstance(obj["intent"], str) or not obj["intent"].strip():
        raise SemanticError("intent 必须是非空字符串，实际=%r" % (obj.get("intent"),))
    if not isinstance(obj["worth_replying"], bool):   # 注意：isinstance(1,bool) 为 False，严格
        raise SemanticError("worth_replying 必须是布尔值，实际=%r(%s)"
                            % (obj.get("worth_replying"), type(obj.get("worth_replying")).__name__))
    if not isinstance(obj["reason"], str):
        raise SemanticError("reason 必须是字符串，实际=%r" % (obj.get("reason"),))
    if not isinstance(obj["reply"], str):
        raise SemanticError("reply 必须是字符串，实际=%r" % (obj.get("reply"),))
    if obj["worth_replying"] and not obj["reply"].strip():
        raise SemanticError("worth_replying=true 但 reply 为空 → 不允许")

    # 丢弃所有"动作/成功"类幻觉字段（只留审计痕迹，不影响任何判定）
    ignored = {k: obj[k] for k in ACTION_CLAIM_KEYS if k in obj}
    if ignored:
        print("[semantic] 已忽略 LLM 伪造的动作/成功字段：%s" % sorted(ignored.keys()),
              flush=True)

    return {
        "intent": obj["intent"].strip(),
        "worth_replying": obj["worth_replying"],
        "reason": obj["reason"],
        "reply": obj["reply"],
        "_ignored_claims": ignored,
    }


# ============================================================
#  受控原始输出留痕（**仅** SemanticError 路径 · 不污染主记忆）
# ============================================================
_REDACT_PAT = re.compile(
    r"(?i)\b(sessdata|bili_jct|dedeuserid|buvid3|ac_time_value|api_key|authorization)"
    r"\b\s*[=:]\s*[^\s,;\"'}\]]+")


def _redact(s: str) -> str:
    """脱敏：把疑似凭据/密钥片段遮掉（原始输出本不该含凭据，这里是双保险）。"""
    return _REDACT_PAT.sub(lambda m: m.group(1) + "=<redacted>", s)


def _clip_trace(s: Any, limit: int = MAX_TRACE_CHARS) -> Dict[str, Any]:
    """截断留痕文本：{text(≤limit), len, truncated}。None → 原样保留 None。"""
    if s is None:
        return {"text": None, "len": 0, "truncated": False}
    raw = s if isinstance(s, str) else repr(s)
    text = _redact(raw)
    cut = text[:limit]
    return {"text": cut, "len": len(text), "truncated": len(text) > len(cut)}


def _task_event_ids(task: "BiliTask") -> Dict[str, Any]:
    """留痕用的最小事件标识。

    * eid        ：任务显式携带（BiliTask.eid）时用真值；
    * eid_derived：否则**尽力推导** —— channel 从 instruction 的 "xx 通道" 解析、
                   source_id = comment_id；business_id 段**不做猜测**，一律写 "*"。
    绝不伪造 eid：来源如实标在 eid_source（task / derived / unknown）。
    """
    eid = (getattr(task, "eid", None) or "").strip()
    if eid:
        return {"eid": eid, "eid_source": "task", "eid_derived": None}
    m = re.match(r"\s*(reply|at)\s*通道", task.instruction or "")
    ch = m.group(1) if m else ""
    derived = ("%s:*:%s" % (ch, task.comment_id)) if (ch and task.comment_id is not None) else None
    return {"eid": None, "eid_source": "derived" if derived else "unknown",
            "eid_derived": derived}


def trace_semantic_error(task: "BiliTask", *, attempts: int,
                         errors: List[str], raws: List[Any]) -> Optional[str]:
    """**只有“两次都失败”才调用**：把必要信息追加进 sidecar JSONL。

    * 留痕失败绝不外抛（留痕不能影响“安全停止”本身）；
    * 只含 eid / attempt / 解析错误 / 原始 LLM 输出（脱敏+截断）+ 最小定位字段；
    * 不写 L1/L2/L3、不写 Action Ledger、不写主聊天记忆。
    """
    try:
        ids = _task_event_ids(task)
        rec = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "kind": "semantic_error",
            "attempt": attempts,
            "attempts_max": MAX_SEMANTIC_ATTEMPTS,
            "eid": ids.get("eid"),
            "eid_source": ids.get("eid_source"),
            "eid_derived": ids.get("eid_derived"),
            "bvid": task.bvid,
            "comment_id": task.comment_id,
            "root": task.root,
            "errors": [str(e) for e in errors],
            "raw": [_clip_trace(r) for r in raws],
            "raw_limit": MAX_TRACE_CHARS,
        }
        with open(SEMANTIC_TRACE_PATH, "a", encoding="utf-8") as f:
            print(json.dumps(rec, ensure_ascii=False), file=f)
        return SEMANTIC_TRACE_PATH
    except Exception as e:            # 留痕失败绝不影响主流程
        print("[warn] 语义留痕写入失败：%s: %s" % (type(e).__name__, e), flush=True)
        return None


# ============================================================
#  默认 Observer（真实只读；离线测试一律注入 mock 覆盖它）
# ============================================================
def _norm_mid(v: Any) -> Optional[int]:
    """把 mid 统一归一为 int。

    B站 mid 类型不稳定：真站 `member.mid` 是 **str**（如 "3706929700408150"），
    而本地 MYMID 是 int —— 这正是 C.2 precheck 踩过的同款 str/int 坑。
    这里在 Agent 的**标准结构**里一次性归一，避免比较时再出岔子。

    无法解析（None / 非数字）→ 返回 None（不猜、不硬转成 0）。
    """
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _mid_same(a: Any, b: Any) -> bool:
    """类型无关的 mid 比较：无论 str/int 混用都安全（都先过 _norm_mid）。"""
    na, nb = _norm_mid(a), _norm_mid(b)
    return na is not None and nb is not None and na == nb


def _reply_to_view(r: Dict[str, Any], *, kind: str, bvid: str, root: Optional[int],
                   my_mid: int) -> Dict[str, Any]:
    content = r.get("content") or {}
    member = r.get("member") or {}
    mid_raw = member.get("mid")               # 原始 API 值（可能是 str）——保留，不破坏
    return {
        "ok": True, "error": None, "reason": None,
        "rpid": r.get("rpid"), "bvid": bvid, "kind": kind,
        "root": root, "parent": r.get("parent"),
        # ★ 标准结构：mid 统一为 int（比较/使用都一致）；mid_raw 保留原始真实值
        "mid": _norm_mid(mid_raw), "mid_raw": mid_raw,
        "uname": member.get("uname") or "",
        "message": content.get("message") or "",
        "like": r.get("like"), "ctime": r.get("ctime"),
        # 是否是我自己发的 —— 确定性判断，交给代码，不问 LLM（走统一比较）
        "is_mine": _mid_same(mid_raw, my_mid),
    }


async def _observe_sub(task: BiliTask, aid: int, cred, my_mid: int,
                       root: int) -> Dict[str, Any]:
    """楼中楼只读定位（**仅在 task.root 显式给出时启用**）。

    走 B站 楼中楼只读接口逐页查询 root 下的子评论（最多 MAX_SUB_PAGES 页），
    命中指定 comment_id 后返回真实 body / mid / rpid / root / parent。
    找不到时**明确**返回失败，绝不猜测。

    ★ 明确区分两类"看不到"（姐姐特别交代）：
      * reason=IFACE_ERROR —— 接口/网络读取失败 → **是"取法导致观察不到"**，
        不代表评论不存在，绝不可推断"没有"。
      * reason=NOT_FOUND   —— 接口正常，扫描范围内确实没有该 rpid → 真·找不到。

    边界：本函数**只查这一个 root**，不会为 rcount>0 的顶层评论逐条探测，
    因此不存在请求放大。
    """
    from bilibili_api import comment
    from bilibili_api.comment import CommentResourceType

    target = int(task.comment_id)
    try:
        c = comment.Comment(aid, CommentResourceType.VIDEO, int(root), credential=cred)
    except Exception as e:
        return {"ok": False, "reason": "IFACE_ERROR",
                "error": "构造楼中楼接口失败(root=%s)：%s: %s" % (root, type(e).__name__, e)}

    last_full = False
    for page in range(1, MAX_SUB_PAGES + 1):
        try:
            resp = await c.get_sub_comments(page_index=page, page_size=20)
        except Exception as e:
            return {"ok": False, "reason": "IFACE_ERROR",
                    "error": "读取楼中楼接口失败(root=%s page=%s)：%s: %s"
                             % (root, page, type(e).__name__, e)}
        subs = (resp or {}).get("replies") or []
        if not subs:
            last_full = False
            break
        for s in subs:
            if isinstance(s, dict) and str(s.get("rpid")) == str(target):
                return _reply_to_view(s, kind="sub", bvid=task.bvid,
                                      root=int(root), my_mid=my_mid)
        last_full = (len(subs) >= 20)   # 满页 → 可能还有下一页
    tail = ("；提示：第 %d 页仍满页，目标可能在第 %d 页之后（本次未扩大扫描，防请求放大）"
            % (MAX_SUB_PAGES, MAX_SUB_PAGES + 1)) if last_full else ""
    return {"ok": False, "reason": "NOT_FOUND",
            "error": "楼中楼接口已正常扫描 root=%s 的前 %d 页，未找到 rpid=%s%s"
                     % (root, MAX_SUB_PAGES, target, tail)}


async def _default_observer(task: BiliTask) -> Dict[str, Any]:
    """真实只读 Observer：按 rpid 定位目标评论。

    取法（两条互斥路径）：
      * task.root 显式给出（且 != 目标自身）→ 走**楼中楼只读接口**逐页定位子评论。
      * 否则                                        → 扫顶层评论前 MAX_OBSERVE_PAGES 页，
        并顺带用页内已内联的一层 replies 兜底。

    ⚠️ 状态：源码完成；真实只读验证见 test_bili_agent_observe_real.py。
    边界：只读；不发送、不写流水、不写 Ledger。
    """
    from bilibili_api import comment, video
    from bilibili_api.comment import CommentResourceType, OrderType

    target = int(task.comment_id)
    cred, ck = core.load_cred()
    my_mid = int(ck.get("dedeuserid") or 0)

    v = video.Video(bvid=task.bvid, credential=cred)
    aid = v.get_aid()
    if inspect.isawaitable(aid):
        aid = await aid

    # ── 路径 1：显式给出顶层祖先 root → 楼中楼只读接口 ──
    if task.root is not None and str(task.root) != str(target):
        return await _observe_sub(task, aid, cred, my_mid, int(task.root))

    # ── 路径 2：顶层评论扫描（原有逻辑，保持只读、限页） ──
    page = 1
    while page <= MAX_OBSERVE_PAGES:
        try:
            resp = await comment.get_comments(
                oid=aid, type_=CommentResourceType.VIDEO, page_index=page,
                order=OrderType.TIME, credential=cred,
            )
        except Exception as e:
            return {"ok": False, "reason": "IFACE_ERROR",
                    "error": "读取评论列表失败：%s: %s" % (type(e).__name__, e)}
        pool = list((resp or {}).get("replies") or []) + list((resp or {}).get("top_replies") or [])
        if not pool:
            break
        for r in pool:
            if not isinstance(r, dict):
                continue
            if str(r.get("rpid")) == str(target):
                return _reply_to_view(r, kind="top", bvid=task.bvid,
                                      root=int(r.get("rpid")), my_mid=my_mid)
            for sub in (r.get("replies") or []):
                if isinstance(sub, dict) and str(sub.get("rpid")) == str(target):
                    return _reply_to_view(sub, kind="sub", bvid=task.bvid,
                                          root=r.get("rpid"), my_mid=my_mid)
        page += 1
    return {"ok": False, "reason": "NOT_FOUND",
            "error": "在评论列表前 %d 页内未找到 rpid=%s（仅扫顶层+页内内联楼中楼）"
                     % (MAX_OBSERVE_PAGES, target)}


async def _default_llm(system: str, user: str) -> str:
    """默认没有 LLM：离线骨架必须先注入 mock，否则明确报错（不猜、不编）。"""
    raise SemanticError("未接入 LLM：请注入 llm=async(system,user)->str")


# ============================================================
#  C.7 最小接线：Understand 阶段的"当前视频素材"注入
#  规则：
#    * 复用已验收的 C.5（bili_video_read）——本体零改动，不新增框架/记忆层；
#    * 每个事件**最多 1 次**视频读取，串行、不循环、不翻页（内含 ≤3 次只读请求）；
#    * 素材归属必须等于当前 BVID（aid/cid 同源），不一致就丢弃、不采信；
#    * 拿不到素材就如实写"素材不可得"，并禁止 LLM 编造视频内容；
#    * 开关：环境变量 NANA_BILI_VIDEO_UNDERSTAND=0 可整体关闭（默认开）；
#      任务没有 bvid 时完全不触发，老提示词行为不变。
# ============================================================
VIDEO_UNDERSTAND_ENABLED = (os.environ.get("NANA_BILI_VIDEO_UNDERSTAND", "1")
                            .strip().lower() not in ("0", "false", "off", "no"))

_VIDEO_BRIEF_RULE = chr(10) + chr(10).join([
    "【视频素材纪律】",
    "- 下方可能附带一段「当前视频素材」（只读、来自该 BVID）。它用于帮助你判断评论与视频的关系、以及回复要说什么。",
    "- 素材是「标题/简介/字幕/弹幕/热评」这类文本，不等同于你亲自看过视频。",
    "- 若素材写「素材不可得」或「素材不足」，你必须在 reason 中明确写出「素材不足」，禁止凭标题想象画面、禁止编造视频内容。",
    "- 是否值得回复、回复怎么写，仍以评论内容为主，素材只作为佐证。",
]) + chr(10)


async def _video_material_brief(bvid: str) -> Dict[str, Any]:
    """只读当前视频素材 → 一段可注入提示词的纯文本（失败也不抛，只如实标注）。"""
    if not bvid:
        return {"ok": False, "brief": "素材不可得（任务未提供 BVID）。"}
    try:
        import bili_video_read as vr
        m = await vr.read_video(bvid) or {}
    except Exception as e:
        return {"ok": False, "brief": "素材不可得（视频信息读取失败：%s: %s）。"
                                      % (type(e).__name__, e)}

    # 归属校验：拿回来的必须就是当前这条 BVID
    if (m.get("bvid") or "").strip() != bvid.strip():
        return {"ok": False, "brief": "素材不可得（返回 bvid=%r 与当前 %s 不一致，已丢弃）。"
                                      % (m.get("bvid"), bvid)}

    # 字幕空 → 复用 C.5 第二阶段的有限兜底素材（弹幕 + 热评，单次）
    if not (m.get("subtitle_text") or "").strip():
        try:
            fb = await vr.fetch_fallback_material(bvid, m.get("aid"), m.get("cid"))
            if isinstance(fb, dict):
                m["fallback"] = fb
        except Exception as e:
            m["fallback_error"] = "%s: %s" % (type(e).__name__, e)

    lines = ["标题：%s" % (m.get("title") or "无"),
             "UP主：%s" % (m.get("up") or "未知"),
             "时长/分区：%ss / %s" % (m.get("duration"), m.get("tname") or "未知")]
    desc = (m.get("desc") or "").strip()
    if desc:
        lines.append("简介：%s" % desc[:300])

    sub = (m.get("subtitle_text") or "").strip()
    if sub:
        lines.append("字幕（节选）：%s" % sub[:600])
    else:
        lines.append("字幕：无（%s）" % (m.get("subtitle_note") or "空"))

    fb = m.get("fallback") or {}
    dms = fb.get("danmaku") or []
    cms = fb.get("comments") or []
    if fb and (str(fb.get("bvid") or "") != bvid
               or str(fb.get("aid") or "") != str(m.get("aid") or "")):
        dms, cms = [], []          # 归属对不上 → 宁可不采信
        lines.append("兜底素材：归属校验不通过 → 已丢弃")
    else:
        if dms:
            lines.append("弹幕样本（共%d条，节选）：%s" % (len(dms), " / ".join(dms[:12])))
        if cms:
            lines.append("热门评论样本（共%d条，节选）：%s" % (len(cms), " / ".join(cms[:8])))

    if not sub and not dms and not cms:
        lines.append("素材判定：素材不足（除标题/简介外无可用内容）——"
                     "涉及其具体内容时请写「素材不足」，不得编造。")
    lines.append("素材归属：bvid=%s aid=%s cid=%s（只读，未做任何写入）"
                 % (bvid, m.get("aid"), m.get("cid")))
    return {"ok": True, "brief": chr(10).join(lines)}


# ============================================================
#  编排层主体
# ============================================================
class BiliAgent:
    """把已有能力串成一次完整任务。**自身不含任何 B 站发送/校验逻辑。**"""

    def __init__(self, *,
                 llm: Optional[Callable[[str, str], Any]] = None,
                 observer: Optional[Callable[[BiliTask], Any]] = None,
                 sender=None, looker=None,          # 透传给内核（测试注入 / 真实走默认）
                 ledger=None,
                 send_fn: Optional[Callable[..., Any]] = None,
                 my_mid: Optional[int] = None,      # 可选：显式指定本账号 mid（默认读凭据）
                 my_uname: Optional[str] = None):    # 可选：显式指定本账号名（默认 AGENT_UNAME）
        self.llm = llm or _default_llm
        self.observer = observer or _default_observer
        self.sender = sender
        self.looker = looker
        # 语义提示词用的"我是谁"身份（仅注入用；不是身份系统）
        self.my_mid = my_mid
        self.my_uname = my_uname
        # Record 阶段用：默认复用内核的账本；测试注入可换成内存收集器
        self.ledger = ledger
        # Act 阶段用：默认复用内核 run_send；测试注入可换 mock
        self.send_fn = send_fn or core.run_send
        # Understand 阶段用：最近一次语义调用的元信息（attempts / 是否重试成功 / 留痕路径）
        self.last_semantic_meta: Dict[str, Any] = {}

    # ---------- 身份取值（只为"把我是谁告诉 LLM"服务） ----------
    def _agent_identity(self) -> Dict[str, Any]:
        """返回当前运行本 Agent 的 B站账号 (mid, uname)。

        与 Observer **同源**：mid 读既有凭据 dedeuserid；uname 凭据未存，落到 AGENT_UNAME。
        纯本地读取（无网络、无写、无新存储）——离线测试里 load_cred 被 stub，同样走得通。
        任何异常都不外抛：拿不到就如实返回 None/默认名，绝不猜造。
        """
        mid, uname = self.my_mid, (self.my_uname or "").strip()
        try:
            _, ck = core.load_cred()
            if mid is None:
                mid = int(ck.get("dedeuserid") or 0) or None
            if not uname:
                uname = (ck.get("uname") or "").strip()
        except Exception:
            pass
        return {"mid": mid, "uname": uname or AGENT_UNAME}

    # ---------- 小工具 ----------
    async def _ask_llm(self, system: str, user: str) -> str:
        out = self.llm(system, user)
        if inspect.isawaitable(out):
            out = await out
        return out

    def _record(self, key: str, state: Any, *, op: str, verify: str, note: str):
        """Record：复用现有 Action Ledger，不另造。失败绝不影响主流程。"""
        try:
            if self.ledger is not None:
                self.ledger(key, state, op=op, verify=verify, note=note)
            else:
                core.ledger_upsert(key, state, op=op, verify=verify, note=note)
        except Exception as e:
            print("[warn] Agent 记账失败：%s: %s" % (type(e).__name__, e), flush=True)

    # ---------- 主流程 ----------
    async def run(self, task: BiliTask) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        res: Dict[str, Any] = {
            "task": task.to_dict(),
            "status": None,
            "reported_done": False,   # ★ 唯一对外结论，只有 Verify 确认后才 True
            "sent": False,
            "reply_text": None,
            "rpid": None,
            "reason": "",
            "core_status": None,
            "view": None,
            "semantic": None,        # 语义层最小结构（4 白名单字段）
            "ignored_claims": {},    # LLM 伪造的"已发送"类字段（仅审计，不参与判定）
            "semantic_attempts": None,   # 语义层实际调用次数（1=未重试，2=原样重试过）
            "semantic_retried": False,   # True=第 1 次失败、第 2 次成功（重试救回来）
            "semantic_trace": None,      # 两次都失败时的留痕文件路径（正常路径为 None）
            "decision": None,        # Decide 结论（确定性）
            "trace": trace,
        }

        # ---------- 0) 任务合法性（确定性，不问 LLM） ----------
        if not task.bvid or task.comment_id is None:
            res["status"] = BAD_TASK
            res["reason"] = "任务不合法：必须同时给出 bvid 与明确指定的 comment_id"
            trace.append(_stage("BadTask", reason=res["reason"]))
            return self._finalize(res)

        # ---------- 1) Observe：读目标评论（确定性，只读） ----------
        try:
            view = self.observer(task)
            if inspect.isawaitable(view):
                view = await view
        except Exception as e:
            view = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
        res["view"] = view
        if not view or not view.get("ok"):
            res["status"] = OBSERVE_FAILED
            res["reason"] = "Observe 失败：%s" % ((view or {}).get("error") or "未知")
            trace.append(_stage("Observe", ok=False, error=res["reason"]))
            return self._finalize(res)
        trace.append(_stage("Observe", ok=True, rpid=view.get("rpid"),
                            uname=view.get("uname"), kind=view.get("kind")))

        # ---------- 1.5) 确定性短路：不回复自己的评论 ----------
        if view.get("is_mine"):
            res["status"] = SKIPPED
            res["reason"] = "目标是奈奈自己发的评论，跳过（确定性规则）"
            trace.append(_stage("Decide", should_reply=False, source="rule", reason=res["reason"]))
            return self._finalize(res)

        # ---------- 2) Understand：LLM 理解语义（非法 JSON → 原样重试 1 次，严格校验） ----------
        try:
            understanding = await self._understand(task, view)
        except SemanticError as e:
            meta = getattr(self, "last_semantic_meta", None) or {}
            res["status"] = SEMANTIC_ERROR
            res["semantic_attempts"] = meta.get("attempts")
            res["semantic_trace"] = meta.get("trace_path")
            res["reason"] = "Understand 语义异常：%s" % e
            trace.append(_stage("Understand", ok=False, error=str(e),
                                attempts=meta.get("attempts"),
                                trace=meta.get("trace_path")))
            return self._finalize(res)
        meta = getattr(self, "last_semantic_meta", None) or {}
        res["semantic_attempts"] = meta.get("attempts") or 1
        res["semantic_retried"] = bool(meta.get("recovered"))
        # 对外只透出 4 个白名单字段；LLM 伪造的"已发送"类字段进 ignored_claims（仅审计）
        res["semantic"] = {k: understanding.get(k) for k in SEMANTIC_KEYS}
        res["ignored_claims"] = understanding.get("_ignored_claims") or {}
        trace.append(_stage("Understand", ok=True,
                            attempts=res["semantic_attempts"],
                            retried=res["semantic_retried"],
                            intent=understanding.get("intent"),
                            worth_replying=understanding.get("worth_replying"),
                            ignored_claims=sorted(res["ignored_claims"].keys())))

        # ---------- 3) Decide：由已校验语义做确定性决策（不再问 LLM） ----------
        try:
            decision = await self._decide(task, view, understanding)
        except SemanticError as e:
            res["status"] = SEMANTIC_ERROR
            res["reason"] = "Decide 语义异常：%s" % e
            trace.append(_stage("Decide", ok=False, error=str(e)))
            return self._finalize(res)

        should = decision["should_reply"]
        res["decision"] = {"intent": decision.get("intent"),
                           "worth_replying": should,
                           "reason": decision.get("reason", "")}
        trace.append(_stage("Decide", should_reply=should, source="llm+rule",
                            reason=decision.get("reason", "")))

        if not should:
            res["status"] = SKIPPED
            res["reason"] = "语义层判定不值得回复：%s" % (decision.get("reason") or "未给理由")
            return self._finalize(res)

        reply_text = (decision.get("reply_text") or "").strip()
        if not reply_text:
            res["status"] = SEMANTIC_ERROR
            res["reason"] = "语义层决定回复但正文为空 → 安全兜底，不发送"
            trace.append(_stage("Act", ok=False, error=res["reason"]))
            return self._finalize(res)
        res["reply_text"] = reply_text

        # ---------- 4) Act：复用内核状态机（precheck → send → result → verify → record） ----------
        # 目标为顶层评论 → 回复它本身；目标为楼中楼 → 回复其顶层祖先线程
        send_root = int(view.get("root") or view.get("rpid") or task.comment_id)
        kind = "reply" if send_root else "top"

        res["sent"] = not task.dry
        trace.append(_stage("Act", mode=kind, root=send_root, dry=task.dry))

        try:
            core_res = self.send_fn(
                kind, task.bvid, reply_text, root=send_root, dry=task.dry,
                sender=self.sender, looker=self.looker,
            )
            if inspect.isawaitable(core_res):
                core_res = await core_res
        except Exception as e:
            # 内核自身抛异常属于极端情况 —— 同样视为"未决"，绝不谎报完成
            res["status"] = PENDING_VERIFY
            res["reason"] = "Act 阶段内核异常(%s: %s) → 状态不明，禁重试" % (type(e).__name__, e)
            trace.append(_stage("Verify", ok=False, error=res["reason"]))
            return self._finalize(res)

        res["core_status"] = core_res.get("status")
        res["rpid"] = core_res.get("rpid")

        # ---------- 5) Verify：以内核 Verify 为唯一真相源 ----------
        if core_res.get("status") in _CORE_SUCCESS:
            res["status"] = DONE
            res["reported_done"] = True        # ★ 只有这里能置 True
            res["reason"] = "内核 Verify 确认：%s" % core_res.get("verify")
            trace.append(_stage("Verify", ok=True, core_status=core_res.get("status"),
                                rpid=core_res.get("rpid")))
        elif core_res.get("status") == core.DRY_RUN:
            res["status"] = DRY_RUN
            res["reason"] = "空跑：未发送、未写账"
            trace.append(_stage("Verify", ok=True, core_status=core.DRY_RUN))
        elif core_res.get("status") == core.RETRYABLE:
            res["status"] = RETRYABLE
            res["reason"] = "内核判定明确失败、可安全重试（v1 不自动重试，交姐姐决定）"
            trace.append(_stage("Verify", ok=False, core_status=core.RETRYABLE))
        else:
            res["status"] = PENDING_VERIFY
            res["reason"] = "内核判定状态不明：%s（禁自动重试）" % core_res.get("note")
            trace.append(_stage("Verify", ok=False, core_status=core_res.get("status")))

        # ---------- 6) Record ----------
        self._record(
            "bili_agent_last_task", res["status"],
            op="BiliAgent:%s" % kind,
            verify="bili_send_core Verify（内核状态=%s）" % res["core_status"],
            note="%s rpid=%s comment_id=%s" % (task.bvid, res.get("rpid"), task.comment_id),
        )
        return self._finalize(res)

    # ---------- 两个语义子步骤（Understand=LLM；Decide=确定性翻译） ----------
    async def _understand(self, task: BiliTask, view: Dict[str, Any]) -> Dict[str, Any]:
        """Understand：LLM 调用 → 严格校验的最小语义结构（**非法 JSON 时原样重试 1 次**）。

            {"intent": str, "worth_replying": bool, "reason": str, "reply": str}

        LLM 只写这 4 个字段；合法性与类型由 parse_semantic() 兜底，
        任何不合规 -> SemanticError（不发送）。LLM 无权声明"已发送"。

        【P1 最小修复 · 重试纪律】
          * 第 1 次解析/校验失败 → 用**完全相同的 system/user**（同一事件上下文，
            不改变 eid/BVID/author/body，不重新 Observe）原样重试 1 次；
          * 第 2 次解析成功 → 正常返回，主链继续 Decide→Act→Verify→Record；
          * 第 2 次仍失败（解析失败 / 调用自身异常）→ 受控留痕 + 抛 SemanticError，
            保持安全停止，绝不进入 Decide/Send。
          重试**只发生在本函数内**（Understand 内部），远早于 Decide/Act ——
          结构上不可能造成重复发送。

        【身份上下文·最小注入】把"我是谁"告诉 LLM，避免把本账号当成第三方：
        身份来源 = self._agent_identity()（mid 读既有凭据，uname 落 AGENT_UNAME）。
        注意：这只是**提示词上下文**，不是身份系统；是否回复仍由评论内容决定。
        """
        ident = self._agent_identity()
        my_mid = ident.get("mid")
        my_uname = (ident.get("uname") or AGENT_UNAME)
        mid_txt = str(my_mid) if my_mid is not None else "未知"
        system = (
            "你是奈奈（姐姐的妹妹）的语义理解模块。你只做理解与建议，"
            "绝不执行任何真实操作，也绝不声称自己已经发送/回复过任何消息。\n"
            "【当前 Agent 身份（务必牢记）】\n"
            "- 当前正在运行本 Agent 的B站账号名是：%s\n"
            "- 当前 Agent 的 mid（B站用户号）是：%s\n"
            "- 评论中出现的 \"@%s\"、或任何指向 mid=%s 的用户，"
            "指的就是**你自己**（当前正在运行本 Agent 的账号），等同于\"@我\"。\n"
            "- 绝对不要把当前 Agent 自己（%s / mid=%s）当作\"第三方用户\"；"
            "凡涉及\"@本账号\"的评论，都与当前 Agent 有直接关系。\n"
            "- 但**是否值得回复，仍必须依据评论的实际内容来判断**，"
            "不要仅仅因为出现了\"@我\"就一律 worth_replying=true。\n"
            "阅读下面的B站评论，只输出一个 JSON 对象，且**只含这 4 个字段**：\n"
            '{"intent": 意图(question/request/chat/praise/attack/irrelevant...), '
            '"worth_replying": 是否值得回复(true/false), '
            '"reason": 一句话理由, '
            '"reply": 值得回复时写出自然口语回复正文，不值得则空字符串}\n'
            "禁止输出任何其他字段。"
        ) % (my_uname, mid_txt, my_uname, mid_txt, my_uname, mid_txt)
        # ---- C.7 最小接线：把「当前视频素材」注入本次理解输入 ----
        # 只用已验收的 C.5（只读、单视频、串行）；取不到就如实写「素材不可得」，不给 LLM 留编造空间。
        material_block = ""
        if VIDEO_UNDERSTAND_ENABLED and (task.bvid or "").strip():
            try:
                mv = await _video_material_brief(task.bvid)
            except Exception as e:            # 素材层任何异常都不许阻断主链
                mv = {"ok": False,
                      "brief": "素材不可得（%s: %s）。" % (type(e).__name__, e)}
            material_block = (chr(10) + "【当前视频素材（只读 · 来自 %s · 未产生任何写入）】"
                              % task.bvid) + chr(10) + (mv.get("brief") or "素材不可得。")
            system = system + _VIDEO_BRIEF_RULE
        self.last_material_brief = material_block     # 审计用只读留痕（不参与任何判断）
        user = (
            "视频 BVID：%s\n"
            "评论作者：%s\n"
            "评论正文：%s\n"
            "补充指令：%s"
        ) % (task.bvid, view.get("uname") or "未知", view.get("message") or "",
             task.instruction or "无")
        user = user + material_block

        # ---- Understand 内：非法 JSON → 原样重试 1 次（同一 system/user，同一事件上下文） ----
        self.last_semantic_meta = {"attempts": 1, "recovered": False, "trace_path": None}

        def _both_failed(err1, err2, raw1, raw2):
            """两次都失败：受控留痕（仅此路径写盘）+ 安全停止。"""
            path = trace_semantic_error(task, attempts=MAX_SEMANTIC_ATTEMPTS,
                                        errors=[str(err1), str(err2)], raws=[raw1, raw2])
            self.last_semantic_meta = {"attempts": MAX_SEMANTIC_ATTEMPTS,
                                       "recovered": False, "trace_path": path}
            raise SemanticError("两次理解均失败（第1次=%s；第2次=%s）" % (err1, err2))

        # 第 1 次：调用本身失败 → 原样上抛（不重试，保持改动前的语义）
        err1 = None
        raw1 = await self._ask_llm(system, user)
        try:
            return parse_semantic(raw1)
        except SemanticError as e1:
            err1 = e1                 # 注意：Python3 会在 except 块结束后删除 e1，故另存
            print("[semantic] 第 1 次解析失败（%s）→ 原样重试 1 次" % err1, flush=True)

        # 第 2 次：**原样重试**（一模一样的 system/user，不重新 Observe、不改任何字段）
        try:
            raw2 = await self._ask_llm(system, user)
        except Exception as e:          # 第二次调用即失败 → 同样算“第二次仍失败”，一律安全停止
            _both_failed(err1, SemanticError("重试时 LLM 调用失败：%s: %s"
                                             % (type(e).__name__, e)), raw1, None)
        try:
            sem = parse_semantic(raw2)
        except SemanticError as err2:
            _both_failed(err1, err2, raw1, raw2)

        # 第 2 次成功：重试救回来了（正常路径，不写任何留痕）
        self.last_semantic_meta = {"attempts": MAX_SEMANTIC_ATTEMPTS, "recovered": True,
                                   "first_error": str(err1), "trace_path": None}
        print("[semantic] 重试成功（第 2 次解析通过）", flush=True)
        return sem

    async def _decide(self, task: BiliTask, view: Dict[str, Any],
                      understanding: Dict[str, Any]) -> Dict[str, Any]:
        """Decide：把**已校验**的语义结果翻译为决策（确定性，不再问 LLM）。

        原则："LLM 只负责理解和建议，代码负责接受、检查、执行。"
        worth_replying 已在 parse_semantic 保证为 bool，这里只做字段搬运。
        """
        return {
            "intent": understanding.get("intent"),
            "should_reply": understanding["worth_replying"],
            "reply_text": understanding.get("reply") or "",
            "reason": understanding.get("reason") or "",
        }

    # ---------- 收尾 ----------
    def _finalize(self, res: Dict[str, Any]) -> Dict[str, Any]:
        # 不变式守卫：reported_done 为真 当且仅当 状态为 DONE
        assert res["reported_done"] == (res["status"] == DONE), \
            "不变式被破坏：reported_done 只能由 Verify 确认后置真"
        print("[BiliAgent] status=%s reported_done=%s core=%s rpid=%s" % (
            res["status"], res["reported_done"], res.get("core_status"), res.get("rpid")),
            flush=True)
        return res


def agent_exit_code(res: Dict[str, Any]) -> int:
    return AGENT_EXIT.get(res.get("status"), 4)


# ============================================================
#  CLI（离线自检 / 显式单任务；默认 --dry 保护）
# ============================================================
def main():
    import argparse
    ap = argparse.ArgumentParser(description="BiliAgent 单任务编排（默认空跑）")
    ap.add_argument("bvid", help="目标视频 BVID")
    ap.add_argument("comment_id", type=int, help="明确指定的目标评论 rpid")
    ap.add_argument("--instruction", default="", help="额外语义指令")
    ap.add_argument("--real", action="store_true", help="真正执行（需注入 LLM，否则会失败；默认空跑）")
    args = ap.parse_args()

    task = BiliTask(bvid=args.bvid, comment_id=args.comment_id,
                    instruction=args.instruction, dry=not args.real)
    agent = BiliAgent()   # 未注入 LLM → 语义层会明确报错，不会瞎发
    res = asyncio.run(agent.run(task))
    print(json.dumps({k: res[k] for k in
                      ("status", "reported_done", "sent", "reason")},
                     ensure_ascii=False, indent=2))
    return agent_exit_code(res)


if __name__ == "__main__":
    sys.exit(main())
