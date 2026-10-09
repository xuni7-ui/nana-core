#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站发评论（顶层，单条）—— C.2 可靠版

用法: python3 bili_send_comment.py <BVID> "<正文>" [--dry]
状态机: precheck → send → result → verify → record
退出码: 0=成功/幂等命中  1=可重试  2=状态不明(禁重试)  3=空跑
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_send_core import run_send, exit_code  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if len(args) < 2:
        print(__doc__)
        return 2
    bvid, text = args[0], args[1]
    res = asyncio.run(run_send("top", bvid, text, dry=dry))
    if dry:
        print("DRY_RUN 正文=%s" % text, flush=True)
    return exit_code(res)


if __name__ == "__main__":
    sys.exit(main())
