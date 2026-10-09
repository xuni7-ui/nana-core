#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站凭据保活：检查并刷新 cookie，延长登录寿命
用法: python3 bili_refresh.py
产物: 就地更新 /root/.nana_secrets/bilibili_credential.json
说明: 只做「检查 + 刷新 + 回写」，不打印任何 cookie 明文
"""
import asyncio, json, os, sys, time

CRED_PATH = "/root/.nana_secrets/bilibili_credential.json"

from bilibili_api.utils.network import Credential
from bilibili_api import user


def load():
    with open(CRED_PATH, encoding="utf-8") as f:
        return json.load(f)


def dump(ck):
    ck["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    ck["refreshed_at"] = ck["saved_at"]
    with open(CRED_PATH, "w", encoding="utf-8") as f:
        json.dump(ck, f, ensure_ascii=False, indent=2)
    os.chmod(CRED_PATH, 0o600)


def to_cred(ck):
    return Credential(sessdata=ck["sessdata"], bili_jct=ck["bili_jct"],
                      buvid3=ck.get("buvid3") or "", buvid4=ck.get("buvid4") or "",
                      dedeuserid=ck.get("dedeuserid") or "",
                      ac_time_value=ck.get("ac_time_value") or "")


def from_cred(cred):
    return {"sessdata": getattr(cred, "sessdata", "") or "",
            "bili_jct": getattr(cred, "bili_jct", "") or "",
            "buvid3": getattr(cred, "buvid3", "") or "",
            "buvid4": getattr(cred, "buvid4", "") or "",
            "dedeuserid": getattr(cred, "dedeuserid", "") or "",
            "ac_time_value": getattr(cred, "ac_time_value", "") or ""}


async def main():
    ck = load()
    if not ck.get("sessdata"):
        print("NO_CRED 没有有效凭据，需要重新扫码", flush=True)
        return 2
    cred = to_cred(ck)
    try:
        need = await cred.check_refresh()
    except Exception as e:
        print("CHECK_ERR", repr(e)[:160], flush=True)
        return 3
    print("CHECK_REFRESH", need, flush=True)
    if need:
        try:
            await cred.refresh()
        except Exception as e:
            print("REFRESH_ERR", repr(e)[:200], flush=True)
            return 4
        dump(from_cred(cred))
        print("REFRESHED", flush=True)
    try:
        info = await user.get_self_info(credential=cred)
        print("ALIVE name=%s mid=%s level=%s" % (
            info.get("name"), info.get("mid"), info.get("level")), flush=True)
    except Exception as e:
        print("ALIVE_ERR", repr(e)[:160], flush=True)
        return 5
    return 0


sys.exit(asyncio.run(main()))
