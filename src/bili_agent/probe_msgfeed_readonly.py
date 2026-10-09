#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针：看一眼 B站 msgfeed 现在有什么（绝不写状态、绝不调 Agent、绝不发送）"""
import asyncio, json, sys, time
sys.path.insert(0, "/root/.nana_secrets")
import bili_send_core as core
import bili_event_source as src


async def main():
    cred, ck = core.load_cred()
    my_mid = int(ck.get("dedeuserid") or 0)
    print("MY_MID =", my_mid, "| now =", time.strftime("%Y-%m-%d %H:%M:%S"))
    raw = {}
    for ch in src.CHANNELS:
        try:
            raw[ch] = await src.fetch_channel(cred, ch)
        except Exception as e:
            raw[ch] = {"ok": False, "error": "%s: %s" % (type(e).__name__, e), "items": []}
    coll = src.collect(raw, my_mid=my_mid)
    print("ok =", coll["ok"], "| errors =", coll["errors"])
    print("alive(归一化后事件数) =", len(coll["events"]), "| bad =", len(coll["bad"]))
    for ev in coll["events"]:
        print("-", ev["eid"], "|", ev["bvid"], "|", ev["author_name"],
              "(mid=%s)" % ev["author_mid"], "| is_mine =", ev["is_mine"],
              "| ctime =", ev["ctime"], "|", repr(ev["message"][:60]))
    for b in coll["bad"]:
        print("  bad:", b.get("channel"), b.get("id"), b.get("item_keys"))


asyncio.run(main())
