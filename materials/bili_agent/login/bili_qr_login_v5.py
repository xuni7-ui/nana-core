#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站扫码登录 v5 —— 双通道（web / tv）
用法: python3 bili_qr_login_v5.py <web|tv> /tmp/qr.png
产物: /root/.nana_secrets/bilibili_credential.json (600)
      /root/.nana_secrets/last_done_events.json (600, 原始返回，便于失败重试)
"""
import asyncio, json, os, re, sys, time
from urllib.parse import unquote, parse_qs, urlparse

CHANNEL = (sys.argv[1] if len(sys.argv) > 1 else "tv").lower()
QR_PATH = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/bili_qr_{CHANNEL}.png"
SEC_DIR = "/root/.nana_secrets"
CRED_PATH = os.path.join(SEC_DIR, "bilibili_credential.json")
EV_PATH = os.path.join(SEC_DIR, "last_done_events.json")

from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginChannel
from bilibili_api.utils.network import Api, Credential
from bilibili_api.utils.utils import get_api

POLL = get_api("login")["qrcode"][CHANNEL]["get_events"] if CHANNEL == "tv" else \
       get_api("login")["qrcode"]["web"]["get_events"]
WANT = ["SESSDATA", "bili_jct", "DedeUserID", "buvid3", "buvid4", "DedeUserID__ckMd5"]
KEYMAP = {"sessdata": "SESSDATA", "bili_jct": "bili_jct", "dedeuserid": "DedeUserID",
          "buvid3": "buvid3", "buvid4": "buvid4"}


def mask(v):
    v = v or ""
    return f"{v[:4]}…(len={len(v)})" if v else "EMPTY"


def harvest(obj):
    out = {}
    for getter in ("get_dict", "get_dict_all", "to_dict"):
        fn = getattr(obj, getter, None)
        if callable(fn):
            try:
                d = fn()
                d = d() if callable(d) else d
                if isinstance(d, dict):
                    out.update({str(k): str(v) for k, v in d.items()})
            except Exception:
                pass
    if hasattr(obj, "items"):
        try:
            out.update({str(k): str(v) for k, v in obj.items()})
        except Exception:
            pass
    try:
        for c in obj:
            n = getattr(c, "name", None)
            if n:
                out[n] = getattr(c, "value", "")
    except Exception:
        pass
    return out


async def exchange_ticket(ticket_url):
    """web 通道的新流程：拿票据 url 换 cookie"""
    from curl_cffi.requests import AsyncSession
    jar, final_url, scnames = {}, "", []
    async with AsyncSession(impersonate="chrome", timeout=20) as s:
        r = await s.get(ticket_url, allow_redirects=True)
        final_url = str(r.url)
        for k, v in harvest(r.cookies).items():
            jar.setdefault(k, v)
        sc = (getattr(r, "headers", {}) or {}).get("set-cookie", "") or ""
        if sc:
            for piece in re.split(r",(?=[^;,\s]+=)", sc):
                m = re.match(r"\s*([^=]+)=([^;]*)", piece)
                if m:
                    jar.setdefault(m.group(1).strip(), m.group(2).strip())
        for k, v in harvest(s.cookies).items():
            jar.setdefault(k, v)
        for blob in (final_url, ticket_url, unquote(final_url), unquote(ticket_url)):
            for k, vals in parse_qs(urlparse(blob).query, keep_blank_values=True).items():
                if k in WANT and vals and not jar.get(k):
                    jar[k] = vals[0]
    return jar, final_url, scnames


def save_cred(ck):
    os.makedirs(SEC_DIR, exist_ok=True)
    ck["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(CRED_PATH, "w", encoding="utf-8") as f:
        json.dump(ck, f, ensure_ascii=False, indent=2)
    os.chmod(CRED_PATH, 0o600)
    print("FIELD_CHECK", {k: mask(v) for k, v in ck.items() if k != "saved_at"}, flush=True)


async def verify(ck):
    from bilibili_api import user
    try:
        cred = Credential(sessdata=ck["sessdata"], bili_jct=ck["bili_jct"],
                          buvid3=ck.get("buvid3") or "", buvid4=ck.get("buvid4") or "",
                          dedeuserid=ck.get("dedeuserid") or "",
                          ac_time_value=ck.get("ac_time_value") or "")
        info = await user.get_self_info(credential=cred)
        print("VERIFY_OK name=%s mid=%s level=%s" % (
            info.get("name"), info.get("mid"), info.get("level")), flush=True)
        return True
    except Exception as e:
        print("VERIFY_ERR", repr(e)[:200], flush=True)
        return False


async def main():
    ch = QrCodeLoginChannel.TV if CHANNEL == "tv" else QrCodeLoginChannel.WEB
    qr = QrCodeLogin(platform=ch)
    await qr.generate_qrcode()
    pic = qr.get_qrcode_picture()
    try:
        pic.to_file(QR_PATH)
    except Exception as e:
        print("TOFILE_ERR", repr(e), flush=True)
    if not (os.path.exists(QR_PATH) and os.path.getsize(QR_PATH) > 0):
        raw = getattr(pic, "content", None)
        if isinstance(raw, bytes):
            open(QR_PATH, "wb").write(raw)
    if os.path.getsize(QR_PATH) == 0:
        print("QR_FAIL", flush=True)
        return
    print("QR_READY channel=" + CHANNEL, flush=True)

    last, start = None, time.time()
    while time.time() - start < 175:
        try:
            st = await qr.check_state()
        except Exception as e:
            print("POLL_ERR", repr(e)[:160], flush=True)
            await asyncio.sleep(3)
            continue
        if st != last:
            print("STATE", st.value, flush=True)
            last = st
        if st.value == "done":
            cred_obj = qr.get_credential()
            ck = {"sessdata": getattr(cred_obj, "sessdata", "") or "",
                  "bili_jct": getattr(cred_obj, "bili_jct", "") or "",
                  "buvid3": getattr(cred_obj, "buvid3", "") or "",
                  "buvid4": getattr(cred_obj, "buvid4", "") or "",
                  "dedeuserid": getattr(cred_obj, "dedeuserid", "") or "",
                  "ac_time_value": getattr(cred_obj, "ac_time_value", "") or ""}
            if not ck["sessdata"]:
                jar = harvest(getattr(cred_obj, "get_cookies", lambda: {})() or {})
                for k, v in jar.items():
                    kl = k.lower().replace("__", "_")
                    if kl in ck and not ck[kl]:
                        ck[kl] = v
            try:
                with open(EV_PATH, "w", encoding="utf-8") as f:
                    json.dump({"channel": CHANNEL, "channel_hint": "tv-direct-cookie"},
                              f, ensure_ascii=False)
                os.chmod(EV_PATH, 0o600)
            except Exception:
                pass
            save_cred(ck)
            ok = await verify(ck)
            print("LOGIN_%s uid=%s" % ("OK" if ok else "UNVERIFIED",
                                       ck.get("dedeuserid") or "?"), flush=True)
            return
        if st.value == "timeout":
            print("TIMEOUT", flush=True)
            return
        await asyncio.sleep(2)
    print("GAVE_UP", flush=True)


asyncio.run(main())
