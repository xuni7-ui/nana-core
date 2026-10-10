#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站扫码登录 v2（稳健解析版）
- 生成二维码 -> 轮询 -> DONE 时对返回 url 做 unquote + parse_qs 解析
- 兼容 cookie 写在 url query / cookie_info 两种形态
- 凭据落 /root/.nana_secrets/bilibili_credential.json（600）
"""
import asyncio, json, os, re, sys, time
from urllib.parse import unquote, parse_qs, urlparse

QR_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bili_qr_v2.png"
SEC_DIR = "/root/.nana_secrets"
CRED_PATH = os.path.join(SEC_DIR, "bilibili_credential.json")

from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginChannel, QrCodeLoginEvents


def mask(v):
    if not v:
        return "EMPTY"
    return f"{v[:4]}…len{len(v)}"


def parse_cookies(events: dict) -> dict:
    """从 DONE 响应里尽可能稳地取出 cookie"""
    out = {"sessdata": "", "bili_jct": "", "buvid3": "", "buvid4": "",
           "dedeuserid": "", "ac_time_value": events.get("refresh_token", "") or ""}

    raw_url = events.get("url") or (events.get("data") or {}).get("url") or ""
    if raw_url:
        cand = [raw_url, unquote(raw_url), unquote(unquote(raw_url))]
        for blob in cand:
            qs = parse_qs(urlparse(blob).query, keep_blank_values=True)
            low = {k.lower(): v[0] if v else "" for k, v in qs.items()}
            got = False
            for key, dst in (("sessdata", "sessdata"), ("bili_jct", "bili_jct"),
                             ("dedeuserid", "dedeuserid"), ("buvid3", "buvid3"),
                             ("buvid4", "buvid4")):
                if low.get(key) and not out[dst]:
                    out[dst] = low[key]
                    got = True
            if got and out["sessdata"]:
                break
        if not out["sessdata"]:
            m = re.search(r"[?&]SESSDATA=([^&\s]+)", unquote(raw_url))
            if m:
                out["sessdata"] = m.group(1)
            m = re.search(r"[?&]bili_jct=([^&\s]+)", unquote(raw_url))
            if m:
                out["bili_jct"] = m.group(1)
            m = re.search(r"[?&]DedeUserID=([^&\s]+)", unquote(raw_url), re.I)
            if m:
                out["dedeuserid"] = m.group(1)

    # 形态二：cookie_info
    ci = ((events.get("data") or {}).get("cookie_info") or {}).get("cookies") or []
    for c in ci:
        n = str(c.get("name", "")).lower().replace("__", "_")
        if n in out and not out[n]:
            out[n] = c.get("value", "")

    return out


async def main():
    qr = QrCodeLogin(platform=QrCodeLoginChannel.WEB)
    await qr.generate_qrcode()
    pic = qr.get_qrcode_picture()
    try:
        pic.to_file(QR_PATH)
    except Exception as e:
        print("TOFILE_ERR", repr(e), flush=True)
    if not (os.path.exists(QR_PATH) and os.path.getsize(QR_PATH) > 0):
        data = getattr(pic, "content", None)
        if isinstance(data, bytes):
            open(QR_PATH, "wb").write(data)
    print("QR_READY" if os.path.getsize(QR_PATH) > 0 else "QR_FAIL", flush=True)
    if os.path.getsize(QR_PATH) == 0:
        return

    last, start = None, time.time()
    while time.time() - start < 170:
        try:
            st = await qr.check_state()
        except Exception as e:
            print("CHECK_ERR", repr(e), flush=True)
            await asyncio.sleep(3)
            continue
        if st != last:
            print("STATE", st.value, flush=True)
            last = st
        if st == QrCodeLoginEvents.DONE:
            cred_obj = qr.get_credential()
            ck = {
                "sessdata": getattr(cred_obj, "sessdata", "") or "",
                "bili_jct": getattr(cred_obj, "bili_jct", "") or "",
                "buvid3": getattr(cred_obj, "buvid3", "") or "",
                "buvid4": getattr(cred_obj, "buvid4", "") or "",
                "dedeuserid": getattr(cred_obj, "dedeuserid", "") or "",
                "ac_time_value": getattr(cred_obj, "ac_time_value", "") or "",
            }
            if not ck["sessdata"]:
                # 直接尝试从对象 cookie 字典兜底
                for k, v in (getattr(cred_obj, "_Credential__cookies", {}) or {}).items():
                    kl = k.lower()
                    if kl in ck and not ck[kl]:
                        ck[kl] = v
            ck["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            os.makedirs(SEC_DIR, exist_ok=True)
            with open(CRED_PATH, "w", encoding="utf-8") as f:
                json.dump(ck, f, ensure_ascii=False, indent=2)
            os.chmod(CRED_PATH, 0o600)
            print("FIELD_CHECK", {k: mask(v) for k, v in ck.items() if k != "saved_at"}, flush=True)
            print("LOGIN_OK uid=" + str(ck["dedeuserid"] or "?"), flush=True)
            return
        if st == QrCodeLoginEvents.TIMEOUT:
            print("TIMEOUT", flush=True)
            return
        await asyncio.sleep(2)
    print("GAVE_UP", flush=True)


asyncio.run(main())
