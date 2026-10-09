#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bili_video_vision.py  —  C.5-V-1 离线独立模块
================================================
目标（Level 2：看懂视频主要画面 + 事件顺序，不是逐帧理解）：

    视频 → 视频结构分析 → 智能关键帧 → 视觉模型 → 结构化视觉事实

设计纪律
--------
* 本模块 **离线独立**：不 import bili_agent / bili_event_pump / bili_send_core /
  bili_video_read / nana_bili_health_check，也不读写任何生产 state / Ledger / 日志。
* 视觉模型调用 **可注入**（client 参数）；离线测试注入 fake，不产生真实请求。
* 唯一允许的落盘：调用方指定的 workdir（默认 /tmp 下随机目录）里的关键帧 jpg。
* 任何失败都不抛到调用方：返回结构化结果，error 如实记录，**绝不编造画面内容**。

结构化视觉事实 schema = c5v.visual_facts.v1（见 build_visual_facts / validate_visual_facts）
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "c5v.visual_facts.v1"
MODULE_NAME = "bili_video_vision"
MODULE_STAGE = "C.5-V-1"

# ---- 默认参数（可被调用方覆盖） ----
DEFAULT_MAX_FRAMES = 8          # 关键帧硬上限（≤8，token 友好）
DEFAULT_SCENE_THRESHOLD = 0.30  # ffmpeg scene 切换阈值
DEFAULT_FALLBACK_FRAMES = 4     # 检测不到镜头切换时的均匀采样张数
DEFAULT_FRAME_WIDTH = 640       # 抽帧缩放宽度（长边不超过）
DEFAULT_MIN_GAP_S = 0.5         # 两个关键帧之间的最小时间间隔
DEFAULT_JPEG_Q = 3              # ffmpeg -q:v

_FFMPEG = os.environ.get("NANA_C5V_FFMPEG", "ffmpeg")
_FFPROBE = os.environ.get("NANA_C5V_FFPROBE", "ffprobe")

# 视觉模型出口：默认复用 AstrBot 现有 chat provider（deepseek-flash，modalities 含 image）
DEFAULT_VISION_MODEL = os.environ.get("NANA_C5V_VISION_MODEL", "deepseek-flash")

VISION_PROMPT = (
    "你在看一段视频的若干张**关键帧**（按时间先后排列，已标注时间点）。\n"
    "请只依据这些画面回答，**不要编造**画面里没有的内容。\n"
    "只输出一个 JSON 对象，且只含这些字段：\n"
    '{"summary": 一句话概括视频主要画面,'
    ' "scenes":[{"order":序号,"start_s":起点秒,"end_s":终点秒,"description":该段画面描述}],'
    ' "entities":[画面中出现的对象/人物/场景],'
    ' "on_screen_text":[画面中的文字/字幕,没有就空数组],'
    ' "actions":[按顺序发生的主要动作/事件],'
    ' "evidence_sufficient": true/false 画面是否足以支撑上面结论,'
    ' "confidence": 0~1 之间的置信度}\n'
    "禁止输出任何其他字段或解释文字。"
)


# ============================================================
# 0. 数据结构
# ============================================================
@dataclass
class Keyframe:
    idx: int
    t: float                 # 时间点（秒）
    reason: str              # head / tail / scene_cut / uniform
    path: Optional[str] = None
    b64: Optional[str] = None
    bytes_: Optional[int] = None


@dataclass
class VideoStructure:
    path: str
    ok: bool
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    vcodec: str = ""
    n_scene_cuts: int = 0
    selection_mode: str = ""      # scene_cut / fallback_uniform / none
    error: Optional[str] = None


# ============================================================
# 1. 结构分析（ffprobe）
# ============================================================
def _run(cmd: Sequence[str], timeout: int = 60) -> Tuple[int, str, str]:
    p = subprocess.run(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def probe_video(path: str, *, ffprobe: str = _FFPROBE) -> VideoStructure:
    """ffprobe 读时长/分辨率/帧率。失败返回 ok=False（不抛）。"""
    if not path:
        return VideoStructure(path="", ok=False, error="空路径")
    if not os.path.exists(path):
        return VideoStructure(path=path, ok=False, error="文件不存在：%s" % path)
    cmd = [ffprobe, "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height,avg_frame_rate,codec_name,duration",
           "-show_entries", "format=duration",
           "-of", "json", path]
    try:
        rc, out, err = _run(cmd, timeout=30)
    except Exception as e:
        return VideoStructure(path=path, ok=False, error="ffprobe 异常：%s: %s" % (type(e).__name__, e))
    if rc != 0:
        return VideoStructure(path=path, ok=False, error="ffprobe rc=%d：%s" % (rc, err.strip()[:200]))
    try:
        data = json.loads(out)
    except Exception:
        return VideoStructure(path=path, ok=False, error="ffprobe 输出非 JSON")
    streams = data.get("streams") or []
    if not streams:
        return VideoStructure(path=path, ok=False, error="无视频流")
    st = streams[0]
    dur = 0.0
    for src in (st.get("duration"), (data.get("format") or {}).get("duration")):
        try:
            dur = float(src)
            if dur > 0:
                break
        except (TypeError, ValueError):
            continue
    fps = 0.0
    afr = st.get("avg_frame_rate") or "0/0"
    try:
        num, _, den = afr.partition("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except Exception:
        fps = 0.0
    return VideoStructure(
        path=path, ok=True, duration_s=dur,
        width=int(st.get("width") or 0), height=int(st.get("height") or 0),
        fps=round(fps, 3), vcodec=st.get("codec_name") or "",
    )


# ============================================================
# 2. 场景切换检测（ffmpeg scene + showinfo）
# ============================================================
_PTS_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


def detect_scene_cuts(path: str, *, threshold: float = DEFAULT_SCENE_THRESHOLD,
                      ffmpeg: str = _FFMPEG, timeout: int = 120) -> List[float]:
    """返回镜头切换时间点列表（秒，升序）。检测失败返回 []（调用方应降级）。"""
    sel = "select='gt(scene,%.4f)',showinfo" % max(0.0, min(1.0, threshold))
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-i", path, "-filter:v", sel,
           "-an", "-f", "null", "-"]
    try:
        _, _, err = _run(cmd, timeout=timeout)
    except Exception:
        return []
    out: List[float] = []
    for line in err.splitlines():
        if "pts_time:" not in line or "showinfo" not in line:
            continue
        m = _PTS_RE.search(line)
        if not m:
            continue
        t = float(m.group(1))
        if not out or t - out[-1] >= 1e-3:
            out.append(t)
    return out


# ============================================================
# 3. 智能关键帧选择
# ============================================================
def select_keyframes(duration_s: float, cuts: Sequence[float], *,
                     max_frames: int = DEFAULT_MAX_FRAMES,
                     min_gap_s: float = DEFAULT_MIN_GAP_S,
                     fallback_frames: int = DEFAULT_FALLBACK_FRAMES
                     ) -> Tuple[List[Tuple[float, str]], str]:
    """在 ≤max_frames 的预算内挑关键帧。

    规则：必取首帧 + 尾帧；中间优先用镜头切换点；
    * 切换点 ≤ 剩余配额 → 全取
    * 切换点 >  剩余配额 → 沿时间轴均匀抽配额个
    * 一个切换点都没有 → fallback 均匀采样（mode 显式标记 fallback_uniform）
    """
    dur = float(duration_s or 0.0)
    if dur <= 0:
        return [], "none"
    max_frames = max(1, int(max_frames))
    picked: List[Tuple[float, str]] = []

    # 去重 + 最小间隔
    dedup: List[float] = []
    for c in sorted(float(x) for x in cuts):
        if c <= 0.05 or c >= dur - 0.05:
            continue
        if not dedup or c - dedup[-1] >= min_gap_s:
            dedup.append(c)

    if dedup:
        head_t = min(0.20, max(0.0, dur * 0.02))
        tail_t = max(head_t, dur - 0.20)
        reserved = 2 if max_frames >= 3 else 0
        quota = max(1, max_frames - reserved) if reserved else max_frames
        if len(dedup) <= quota:
            mid = dedup
        else:
            if quota == 1:
                mid = [dedup[len(dedup) // 2]]
            else:
                idxs = sorted({int(round(i * (len(dedup) - 1) / (quota - 1))) for i in range(quota)})
                mid = [dedup[i] for i in idxs]
        picked.append((head_t, "head"))
        picked.extend((t, "scene_cut") for t in mid)
        if reserved:
            picked.append((tail_t, "tail"))
        # 去重 + 截断
        seen, final = set(), []
        for t, why in sorted(picked, key=lambda x: x[0]):
            key = round(t, 3)
            if key in seen:
                continue
            seen.add(key)
            final.append((t, why))
        return final[:max_frames], "scene_cut"

    # 无切换点 → 均匀采样（显式降级标记）
    n = max(1, min(int(fallback_frames), max_frames))
    return [(dur * (i + 0.5) / n, "uniform") for i in range(n)], "fallback_uniform"


# ============================================================
# 4. 抽帧 + 编码
# ============================================================
def extract_frames(path: str, keyframes: Sequence[Tuple[float, str]], outdir: str, *,
                   width: int = DEFAULT_FRAME_WIDTH, jpeg_q: int = DEFAULT_JPEG_Q,
                   ffmpeg: str = _FFMPEG, timeout: int = 60) -> List[Keyframe]:
    """按时间点抽单帧 jpg。单帧失败只跳过该帧，不抛。"""
    os.makedirs(outdir, exist_ok=True)
    out: List[Keyframe] = []
    for i, (t, why) in enumerate(keyframes):
        fp = os.path.join(outdir, "kf_%02d_%s_%.2fs.jpg" % (i, why, t))
        vf = "scale='min(%d,iw)':-2" % int(width)
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-ss", "%.3f" % t, "-i", path,
               "-frames:v", "1", "-vf", vf, "-q:v", str(jpeg_q), fp]
        try:
            rc, _, _ = _run(cmd, timeout=timeout)
        except Exception:
            rc = -1
        if rc == 0 and os.path.exists(fp) and os.path.getsize(fp) > 0:
            out.append(Keyframe(idx=len(out), t=round(float(t), 3), reason=why,
                                path=fp, bytes_=os.path.getsize(fp)))
    return out


def encode_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


# ============================================================
# 5. 视觉模型调用（可注入）
# ============================================================
class OpenAIVisionClient:
    """OpenAI 兼容 /chat/completions 的多模态客户端（只发图，不写任何东西）。"""

    def __init__(self, base_url: str, api_key: str, model: str = DEFAULT_VISION_MODEL,
                 timeout: int = 120):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout

    def __call__(self, images_b64: Sequence[str], prompt: str) -> Dict[str, Any]:
        import urllib.request
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for b in images_b64:
            content.append({"type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,%s" % b}})
        payload = {"model": self.model, "temperature": 0,
                   "messages": [{"role": "user", "content": content}]}
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer %s" % self.api_key},
            method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
        text = ""
        try:
            text = body["choices"][0]["message"]["content"] or ""
        except Exception:
            text = ""
        return {"text": text, "usage": body.get("usage") or {},
                "model": body.get("model") or self.model, "raw_ok": True}


def call_vision_model(images_b64: Sequence[str], prompt: str = VISION_PROMPT, *,
                      client: Optional[Callable[[Sequence[str], str], Any]] = None,
                      model: str = DEFAULT_VISION_MODEL) -> Dict[str, Any]:
    """统一调用入口；client=None 时明确返回 not-called（离线安全，不偷偷联网）。"""
    t0 = time.time()
    meta: Dict[str, Any] = {"model": model, "called": False, "frames_sent": len(images_b64),
                            "elapsed_s": 0.0, "tokens": {}, "error": None}
    if not images_b64:
        meta["error"] = "没有可用关键帧，跳过视觉调用"
        return {"ok": False, "text": "", "meta": meta}
    if client is None:
        meta["error"] = "未注入视觉客户端（离线模式，未发起真实请求）"
        return {"ok": False, "text": "", "meta": meta}
    try:
        res = client(list(images_b64), prompt)
        if not isinstance(res, dict):
            raise TypeError("client 返回类型异常：%s" % type(res).__name__)
        meta["called"] = True
        meta["tokens"] = res.get("usage") or {}
        meta["model"] = res.get("model") or model
    except Exception as e:
        meta["called"] = True
        meta["error"] = "%s: %s" % (type(e).__name__, e)
        meta["elapsed_s"] = round(time.time() - t0, 3)
        return {"ok": False, "text": "", "meta": meta}
    meta["elapsed_s"] = round(time.time() - t0, 3)
    return {"ok": True, "text": res.get("text") or "", "meta": meta}


# ============================================================
# 6. 视觉文本 → 结构化视觉事实
# ============================================================
_FACT_KEYS = ("summary", "scenes", "entities", "on_screen_text",
              "actions", "evidence_sufficient", "confidence")


def parse_visual_facts(text: str) -> Optional[Dict[str, Any]]:
    """严格解析：剥 ``` 围栏 → 取首个 {...} → json。失败返回 None。"""
    if not isinstance(text, str) or not text.strip():
        return None
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        obj = json.loads(s[i:j + 1])
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return {k: obj[k] for k in _FACT_KEYS if k in obj} or None


def build_visual_facts(structure: VideoStructure, frames: Sequence[Keyframe],
                       vision: Dict[str, Any]) -> Dict[str, Any]:
    """组装 c5v.visual_facts.v1。"""
    facts = parse_visual_facts(vision.get("text") or "")
    errors: List[str] = []
    if structure.error:
        errors.append("structure: " + structure.error)
    if vision.get("meta", {}).get("error"):
        errors.append("vision: " + str(vision["meta"]["error"]))
    if vision.get("ok") and facts is None:
        errors.append("vision: 返回文本无法解析为结构化事实（已保留原文）")
    return {
        "schema": SCHEMA_VERSION,
        "module": {"name": MODULE_NAME, "stage": MODULE_STAGE},
        "video": {"source": structure.path, "duration_s": structure.duration_s,
                  "width": structure.width, "height": structure.height,
                  "fps": structure.fps, "vcodec": structure.vcodec},
        "keyframes": {
            "count": len(frames),
            "selection_mode": structure.selection_mode,
            "scene_cuts_detected": structure.n_scene_cuts,
            "items": [{"i": f.idx, "t": f.t, "reason": f.reason,
                       "bytes": f.bytes_} for f in frames],
        },
        "model": {
            "name": vision.get("meta", {}).get("model"),
            "called": bool(vision.get("meta", {}).get("called")),
            "frames_sent": vision.get("meta", {}).get("frames_sent", 0),
            "tokens": vision.get("meta", {}).get("tokens") or {},
            "elapsed_s": vision.get("meta", {}).get("elapsed_s", 0.0),
            "error": vision.get("meta", {}).get("error"),
        },
        "facts": facts,               # None = 没拿到可信事实，绝不编造
        "raw_text": (vision.get("text") or "")[:2000] or None,
        "errors": errors,
        "ok": bool(structure.ok and vision.get("ok") and facts is not None),
    }


def validate_visual_facts(obj: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """schema 校验（离线测试用；不联网）。"""
    problems: List[str] = []
    if not isinstance(obj, dict):
        return False, ["顶层不是 dict"]
    for k in ("schema", "video", "keyframes", "model", "facts", "errors", "ok"):
        if k not in obj:
            problems.append("缺字段：%s" % k)
    if obj.get("schema") != SCHEMA_VERSION:
        problems.append("schema 版本不符：%r" % obj.get("schema"))
    kf = obj.get("keyframes") or {}
    if not isinstance(kf.get("count"), int) or kf.get("count", 0) < 0:
        problems.append("keyframes.count 非法")
    if isinstance(kf.get("items"), list) and len(kf["items"]) != kf.get("count"):
        problems.append("keyframes.items 与 count 不一致")
    if kf.get("count", 0) > DEFAULT_MAX_FRAMES:
        problems.append("关键帧超上限")
    f = obj.get("facts")
    if f is not None:
        if not isinstance(f, dict):
            problems.append("facts 不是对象")
        else:
            for k in ("summary", "scenes", "entities", "actions", "evidence_sufficient"):
                if k not in f:
                    problems.append("facts 缺 %s" % k)
    return (len(problems) == 0), problems


# ============================================================
# 7. 主编排
# ============================================================
def analyze_video(path: str, *, client: Optional[Callable[..., Any]] = None,
                  workdir: Optional[str] = None, max_frames: int = DEFAULT_MAX_FRAMES,
                  scene_threshold: float = DEFAULT_SCENE_THRESHOLD,
                  frame_width: int = DEFAULT_FRAME_WIDTH,
                  cleanup: bool = False, **kw) -> Dict[str, Any]:
    """视频 → 结构化视觉事实（一次调用走完全链路，永不抛）。"""
    struct = probe_video(path)
    if not struct.ok:
        return build_visual_facts(struct, [], {"ok": False, "text": "",
                                               "meta": {"called": False, "frames_sent": 0,
                                                        "error": struct.error}})
    cuts = detect_scene_cuts(path, threshold=scene_threshold)
    struct.n_scene_cuts = len(cuts)
    picks, mode = select_keyframes(struct.duration_s, cuts, max_frames=max_frames)
    struct.selection_mode = mode

    tmp_created = False
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="c5v_frames_")
        tmp_created = True
    frames = extract_frames(path, picks, workdir, width=frame_width)
    for f in frames:
        try:
            f.b64 = encode_b64(f.path)
            f.bytes_ = os.path.getsize(f.path)
        except Exception:
            f.b64 = None

    usable = [f for f in frames if f.b64]
    vision = call_vision_model([f.b64 for f in usable], VISION_PROMPT, client=client,
                               model=kw.get("model", DEFAULT_VISION_MODEL))
    facts = build_visual_facts(struct, frames, vision)
    if cleanup and tmp_created:
        shutil.rmtree(workdir, ignore_errors=True)
    return facts


def facts_to_brief(facts: Dict[str, Any]) -> str:
    """把视觉事实压成一段可注入 Understand 的纯文本（本阶段不接线，仅备好接口）。"""
    if not isinstance(facts, dict) or not facts.get("ok") or not facts.get("facts"):
        return "视觉素材不可得（未取得可信画面事实）。"
    f = facts["facts"]
    kf = facts.get("keyframes") or {}
    lines = ["关键帧：%d 张（%s）" % (kf.get("count", 0), kf.get("selection_mode") or "未知"),
             "画面概括：%s" % (f.get("summary") or "无"),
             "置信度：%s" % f.get("confidence")]
    for s in (f.get("scenes") or [])[:6]:
        if isinstance(s, dict):
            lines.append(" - %s~%ss：%s" % (s.get("start_s"), s.get("end_s"),
                                            s.get("description")))
    if f.get("actions"):
        lines.append("事件顺序：%s" % " → ".join(str(a) for a in f["actions"][:8]))
    if f.get("on_screen_text"):
        lines.append("画面文字：%s" % " / ".join(str(x) for x in f["on_screen_text"][:6]))
    return chr(10).join(lines)


if __name__ == "__main__":   # 手动离线自检（不联网、不注入 client）
    import argparse
    ap = argparse.ArgumentParser(description="C.5-V-1 离线自检（默认不调用视觉模型）")
    ap.add_argument("video")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = analyze_video(a.video)
    print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else facts_to_brief(r))
