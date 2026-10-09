#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_c5v_wiring.py — C.5-V-1 接线适配层 · 全离线确定性测试（T1–T9）

运行：python3 test_c5v_wiring.py
纪律：**零网络**。视频由 ffmpeg lavfi 现造；视觉调用一律注入假客户端。
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
C5V_DIR = os.path.join(os.path.dirname(HERE), "c5v")
if C5V_DIR not in sys.path:
    sys.path.insert(0, C5V_DIR)

import c5v_wiring as w                      # noqa: E402
import bili_video_vision as c5v             # noqa: E402

PASS: list = []
FAIL: list = []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("✅" if cond else "❌", name, ("  — " + detail) if detail and not cond else ""))


# ------------------------------------------------------------
# 工具
# ------------------------------------------------------------
def make_video(path: str, seconds: float = 2.0) -> bool:
    """lavfi 造一段确定性测试视频（不联网）。"""
    base = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-f", "lavfi",
            "-i", "testsrc=duration=%.1f:size=160x120:rate=10" % seconds]
    for codec in (["-c:v", "libx264", "-pix_fmt", "yuv420p"], ["-c:v", "mpeg4"]):
        r = subprocess.run(base + codec + [path], capture_output=True)
        if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
            return True
    return False


VALID_JSON_TEXT = json.dumps({
    "summary": "一段彩色测试图随时间变化的画面",
    "scenes": [{"order": 1, "start_s": 0, "end_s": 2, "description": "测试图持续变化"}],
    "entities": ["测试图案"],
    "on_screen_text": [],
    "actions": ["图案变化"],
    "evidence_sufficient": True,
    "confidence": 0.82,
}, ensure_ascii=False)


def fake_client_ok(images, prompt):
    return {"text": VALID_JSON_TEXT, "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "fake-vision"}


def fake_client_nonjson(images, prompt):
    return {"text": "我看到了一些东西，但我不打算给你 JSON。", "usage": {}, "model": "fake-vision"}


def fake_client_boom(images, prompt):
    raise RuntimeError("模拟视觉接口 500")


def fake_fetcher_none(bvid, dest_dir, timeout_s=60):
    return None


def run(coro):
    return asyncio.run(coro)


def main():
    tmp = tempfile.mkdtemp(prefix="c5v_wire_test_")
    video = os.path.join(tmp, "clip.mp4")
    has_video = make_video(video)
    print("测试视频：", video, "（生成%s）" % ("成功" if has_video else "失败"))

    original_enabled = w.WIRING_ENABLED

    # ---------------- T1 未启用 → 逐字节不变 ----------------
    w.WIRING_ENABLED = False
    src = "标题：X\n字幕：无（空）"
    out, meta = run(w.augment_material_brief(src, "BV1test"))
    check("T1 未启用时素材块逐字节不变",
          out == src and meta.get("enabled") is False, repr(out))

    # ---------------- T2 启用但视频不可得 → 原文不变 ----------------
    w.WIRING_ENABLED = True
    out, meta = run(w.augment_material_brief(src, "BV1test", fetcher=fake_fetcher_none))
    check("T2 视频不可得时原文不变 + 有 reason",
          out == src and meta.get("enabled") is True and "不可得" in (meta.get("reason") or ""),
          json.dumps(meta, ensure_ascii=False))

    # ---------------- T3 本地视频 + 假客户端 → 追加画面事实 ----------------
    if has_video:
        out, meta = run(w.augment_material_brief(
            src, "BV1test", video_path=video, client=fake_client_ok,
            budget=w.Budget(cleanup=False)))
        check("T3 可用时追加【画面事实】且含 summary",
              out.startswith(src) and "【画面事实】" in out and "彩色测试图" in out
              and meta.get("available") is True, json.dumps(meta, ensure_ascii=False))
    else:
        check("T3 (跳过：无 ffmpeg 视频)", False, "ffmpeg 不可用")

    # ---------------- T4 视觉接口炸 → 原文不变 ----------------
    if has_video:
        out, meta = run(w.augment_material_brief(src, "BV1test", video_path=video,
                                                 client=fake_client_boom,
                                                 budget=w.Budget(cleanup=False)))
        check("T4 视觉接口异常时原文不变", out == src and meta.get("ok") is False,
              json.dumps(meta, ensure_ascii=False))

    # ---------------- T5 非 JSON 回复 → 不注入（绝不编造） ----------------
    if has_video:
        out, meta = run(w.augment_material_brief(src, "BV1test", video_path=video,
                                                 client=fake_client_nonjson,
                                                 budget=w.Budget(cleanup=False)))
        check("T5 非 JSON 回复不注入画面事实", out == src and meta.get("ok") is False,
              json.dumps(meta, ensure_ascii=False))

    # ---------------- T6 时长超预算 → 拒绝 ----------------
    if has_video:
        out, meta = run(w.augment_material_brief(src, "BV1test", video_path=video,
                                                 client=fake_client_ok,
                                                 budget=w.Budget(max_duration_s=0.5,
                                                                 cleanup=False)))
        check("T6 超时长预算时拒绝并说明", out == src and "超过预算上限" in (meta.get("reason") or ""),
              json.dumps(meta, ensure_ascii=False))

    # ---------------- T7 离线（无客户端、无环境变量）→ 明确不联网 ----------------
    if has_video:
        saved = {k: os.environ.pop(k, None) for k in
                 ("NANA_C5V_VISION_BASE_URL", "NANA_C5V_VISION_API_KEY")}
        out, meta = run(w.augment_material_brief(src, "BV1test", video_path=video,
                                                 client=None, budget=w.Budget(cleanup=False)))
        check("T7 无视觉客户端时明确离线且不注入",
              out == src and meta.get("available") is False
              and "离线" in (meta.get("reason") or ""), json.dumps(meta, ensure_ascii=False))
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v

    # ---------------- T8 静态纪律：导入面 / 无硬编码密钥 ----------------
    src_code = open(os.path.join(HERE, "c5v_wiring.py"), encoding="utf-8").read()
    tree = ast.parse(src_code)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
    forbidden = {"bili_send_core", "bili_event_pump", "bili_video_read",
                 "nana_bili_health_check", "bili_agent"}
    leaked = sorted(imported & forbidden)
    top_imports = {n.names[0].name for n in tree.body if isinstance(n, ast.Import)}
    check("T8a 不 import 任何生产发送/事件/日志模块", not leaked, str(leaked))
    check("T8b 顶层只 import 标准库",
          top_imports.issubset({"os", "shutil", "subprocess", "tempfile", "time",
                                "dataclasses", "typing", "__future__"}), str(top_imports))
    check("T8c 无硬编码密钥特征", "Bearer " not in src_code and "SESSDATA" not in src_code)

    # ---------------- T9 render_block 不编造 ----------------
    empty = w.render_block(w.WiringResult(ok=False, available=False, brief=""))
    check("T9 不可用时 render_block 返回空串", empty == "", repr(empty))

    w.WIRING_ENABLED = original_enabled
    import shutil as _sh
    _sh.rmtree(tmp, ignore_errors=True)

    print("\n===== 结果：%d 通过 / %d 失败 =====" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：", FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
