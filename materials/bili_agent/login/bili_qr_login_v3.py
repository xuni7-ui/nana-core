#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站扫码登录 v3 —— 自己轮询原始响应，稳健解析 cookie
用法: python3 bili_qr_login_v3.py /tmp/bili_qr_v3.png
产物: /root/.nana_secrets/bilibili_credential.json (600)
      /root/.nana_secrets/last_poll_debug.json (600, 值已打码，只留结构与长度)
"""
import asyncio, json, os, re, sys, time
from urllib.parse import unquote, parse_qs, urlparse

QR_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bili_qr_v3.png"
SEC_DIR = "/root/.nana_secrets"
CRED_PATH = os.path.join(SEC_DIR, "bilibili_credential.json")

from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginChannel
from bilibili_api.utils.network import Api, Credential
from bilibili_api.utils.utils import get_api

API = get_api("login")["qrcode"]["web"]["get_events"]

WANT = {"sessdata": "sessdata", "bili_jct": "bili_jct", "dedeuserid": "dedeuserid",
        "buvid3": "buvid3", "buvid4": "buvid4"}


def mask(v, keep=4):
    v = v or ""
    return f"{v[:keep]}…(len={len(v)})" if v else "EMPTY"


def unroll(events):
    """把各种可能的嵌套摊平，便于解析"""
    flat = dict(events)
    for key in ("data", "cookie_info"):
        sub = events.get(key)
        if isinstance(sub, dict):
            for k, v in sub.items():
                flat.setdefault(k, v)
            for k, v in (sub.get("cookie_info") or {}).items():
                flat.setdefault(k, v)
    return flat


def grab(flat):
    out = {v: "" for v in WANT.values()}
    out["ac_time_value"] = flat.get("refresh_token") or ""
    raw = flat.get("url") or ""

    if raw:
        for blob in (raw, unquote(raw), unquote(unquote(raw))):
            qs = parse_qs(urlparse(blob).query, keep_blank_values=True)
            for k, vals in qs.items():
                kl = k.lower()
                if kl in WANT and vals and not out[WANT[kl]]:
                    out[WANT[kl]] = vals[0]
            if out["sessdata"]:
                break
        if not out["sessdata"]:
            for pat, dst in ((r"SESSDATA=([^&\s]+)", "sessdata"),
                             (r"bili_jct=([^&\s]+)", "bili_jct"),
                             (r"DedeUserID=([^&\s]+)", "dedeuserid")):
                m = re.search(pat, unquote(raw), re.I)
                if m:
                    out[dst] = m.group(1)

    for c in (flat.get("cookies") or []):
        if isinstance(c, dict):
            kl = str(c.get("name", "")).lower().replace("__", "_")
            if kl in WANT and not out[WANT[kl]]:
                out[WANT[kl]] = c.get("value", "")
    return out


def diag(flat, raw_url=""):
    keys = list(flat.keys())
    qkeys = []
    if raw_url:
        for blob in (raw_url, unquote(raw_url)):
            q = parse_qs(urlparse(blob).query, keep_blank_values=True)
            if q:
                qkeys = {k: len(v[0]) if v else 0 for k, v in q.items()}
                break
    return {"top_keys": keys, "url_len": len(raw_url or ""), "url_qkeys": qkeys,
            "url_head": (raw_url or "")[:40]}


async def main():
    qr = QrCodeLogin(platform=QrCodeLoginChannel.WEB)
    await qr.generate_qrcode()
    key = getattr(qr, "_QrCodeLogin__qr_key", None)
    pic = qr.get_qrcode_picture()
    try:
        pic.to_file(QR_PATH)
    except Exception as e:
        print("TOFILE_ERR", repr(e), flush=True)
    if not (os.path.exists(QR_PATH) and os.path.getsize(QR_PATH) > 0):
        data = getattr(pic, "content", None)
        if isinstance(data, bytes):
            open(QR_PATH, "wb").write(data)
    good = os.path.exists(QR_PATH) and os.path.getsize(QR_PATH) > 0
    print("QR_READY key=" + ("yes" if key else "no") if good else "QR_FAIL", flush=True)
    if not good:
        return

    last, start = None, time.time()
    while time.time() - start < 175:
        try:
            events = await Api(credential=Credential(), **API).update_params(qrcode_key=key).result
        except Exception as e:
            print("POLL_ERR", repr(e)[:200], flush=True)
            await asyncio.sleep(3)
            continue
        code = events.get("code")
        tag = {86101: "SCAN", 86090: "CONF", 86038: "TIMEOUT"}.get(code, "DONE")
        if tag != last:
            print("STATE", tag, flush=True)
            last = tag
        if tag == "DONE":
            flat = unroll(events)
            raw_url = flat.get("url") or ""
            try:
                os.makedirs(SEC_DIR, exist_ok=True)
                with open(os.path.join(SEC_DIR, "last_poll_debug.json"), "w") as f:
                    json.dump(diag(flat, raw_url), f, ensure_ascii=False, indent=1)
                os.chmod(os.path.join(SEC_DIR, "last_poll_debug.json"), 0o600)
            except Exception as e:
                print("DEBUG_ERR", repr(e)[:120], flush=True)
            ck = grab(flat)
            ck["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(CRED_PATH, "w", encoding="utf-8") as f:
                json.dump(ck, f, ensure_ascii=False, indent=2)
            os.chmod(CRED_PATH, 0o600)
            print("FIELD_CHECK", {k: mask(v) for k, v in ck.items() if k != "saved_at"}, flush=True)
            print("LOGIN_OK uid=" + str(ck["dedeuserid"] or "?"), flush=True)
            return
        if tag == "TIMEOUT":
            print("TIMEOUT", flush=True)
            return
        await asyncio.sleep(2)
    print("GAVE_UP", flush=True)


asyncio.run(main())
