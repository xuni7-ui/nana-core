#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili Agent Health Check —— 只读 · 确定性 · 无 LLM · 无网络 · 轻量
仅“读取”现有：event state / event log / comment log / Action Ledger / pump cron log。
绝不：改代码、改配置、重启、重发评论、扩大 replay window、切换 act/observe。
只向 stdout 打印一行 JSON 结论。可被「容器内」或「主机 cron」两种上下文调用。
"""
import calendar
import glob
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone

# ---------- 运行上下文自适应（容器内 / 主机侧）----------
def _detect_ctx():
    b = os.environ.get("NANA_BASE")
    l = os.environ.get("NANA_LEDGER")
    if b and l:
        return b, l
    if os.path.isdir("/AstrBot/data"):                       # 容器内
        return ("/root/.nana_secrets",
                "/AstrBot/data/plugin_data/astrbot_plugin_iris_chat_memory/action_ledger/ledger.json")
    cands = glob.glob("/var/lib/docker/rootfs/overlayfs/*/root/.nana_secrets")  # 主机侧
    base = cands[0] if cands else "/root/.nana_secrets"
    return (base,
            "/root/astrbot_data/plugin_data/astrbot_plugin_iris_chat_memory/action_ledger/ledger.json")

BASE, LEDGER_PATH = _detect_ctx()
STATE    = os.path.join(BASE, "bili_event_state.json")
PUMPLOG  = os.path.join(BASE, "bili_event_pump_cron.log")
CLOG     = os.path.join(BASE, "bili_comment_log.jsonl")
LOCK     = os.path.join(BASE, ".bili_event_pump.lock")

# 四封板文件基线（只校验、绝不修改）；封板文件若被“合法”重封，需同步更新此处
SEALED = {
    "bili_event_pump.py": "59f3e8ee50dff268622b85d1113830dd",
    "bili_agent.py":      "afcd69df7a8840d69b67c3ae6b2dcee0",
    "bili_send_core.py":  "b87ce89c5f208ac272080a4f9321d9fd",
    "bili_video_read.py": "96fb021529228c752bc1c865f05021eb",
}
HEART_WARN_MIN, HEART_ALERT_MIN = 5.0, 15.0
PV_STUCK_MIN = 30.0

NOW = time.time()
findings = []
def add(level, code, msg):
    findings.append({"level": level, "code": code, "msg": msg})

def _age_min(ts_str):
    """时间串 → 距今分钟（时区安全，与统一 timeutil 基准一致）。

    规则（对齐 iris_memory/utils/timeutil.py）：
      - 带偏移（+08:00 / +00:00 / Z）→ 按原偏移换算（Action Ledger 口径）
      - naive（无时区）→ 一律按 UTC 解释（容器 TZ=UTC 写出的 pump/state 口径）

    修复说明：旧实现用 time.mktime()，会把 naive 串当成「本机本地时区」。
    主机 cron 本地时区是 CST(+8)，而 pump 日志 / event state 的 naive 串是
    UTC，于是被多算 8 小时，恒定误报 HEARTBEAT_STALE(480min)。改用 UTC
    基准后，容器内(UTC)与主机侧(CST)两种上下文结论一致。
    """
    if not ts_str:
        return None
    s = str(ts_str).strip()
    if not s:
        return None
    try:
        iso = s[:-1] + "+00:00" if s.endswith("Z") else s
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)      # naive → UTC（timeutil 兼容规则）
        return (NOW - dt.timestamp()) / 60.0
    except Exception:
        pass
    try:
        return (NOW - calendar.timegm(time.strptime(s[:19], "%Y-%m-%d %H:%M:%S"))) / 60.0
    except Exception:
        return None

rep = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "ctx_base": BASE, "checks": {}, "findings": findings}

# ---------- 1. event state ----------
try:
    with open(STATE, encoding="utf-8") as f:
        st = json.load(f)
    mode, seen, order = st.get("mode"), st.get("seen") or {}, st.get("order") or []
    rep["checks"].update(mode=mode, events=len(seen), updated_at=st.get("updated_at"))
    if mode not in ("observe", "act"):
        add("ALERT", "MODE_INVALID", "mode=%r 非 observe/act" % mode)
    if len(order) != len(set(order)):
        add("ALERT", "DUP_EID", "order 内 eid 重复")
    miss = [k for k in seen if k not in order]
    extra = [k for k in order if k not in seen]
    if miss or extra:
        add("WARN", "ORDER_MISMATCH", "seen/order 不一致 missing=%d extra=%d" % (len(miss), len(extra)))
    rep["checks"]["status_counts"] = dict(Counter(v.get("status") for v in seen.values()))
    retry = [k for k, v in seen.items()
             if v.get("status") == "RETRYABLE" or v.get("agent_status") == "RETRYABLE"]
    if retry:
        add("WARN", "RETRYABLE_ACCUM", "RETRYABLE %d 条: %s" % (len(retry), retry[:3]))
    pv = [k for k, v in seen.items()
          if v.get("status") in ("PENDING_VERIFY",) or v.get("core_status") == "PENDING_VERIFY"]
    if pv:
        add("WARN", "STATE_PENDING_VERIFY", "state 内 PENDING_VERIFY %d 条" % len(pv))
    rp = [v.get("rpid") for v in seen.values() if v.get("rpid")]
    rep["checks"]["rpid_unique_state"] = len(set(rp))
    if len(rp) != len(set(rp)):
        add("ALERT", "DUP_RPID_STATE", "state 内 rpid 重复")
except Exception as e:
    add("ALERT", "STATE_READ_FAIL", "%s: %s" % (type(e).__name__, e))

# ---------- 2. pump 心跳 / 连续正常 ----------
try:
    with open(PUMPLOG, encoding="utf-8", errors="replace") as f:
        ticks = [l for l in f.read().splitlines()[-60:] if "TICK" in l]
    rep["checks"]["recent_ticks"] = len(ticks)
    m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", ticks[-1]) if ticks else None
    if not m:
        add("ALERT", "HEARTBEAT_MISSING", "cron 日志无 TICK")
    else:
        age = _age_min(m.group(1))
        rep["checks"].update(last_tick=m.group(1), last_tick_age_min=round(age, 2))
        if age > HEART_ALERT_MIN:
            add("ALERT", "HEARTBEAT_STALE", "末拍距今 %.1f 分钟" % age)
        elif age > HEART_WARN_MIN:
            add("WARN", "HEARTBEAT_SLOW", "末拍距今 %.1f 分钟" % age)
    bad = sum(1 for l in ticks[-10:]
              if '"ok": false' in l or '"ok":false' in l or "ERROR=" in l or "SKIP=" in l)
    if bad:
        add("WARN", "TICK_NOT_OK", "近 10 拍有 %d 拍异常/SKIP" % bad)
except Exception as e:
    add("ALERT", "PUMPLOG_READ_FAIL", "%s: %s" % (type(e).__name__, e))

# ---------- 3. comment log 重复 rpid ----------
try:
    rps = []
    with open(CLOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    r = json.loads(line).get("rpid")
                    if r:
                        rps.append(r)
                except Exception:
                    pass
    rep["checks"]["comment_log_rpids"] = len(rps)
    if len(rps) != len(set(rps)):
        add("ALERT", "DUP_RPID_COMMENT", "comment_log 内 rpid 重复")
except Exception as e:
    add("WARN", "CLOG_READ_FAIL", "%s: %s" % (type(e).__name__, e))

# ---------- 4. Action Ledger ----------
try:
    with open(LEDGER_PATH, encoding="utf-8") as f:
        ledger = json.load(f)
    keys = ledger.get("keys") or {}
    rep["checks"]["ledger_path"] = LEDGER_PATH
    pv = keys.get("bili_comment_pending_verify")
    if pv and str(pv.get("state")).lower() not in ("none", "null", ""):
        age = _age_min(pv.get("updated_at", ""))
        add("ALERT" if (age is None or age > PV_STUCK_MIN) else "WARN",
            "PENDING_VERIFY_STUCK", "bili_comment_pending_verify=%s age=%s" % (pv.get("state"), age))
    lp = keys.get("bili_event_pump_last_poll")
    if lp:
        rep["checks"]["pump_last_poll"] = lp.get("updated_at")
        a = _age_min(lp.get("updated_at", ""))
        if a is not None and a > HEART_ALERT_MIN:
            add("WARN", "LEDGER_POLL_STALE", "账本末次轮询距今 %.1f 分钟" % a)
except Exception as e:
    add("WARN", "LEDGER_READ_FAIL", "%s: %s" % (type(e).__name__, e))

# ---------- 5. 单飞锁 ----------
try:
    pid = open(LOCK).read().strip()
    rep["checks"].update(lock_pid=pid, lock_pid_alive=os.path.isdir("/proc/%s" % pid))
except Exception:
    pass

# ---------- 6. 四封板文件指纹 ----------
sealed_ok = True
for fn, exp in SEALED.items():
    try:
        h = hashlib.md5(open(os.path.join(BASE, fn), "rb").read()).hexdigest()
        if h != exp:
            sealed_ok = False
            add("ALERT", "SEALED_CHANGED", "%s md5=%s ≠ %s" % (fn, h, exp))
    except Exception as e:
        sealed_ok = False
        add("ALERT", "SEALED_READ_FAIL", "%s: %s" % (fn, e))
rep["checks"]["sealed_files_intact"] = sealed_ok

# ---------- 结语 ----------
rep["verdict"] = ("ALERT" if any(f["level"] == "ALERT" for f in findings)
                  else "WARN" if findings else "OK")
print(json.dumps(rep, ensure_ascii=False))
sys.exit(0)
