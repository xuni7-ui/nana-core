#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站扫码登录 v4 —— 票据换 cookie 版
流程: 生成二维码 -> 轮询 -> DONE 得到 crossDomain 票据 url
      -> 用带 cookie jar 的会话访问票据 url -> 收 Set-Cookie -> 落盘 + 验号
产物: /root/.nana_secrets/bilibili_credential.json  (600)
      /root/.nana_secrets/last_done_events.json    (600, 含票据原文，便于失败重试)
用法: python3 bili_qr_login_v4.py /tmp/bili_qr_v4.png
"""
import asyncio, json, os, re, sys, time
from urllib.parse import unquote, parse_qs, urlparse

QR_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bili_qr_v4.png"
SEC_DIR = "/root/.nana_secrets"
CRED_PATH = os.path.join(SEC_DIR, "bilibili_credential.json")
EV_PATH = os.path.join(SEC_DIR, "last_done_events.json")

from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginChannel
from bilibili_api.utils.network import Api, Credential
from bilibili_api.utils.utils import get_api

POLL_API = get_api("login")["qrcode"]["web"]["get_events"]
WANT = ["SESSDATA", "bili_jct", "DedeUserID", "buvid3", "buvid4", "DedeUserID__ckMd5"]
KEYMAP = {"sessdata": "SESSDATA", "bili_jct": "bili_jct", "dedeuserid": "DedeUserID",
          "buvid3": "buvid3", "buvid4": "buvid4"}


def mask(v):
    v = v or ""
    return f"{v[:4]}…(len={len(v)})" if v else "EMPTY"


def harvest(obj):
    """从各种 cookie 容器里薅出字典"""
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
        for c in obj:  # cookiejar
            n = getattr(c, "name", None)
            if n:
                out[n] = getattr(c, "value", "")
    except Exception:
        pass
    return out


async def exchange_ticket(ticket_url: str) -> tuple:
    """带 jar 访问票据 url，跟随跳转，收 cookie"""
    from curl_cffi.requests import AsyncSession
    jar = {}
    final_url = ""
    set_cookie_names = []
    async with AsyncSession(impersonate="chrome", timeout=20) as s:
        r = await s.get(ticket_url, allow_redirects=True)
        final_url = str(r.url)
        for k, v in harvest(r.cookies).items():
            jar.setdefault(k, v)
        raw_hdrs = getattr(r, "headers", {}) or {}
        sc = raw_hdrs.get("set-cookie") or raw_hdrs.get("Set-Cookie") or ""
        if sc:
            for piece in re.split(r",(?=[^;,\s]+=)", sc):
                name = piece.split("=")[0].strip()
                if name:
                    set_cookie_names.append(name)
                m = re.match(r"\s*([^=]+)=([^;]*)", piece)
                if m:
                    jar.setdefault(m.group(1).strip(), m.group(2).strip())
        for k, v in harvest(s.cookies).items():
            jar.setdefault(k, v)
        # 票据 url 的 query 里也可能带 cookie（老形态）
        for blob in (final_url, ticket_url, unquote(final_url), unquote(ticket_url)):
            for k, vals in parse_qs(urlparse(blob).query, keep_blank_values=True).items():
                if k in WANT and vals and not jar.get(k):
                    jar[k] = vals[0]
    return jar, final_url, set_cookie_names


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
        raw = getattr(pic, "content", None)
        if isinstance(raw, bytes):
            open(QR_PATH, "wb").write(raw)
    if os.path.getsize(QR_PATH) == 0:
        print("QR_FAIL", flush=True)
        return
    print("QR_READY key=yes" if key else "QR_READY key=no", flush=True)

    last, start = None, time.time()
    while time.time() - start < 175:
        try:
            ev = await Api(credential=Credential(), **POLL_API).update_params(qrcode_key=key).result
        except Exception as e:
            print("POLL_ERR", repr(e)[:160], flush=True)
            await asyncio.sleep(3)
            continue
        code = ev.get("code")
        tag = {86101: "SCAN", 86090: "CONF", 86038: "TIMEOUT"}.get(code, "DONE")
        if tag != last:
            print("STATE", tag, flush=True)
            last = tag
        if tag == "DONE":
            os.makedirs(SEC_DIR, exist_ok=True)
            ev_saved = dict(ev)
            with open(EV_PATH, "w", encoding="utf-8") as f:
                json.dump(ev_saved, f, ensure_ascii=False, indent=1)
            os.chmod(EV_PATH, 0o600)
            ticket_url = ev.get("url") or ""
            print("TICKET_LEN", len(ticket_url), flush=True)

            jar, final_url, scnames = {}, "", []
            try:
                jar, final_url, scnames = await exchange_ticket(ticket_url)
            except Exception as e:
                print("EXCHANGE_ERR", repr(e)[:200], flush=True)

            print("COOKIE_KEYS", sorted(jar.keys()), flush=True)
            print("SET_COOKIE", scnames[:10], flush=True)
            print("FINAL_HEAD", final_url[:60], flush=True)

            ck = {v: jar.get(k, "") for k, v in KEYMAP.items()}
            ck["ac_time_value"] = ev.get("refresh_token") or ""
            ck["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(CRED_PATH, "w", encoding="utf-8") as f:
                json.dump(ck, f, ensure_ascii=False, indent=2)
            os.chmod(CRED_PATH, 0o600)
            print("FIELD_CHECK", {k: mask(v) for k, v in ck.items() if k != "saved_at"}, flush=True)
            print("LOGIN_OK uid=" + str(ck.get("dedeuserid") or "?"), flush=True)
            return
        if tag == "TIMEOUT":
            print("TIMEOUT", flush=True)
            return
        await asyncio.sleep(2)
    print("GAVE_UP", flush=True)


asyncio.run(main())
