#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, json, os, time, sys

QR_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bili_qr.png"
SEC_DIR = "/root/.nana_secrets"
CRED_PATH = os.path.join(SEC_DIR, "bilibili_credential.json")

from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginChannel, QrCodeLoginEvents

async def main():
    qr = QrCodeLogin(platform=QrCodeLoginChannel.WEB)
    await qr.generate_qrcode()
    pic = qr.get_qrcode_picture()
    ok = False
    try:
        pic.to_file(QR_PATH)
        ok = os.path.exists(QR_PATH) and os.path.getsize(QR_PATH) > 0
    except Exception as e:
        print("TOFILE_ERR", repr(e), flush=True)
    if not ok:
        try:
            data = getattr(pic, "content", None)
            if isinstance(data, bytes):
                open(QR_PATH, "wb").write(data)
                ok = True
        except Exception as e:
            print("RAW_ERR", repr(e), flush=True)
    print("QR_READY" if ok else "QR_FAIL", flush=True)
    if not ok:
        return
    last = None
    start = time.time()
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
            c = qr.get_credential()
            os.makedirs(SEC_DIR, exist_ok=True)
            obj = {
                "sessdata": getattr(c, "sessdata", ""),
                "bili_jct": getattr(c, "bili_jct", ""),
                "buvid3": getattr(c, "buvid3", ""),
                "buvid4": getattr(c, "buvid4", ""),
                "dedeuserid": getattr(c, "dedeuserid", ""),
                "ac_time_value": getattr(c, "ac_time_value", ""),
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(CRED_PATH, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            os.chmod(CRED_PATH, 0o600)
            print("LOGIN_OK uid=" + str(getattr(c, "dedeuserid", "")), flush=True)
            return
        if st == QrCodeLoginEvents.TIMEOUT:
            print("TIMEOUT", flush=True)
            return
        await asyncio.sleep(2)
    print("GAVE_UP", flush=True)

asyncio.run(main())
