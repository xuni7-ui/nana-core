#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C.4 第一阶段 · B站事件泵（单次运行；由**已有 scheduler** 周期拉起）

     scheduler（AstrBot cron，60s）
        ↓  子进程（本脚本）—— 网络 IO 全程在独立进程，**不持有主聊天 memory 写锁**
     只读拉事件（reply / @）
        ↓
     事件去重（B站真实 ID：business_id + rpid）   ← 同一事件被轮询 100 次也只进 Agent 一次
        ↓
     BiliAgent: Observe → Understand → Decide → Act → Verify → Record
        ↓                （不值得行动 ──→ 直接 Record）

复用而非重建：
    发送 / precheck / verify / 禁盲重试 → bili_send_core.py（C.2 状态机，一行不复制）
    编排 Observe~Record               → bili_agent.py（C.1 骨架）
    现在是什么状态                     → 现有 Action Ledger
    发送流水                          → 现有 bili_comment_log.jsonl

安全红线：
  * 同一事件只进 Agent 一次（先入账再行动）
  * 默认 observe（空跑）：全程只读，永不发送；只有显式 act 才可能有 1 次真实发送
  * 一轮最多 budget 次真实 Act（默认 1）
  * 任何不确定（读取失败 / 结构异常 / 缺 ID / 未决）→ **停，不重试**
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, "/root/.nana_secrets")
import bili_send_core as core          # noqa: E402
import bili_agent as agent_mod         # noqa: E402
import bili_event_source as src        # noqa: E402

STATE_PATH = "/root/.nana_secrets/bili_event_state.json"
EVENT_LOG = "/root/.nana_secrets/bili_event_log.jsonl"
LOCK_PATH = "/root/.nana_secrets/.bili_event_pump.lock"

MODES = ("observe", "act")
DEFAULT_MODE = "observe"        # ★ 默认只会看，不会发
MAX_SEEN = 300                  # 去重表上限（超出淘汰最旧）
REPLAY_WINDOW_SEC = 1800        # C.7.1：OBSERVED_DRY 在 act 下允许复活的时效窗（30 分钟）；超出不复
DEFAULT_MAX_EVENTS = 5          # 单轮最多处理几条新事件
DEFAULT_BUDGET = 1              # 单轮最多几次真实 Act


# ============================================================
#  状态 / 流水
# ============================================================
def load_state(path: str = STATE_PATH) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            st = json.load(f)
        if isinstance(st, dict) and isinstance(st.get("seen"), dict):
            st.setdefault("version", 1)
            st.setdefault("mode", DEFAULT_MODE)
            st.setdefault("order", [])
            return st
    except FileNotFoundError:
        pass
    except Exception as e:
        print("[warn] 事件状态读取失败(%s)，按空表处理" % e, flush=True)
    return {"version": 1, "mode": DEFAULT_MODE, "seen": {}, "order": []}


def save_state(st: Dict[str, Any], path: str = STATE_PATH) -> None:
    """原子写（tmp + os.replace），中途崩掉不会留下半个坏文件。"""
    st["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _mark(st: Dict[str, Any], ev: Dict[str, Any], status: str, **extra) -> None:
    eid = ev["eid"]
    rec = st["seen"].get(eid) or {}
    rec.update({
        "status": status,
        "channel": ev["channel"],
        "bvid": ev["bvid"],
        "source_id": ev["source_id"],
        "root_id": ev.get("root_id") or 0,
        "author_mid": ev.get("author_mid"),
        "author_name": ev.get("author_name"),
        "msgfeed_id": ev.get("msgfeed_id"),
        "ctime": ev.get("ctime"),
        "first_seen": rec.get("first_seen") or time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    if rec.get("first_seen") == rec.get("last_seen"):
        rec["times_seen"] = 1
    else:
        rec["times_seen"] = int(rec.get("times_seen") or 1) + 1
    rec.update(extra)
    st["seen"][eid] = rec
    if eid not in st["order"]:
        st["order"].append(eid)
    while len(st["order"]) > MAX_SEEN:
        old = st["order"].pop(0)
        st["seen"].pop(old, None)


# ---- C.7.1：OBSERVED_DRY 在 act 下的受控复活（只读判定，不改任何状态）----
def _parse_ts(v: Any) -> Optional[float]:
    """把事件的 ctime（秒级时间戳）或 first_seen（'YYYY-mm-dd HH:MM:SS'）解析为 epoch 秒。
    任何无法可靠解析的情况（None / 空 / 非数非日期 / 非正数）→ 返回 None（fail-closed）。"""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        ts = float(v)
        return ts if ts > 0 else None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            ts = float(s)
            return ts if ts > 0 else None
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return time.mktime(time.strptime(s, fmt))
            except ValueError:
                continue
    return None


def _replayable(rec: Optional[Dict[str, Any]], mode: str, now: float) -> bool:
    """判据：仅 act 模式下、「OBSERVED_DRY」状态、且在时效窗内的旧事件可重新进入处理链。
    * 非 act（observe）→ False（不重复拾取）
    * 非 OBSERVED_DRY → False（其它终态继续阻塞）
    * 时间锚点：ctime 优先，无效回落 first_seen；两者都解析失败 → False（fail-closed）
    * age = now - ts，要求 0 <= age <= REPLAY_WINDOW_SEC；时间在未来（脏数据）→ False"""
    if mode != "act" or not isinstance(rec, dict):
        return False
    if rec.get("status") != "OBSERVED_DRY":
        return False
    ts = _parse_ts(rec.get("ctime"))
    if ts is None:
        ts = _parse_ts(rec.get("first_seen"))
    if ts is None:
        return False
    age = now - ts
    return 0 <= age <= REPLAY_WINDOW_SEC


def append_log(rec: Dict[str, Any]) -> None:
    rec.setdefault("ts", time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        with open(EVENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        print("[warn] 事件流水写入失败：%s" % e, flush=True)


def ledger_poll(state: str, *, note: str, verify: str) -> None:
    """只加 **一个** 账本键（不膨胀）：泵最近一次轮询结果。失败绝不影响主流程。"""
    core.ledger_upsert("bili_event_pump_last_poll", state,
                       op="B站事件轮询(pump)", verify=verify, note=note)


# ============================================================
#  Agent 调用（全部复用 C.1 / C.2，不新增逻辑）
# ============================================================
def _real_llm_factory() -> Callable[[str, str], str]:
    """真实 LLM：从既有 cmd_config.json 读 deepseek 配置（与 C.1 真实测试同源）。"""
    import ast

    c = json.load(open("/AstrBot/data/cmd_config.json", encoding="utf-8-sig"))
    source = {p.get("provider"): p for p in c["provider_sources"]}.get("deepseek")
    if not source:
        raise RuntimeError("未找到 deepseek provider 配置")
    k = source["key"]
    if isinstance(k, str):
        try:
            k = ast.literal_eval(k)
        except Exception:
            k = [k]
    api_key = k[0] if isinstance(k, list) else k
    from openai import OpenAI
    cli = OpenAI(api_key=api_key, base_url=source["api_base"], timeout=90)
    model = "deepseek-flash"

    def _llm(system: str, user: str) -> str:
        r = cli.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.2, max_tokens=800)
        return (r.choices[0].message.content or "").strip()

    return _llm


def _real_observer_factory():
    return agent_mod._default_observer


async def run_agent_for_event(ev: Dict[str, Any], *, mode: str, llm, observer, send_fn,
                              ledger, extra_instruction: str = "") -> Dict[str, Any]:
    """把事件变成一个"明确指定对象"的单任务，交给 C.1 编排层跑完整闭环。"""
    task = agent_mod.BiliTask(
        bvid=ev["bvid"],
        comment_id=src.target_comment_id(ev),
        root=src.target_root(ev),
        instruction=extra_instruction or ("%s 通道收到的%s事件" % (
            ev["channel"], "回复" if ev["channel"] == src.CH_REPLY else "@")),
        dry=(mode != "act"),          # ★ observe 模式 = 空跑，永不发送
    )
    agent = agent_mod.BiliAgent(llm=llm, observer=observer, send_fn=send_fn, ledger=ledger)
    return await agent.run(task)


_STATE_MAP = {
    agent_mod.DONE: "DONE",
    agent_mod.SKIPPED: "SKIPPED",
    agent_mod.DRY_RUN: "OBSERVED_DRY",
    agent_mod.PENDING_VERIFY: "PENDING_VERIFY",
    agent_mod.RETRYABLE: "RETRYABLE",
    agent_mod.SEMANTIC_ERROR: "SEMANTIC_ERROR",
    agent_mod.OBSERVE_FAILED: "OBSERVE_FAILED",
    agent_mod.BAD_TASK: "BAD_TASK",
}


# ============================================================
#  主流程（单次运行）
# ============================================================
async def run_once(*, mode: Optional[str] = None, budget: int = DEFAULT_BUDGET,
                   max_events: int = DEFAULT_MAX_EVENTS, baseline: bool = False,
                   state_path: str = STATE_PATH,
                   do_log: bool = True, do_ledger: bool = True,
                   fetch: Optional[Callable] = None, my_mid: Optional[int] = None,
                   llm=None, observer=None, send_fn=None,
                   ledger=None) -> Dict[str, Any]:
    st = load_state(state_path)
    eff_mode = (mode or st.get("mode") or DEFAULT_MODE).strip().lower()
    if eff_mode not in MODES:
        eff_mode = DEFAULT_MODE

    # ---- 事件源（只读；网络在独立进程里，从不持有任何 memory 锁） ----
    if fetch is None:
        cred, ck = core.load_cred()
        my_mid = int(ck.get("dedeuserid") or 0)
        _cred = cred

        async def fetch(ch):                       # noqa: F811
            return await src.fetch_channel(_cred, ch)

    raw: Dict[str, Any] = {}
    for ch in src.CHANNELS:
        try:
            raw[ch] = await fetch(ch)
        except Exception as e:
            raw[ch] = {"ok": False, "error": "%s: %s" % (type(e).__name__, e), "items": []}

    coll = src.collect(raw, my_mid=my_mid)
    if not coll["ok"]:
        note = "；".join(coll["errors"])
        if do_log:
            append_log({"kind": "poll_error", "mode": eff_mode, "error": note})
        if do_ledger:
            ledger_poll("ERROR", note=note, verify="未读到事件源 → 本轮不处理任何事件")
        return {"ok": False, "mode": eff_mode, "error": note, "new": [], "processed": [],
                "exit": 3}

    events: List[Dict[str, Any]] = coll["events"]
    for b in coll["bad"]:
        if do_log:
            append_log({"kind": "bad_event", "channel": b["channel"],
                        "msgfeed_id": b["id"], "reason": "缺少稳定 ID 关键字段 → 跳过（不猜）"})

    if baseline:
        added = 0
        for ev in events:
            if ev["eid"] not in st["seen"]:
                _mark(st, ev, "baseline")
                added += 1
                if do_log:
                    append_log({"kind": "baseline", "eid": ev["eid"],
                                "channel": ev["channel"], "bvid": ev["bvid"],
                                "source_id": ev["source_id"], "message": ev["message"][:60]})
        save_state(st, state_path)
        if do_ledger:
            ledger_poll("BASELINE",
                        note="登记在册 %d 条历史事件（已处理过，不再进 Agent）" % added,
                        verify="事件状态文件 bili_event_state.json")
        return {"ok": True, "mode": eff_mode, "baseline": added, "new": [], "processed": [],
                "exit": 0}

    # ---- 去重闸门（C.7.1 · A2）----
    # fresh = 本轮未见过的新事件；replay = OBSERVED_DRY 且满足复活条件的旧事件。
    # 规则：本轮存在 fresh → 只处理 fresh；本轮没有 fresh → 才允许 replay。
    #       replay 绝不抢 fresh 的 act budget，也不新增 budget（沿用既有 budget 语义）。
    fresh = [e for e in events if e["eid"] not in st["seen"]]
    if fresh:
        new = fresh
    else:
        now = time.time()
        new = [e for e in events
               if _replayable(st["seen"].get(e["eid"]), eff_mode, now)]
    new.sort(key=lambda e: (e.get("ctime") or 0))
    if do_log:
        append_log({"kind": "poll", "mode": eff_mode, "alive": len(events),
                    "new": len(new), "budget": budget, "max_events": max_events})

    if llm is None and new:
        llm = _real_llm_factory()
    if observer is None:
        observer = _real_observer_factory()

    acted = 0
    processed: List[Dict[str, Any]] = []
    for ev in new:
        if len(processed) >= max_events:
            break
        # 预算只约束**真实 Act**；observe 模式永不发送，因此不受预算门限制
        if eff_mode == "act" and acted >= budget:
            break                      # 预算用完 → 剩余**不登记**，留给下一轮
        # ★ 先入账再行动：同一事件被轮询 100 次，也只会有这一次进入 Agent
        _mark(st, ev, "inflight")
        save_state(st, state_path)

        try:
            res = await run_agent_for_event(ev, mode=eff_mode, llm=llm,
                                           observer=observer, send_fn=send_fn,
                                           ledger=ledger)
        except Exception as e:                      # 极端异常：视为未决，绝不重试
            res = {"status": agent_mod.PENDING_VERIFY,
                   "reason": "pump 内部异常(%s: %s) → 状态不明，禁重试" % (type(e).__name__, e),
                   "reported_done": False, "rpid": None}

        st_status = _STATE_MAP.get(res.get("status"), "UNKNOWN")
        st["seen"][ev["eid"]].update(
            status=st_status,
            agent_status=res.get("status"),
            reported_done=bool(res.get("reported_done")),
            rpid=res.get("rpid"),
            core_status=res.get("core_status"),
            worth_replying=(res.get("decision") or {}).get("worth_replying"),
            reason=(res.get("reason") or "")[:200],
        )
        save_state(st, state_path)

        # 只有 act 模式下的真实闭环才算占用预算（observe 永不占用）
        if res.get("status") == agent_mod.DONE and eff_mode == "act":
            acted += 1

        item = {"kind": "event", "eid": ev["eid"], "channel": ev["channel"],
                "mode": eff_mode, "bvid": ev["bvid"], "source_id": ev["source_id"],
                "author": ev["author_name"], "author_mid": ev["author_mid"],
                "message": (ev["message"] or "")[:80],
                "status": st_status, "agent_status": res.get("status"),
                "worth_replying": (res.get("decision") or {}).get("worth_replying"),
                "sent": bool(res.get("sent")),
                "reported_done": bool(res.get("reported_done")),
                "rpid": res.get("rpid"), "core_status": res.get("core_status"),
                "reason": (res.get("reason") or "")[:200]}
        if do_log:
            append_log(item)
        processed.append(item)

    if do_ledger:
        pend = [p for p in processed if p["status"] == "PENDING_VERIFY"]
        done = [p for p in processed if p["status"] == "DONE"]
        if pend:
            ledger_poll("PENDING_VERIFY",
                        note="未决 %d 条：%s（禁自动重试）" % (len(pend), pend[0]["eid"]),
                        verify="事件流水 bili_event_log.jsonl")
        else:
            ledger_poll("OK" if not processed else "PROCESSED",
                        note="mode=%s 新事件=%d 处理=%d 真实发送=%d" % (
                            eff_mode, len(new), len(processed), len(done)),
                        verify="事件流水 bili_event_log.jsonl")

    exit_code = 2 if any(p["status"] == "PENDING_VERIFY" for p in processed) else 0
    return {"ok": True, "mode": eff_mode, "alive": len(events), "new": len(new),
            "processed": processed, "exit": exit_code}


# ============================================================
#  CLI
# ============================================================
def _acquire_lock():
    f = open(LOCK_PATH, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    f.write(str(os.getpid()))
    f.flush()
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description="B站事件泵（默认 observe 只读空跑）")
    ap.add_argument("--mode", choices=list(MODES), default=None,
                    help="observe=只读空跑（默认） / act=允许真实发送（受预算限制）")
    ap.add_argument("--set-mode", choices=list(MODES), default=None,
                    help="只修改持久化模式，不轮询")
    ap.add_argument("--baseline", action="store_true",
                    help="把当前可见事件登记为历史基线（不进 Agent）")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="单轮真实 Act 上限")
    ap.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS, help="单轮处理事件上限")
    ap.add_argument("--state", default=STATE_PATH, help="事件状态文件（测试可换临时文件）")
    ap.add_argument("--timeout", type=float, default=100.0, help="整体超时（秒）")
    ap.add_argument("--no-ledger", action="store_true", help="本轮不写 Action Ledger")
    args = ap.parse_args()

    if args.set_mode:
        st = load_state(args.state)
        st["mode"] = args.set_mode
        save_state(st, args.state)
        print("MODE=" + args.set_mode)
        return 0

    lock = _acquire_lock()
    if lock is None:
        print("SKIP=already_running")
        return 0

    try:
        res = asyncio.run(asyncio.wait_for(
            run_once(mode=args.mode, budget=max(0, args.budget),
                     max_events=max(1, args.max_events), baseline=args.baseline,
                     state_path=args.state,
                     do_ledger=not args.no_ledger),
            timeout=args.timeout))
    except asyncio.TimeoutError:
        append_log({"kind": "error", "reason": "整体超时 %ss → 停，不重试" % args.timeout})
        print("ERROR=timeout")
        return 3
    except Exception as e:
        append_log({"kind": "error", "reason": "%s: %s" % (type(e).__name__, e)})
        print("ERROR=%s: %s" % (type(e).__name__, e))
        return 3
    finally:
        try:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        except Exception:
            pass

    print(json.dumps({k: res.get(k) for k in ("ok", "mode", "alive", "new", "error")},
                     ensure_ascii=False))
    for p in res.get("processed") or []:
        print("  · %s %s status=%s sent=%s done=%s rpid=%s" % (
            p["eid"], p["channel"], p["status"], p["sent"], p["reported_done"], p["rpid"]))
    return int(res.get("exit") or 0)


if __name__ == "__main__":
    sys.exit(main())
