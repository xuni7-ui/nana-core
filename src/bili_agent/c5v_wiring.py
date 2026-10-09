#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
c5v_wiring.py — C.5-V-1 「视频视觉接线」适配层（隔离副本版）
================================================================
职责：把 `bili_video_vision` 的结构化视觉事实，接进 `bili_agent` 的
「视频素材」注入路径（`_video_material_brief` 之后追加一段画面事实）。

设计纪律（与 AGENTS.md §3 一致）
--------------------------------
1. **只增不改**：不改 `_video_material_brief` 的既有语义；只在它之后**追加**。
2. **默认关闭**：`NANA_C5V_WIRING` 未设为 1 → 本模块完全惰性，行为与现状一致。
3. **绝不编造**：拿不到视频文件 / 视觉接口失败 / 回复非 JSON →
   返回原文不变 + `reason`，**不注入任何画面描述**。
4. **不阻塞主链**：本模块所有函数**永不抛异常**到调用方。
5. **预算硬约束**：时长上限、抽帧上限、总超时、临时帧清理。
6. **零凭据硬编码**：真实视觉客户端只能由调用方注入，或从**环境变量**读；
   本文件不含任何 key。
7. **零生产依赖**：只 import `bili_video_vision`；不 import
   `bili_send_core / bili_event_pump / bili_video_read / nana_bili_health_check`。

接线点（生产应用时需姐姐授权，本副本内不碰生产）
------------------------------------------------
`bili_agent._understand()` 内，`material_block` 组装完之后：

    from c5v_wiring import augment_material_brief
    material_block, c5v_meta = await augment_material_brief(material_block, task.bvid)

未启用 / 失败时返回的 `material_block` 与原文**逐字节一致**。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

# ------------------------------------------------------------
# 0. 开关与默认预算
# ------------------------------------------------------------
_ENABLED_VALUES = ("1", "true", "on", "yes")

WIRING_ENABLED = os.environ.get("NANA_C5V_WIRING", "0").strip().lower() in _ENABLED_VALUES

DEFAULT_MAX_DURATION_S = 600      # 超长视频直接拒绝下载（保护磁盘/带宽）
DEFAULT_FETCH_TIMEOUT_S = 180     # yt-dlp 单次总超时
DEFAULT_MAX_FRAMES = 8            # 抽帧硬上限（与 c5v 模块一致）
DEFAULT_TOTAL_TIMEOUT_S = 240     # 视觉链路总预算（下载之外）

# 环境变量里可选的视觉端点（**不使用**即为离线）
_VISION_BASE_URL_ENV = "NANA_C5V_VISION_BASE_URL"
_VISION_API_KEY_ENV = "NANA_C5V_VISION_API_KEY"
_VISION_MODEL_ENV = "NANA_C5V_VISION_MODEL"


@dataclass
class Budget:
    """一次视觉接线的资源预算。全部有硬上限，超了就走降级路径。"""
    max_duration_s: float = DEFAULT_MAX_DURATION_S
    max_frames: int = DEFAULT_MAX_FRAMES
    fetch_timeout_s: int = DEFAULT_FETCH_TIMEOUT_S
    total_timeout_s: int = DEFAULT_TOTAL_TIMEOUT_S
    frame_width: int = 640
    cleanup: bool = True


@dataclass
class WiringResult:
    """接线结果。`available=False` 时 `brief` 必须为空串。"""
    ok: bool = False
    available: bool = False
    brief: str = ""
    reason: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_meta(self) -> Dict[str, Any]:
        return {"ok": self.ok, "available": self.available,
                "reason": self.reason, "meta": self.meta}


# ------------------------------------------------------------
# 1. 视频文件获取（可插拔；默认 yt-dlp，可被测试注入）
# ------------------------------------------------------------
class YtDlpFetcher:
    """用已安装的 yt-dlp 取 B站视频到本地（只读站方，不写站方）。

    * 只取**单个**视频（`--no-playlist`）；
    * 分辨率上限 480p（降 token 与带宽）；
    * 失败返回 None，不抛。
    """

    def __init__(self, ytdlp: Optional[str] = None, *, max_height: int = 480):
        self.ytdlp = ytdlp or os.environ.get("NANA_C5V_YTDLP", "yt-dlp")
        self.max_height = max_height

    def __call__(self, bvid: str, dest_dir: str, *, timeout_s: int = DEFAULT_FETCH_TIMEOUT_S
                 ) -> Optional[str]:
        if not bvid:
            return None
        os.makedirs(dest_dir, exist_ok=True)
        url = "https://www.bilibili.com/video/%s" % bvid
        tmpl = os.path.join(dest_dir, "%s.%%(ext)s" % bvid)
        cmd = [self.ytdlp, "--no-playlist", "--no-warnings", "--quiet",
               "-f", "best[height<=%d]/best" % self.max_height,
               "--max-filesize", "120M", "-o", tmpl, url]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=max(1, int(timeout_s)), check=False)
        except Exception:
            return None
        for name in sorted(os.listdir(dest_dir)):
            if name.startswith(bvid + ".") and not name.endswith((".part", ".ytdl")):
                return os.path.join(dest_dir, name)
        return None


def _make_vision_client() -> Optional[Callable[[Any, str], Any]]:
    """按环境变量构造真实视觉客户端；缺任一变量 → 返回 None（离线，不联网）。"""
    base = (os.environ.get(_VISION_BASE_URL_ENV) or "").strip()
    key = (os.environ.get(_VISION_API_KEY_ENV) or "").strip()
    if not base or not key:
        return None
    try:
        from bili_video_vision import OpenAIVisionClient
        model = (os.environ.get(_VISION_MODEL_ENV) or "deepseek-flash").strip()
        return OpenAIVisionClient(base, key, model=model)
    except Exception:
        return None


# ------------------------------------------------------------
# 2. 主入口：BVID → 结构化视觉事实 → 一段可注入文本
# ------------------------------------------------------------
def _c5v():
    """惰性加载 `bili_video_vision`；必要时把同仓 `src/c5v/` 挂上 sys.path。"""
    import sys
    try:
        import bili_video_vision as m
        return m
    except ImportError:
        cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "c5v")
        cand = os.path.normpath(cand)
        if cand not in sys.path:
            sys.path.insert(0, cand)
        import bili_video_vision as m
        return m


def vision_brief(bvid: str = "", *, video_path: Optional[str] = None,
                 client: Any = None, fetcher: Any = None,
                 budget: Optional[Budget] = None,
                 tmp_root: Optional[str] = None) -> WiringResult:
    """取视频 → 抽帧 → 视觉模型 → 结构化事实 → 压成一段文本。

    * `video_path` 显式给出时**不下载**（离线测试走这条）；
    * `client=None` 且环境变量未配 → 明确 `available=False`，不联网；
    * 任何异常都被吞掉并如实记入 `reason`，**绝不抛**。
    """
    b = budget or Budget()
    t0 = time.time()
    res = WiringResult()

    # --- 取源文件 ---
    tmp_created = []
    src = (video_path or "").strip() or None
    try:
        if not src:
            if not bvid:
                res.reason = "任务未提供 BVID，且未给出本地视频路径"
                return res
            root = tmp_root or tempfile.mkdtemp(prefix="c5v_fetch_")
            tmp_created.append(root)
            f = fetcher or YtDlpFetcher()
            src = f(bvid, root, timeout_s=b.fetch_timeout_s)
        if not src or not os.path.exists(src):
            res.reason = "视频文件不可得（下载失败或不存在），不注入画面事实"
            return res

        # --- 预算：时长上限 ---
        c5v = _c5v()
        struct = c5v.probe_video(src)
        if not struct.ok:
            res.reason = "视频结构不可读：%s" % (struct.error or "未知")
            return res
        if struct.duration_s and struct.duration_s > b.max_duration_s:
            res.reason = ("视频时长 %.0fs 超过预算上限 %.0fs，已跳过视觉理解"
                          % (struct.duration_s, b.max_duration_s))
            res.meta = {"duration_s": struct.duration_s, "limit_s": b.max_duration_s}
            return res

        # --- 视觉链路 ---
        use_client = client if client is not None else _make_vision_client()
        if use_client is None:
            res.reason = ("未配置视觉客户端（离线模式，未发起任何真实请求）")
            res.meta = {"duration_s": struct.duration_s, "offline": True}
            return res

        workdir = tmp_root or tempfile.mkdtemp(prefix="c5v_frames_")
        tmp_created.append(workdir)
        facts = c5v.analyze_video(src, client=use_client, workdir=workdir,
                                  max_frames=b.max_frames, frame_width=b.frame_width)
        if time.time() - t0 > b.total_timeout_s:
            res.reason = "视觉链路超出总预算 %.0fs，结果丢弃" % b.total_timeout_s
            return res
        if not facts.get("ok") or not facts.get("facts"):
            res.reason = "视觉事实不可信（%s），不注入" % (
                "；".join(facts.get("errors") or []) or "未取得结构化事实")
            res.meta = {"errors": facts.get("errors") or []}
            return res

        brief = c5v.facts_to_brief(facts)
        kf = facts.get("keyframes") or {}
        res.ok = True
        res.available = True
        res.brief = brief
        res.reason = "视觉事实可用"
        res.meta = {"duration_s": struct.duration_s,
                    "keyframes": kf.get("count"),
                    "selection_mode": kf.get("selection_mode"),
                    "facts_schema": facts.get("schema")}
        return res
    except Exception as e:                                  # 永不抛到主链
        res.reason = "接线层异常（已吞）：%s: %s" % (type(e).__name__, e)
        return res
    finally:
        if b.cleanup:
            for d in tmp_created:
                shutil.rmtree(d, ignore_errors=True)


# ------------------------------------------------------------
# 3. 注入点：给现有素材块追加画面事实（失败则原样返回）
# ------------------------------------------------------------
C5V_MATERIAL_RULE = (
    "\n\n【画面事实纪律】\n"
    "- 下方「画面事实」来自对当前视频**关键帧**的机器理解，**不是**你亲眼看过视频的等价物。\n"
    "- 它只用于核对评论与画面是否对得上；与评论冲突时，以评论内容为主。\n"
    "- 若写「视觉素材不可得」，则必须按「素材不足」处理，**禁止**凭标题想象画面。\n"
)


def render_block(result: WiringResult) -> str:
    """把可用结果渲染成注入文本；不可用则返回空串。"""
    if not result.ok or not result.available or not result.brief:
        return ""
    return C5V_MATERIAL_RULE + "【画面事实】\n" + result.brief


async def augment_material_brief(brief: str, bvid: str = "", *,
                                 video_path: Optional[str] = None,
                                 client: Any = None, fetcher: Any = None,
                                 budget: Optional[Budget] = None) -> tuple:
    """接线入口：返回 `(新素材块, meta)`。

    未启用 / 不可用时，新素材块与入参**逐字节一致**（调用方可安全全量替换）。
    """
    if not WIRING_ENABLED:
        return brief, {"enabled": False, "available": False}
    r = vision_brief(bvid, video_path=video_path, client=client, fetcher=fetcher,
                     budget=budget)
    m = r.as_meta()
    m["enabled"] = True
    if not r.ok:
        return brief, m
    block = render_block(r)
    if not block:
        return brief, m
    return (brief or "") + block, m


def facts_brief_for_understand(bvid: str, **kw) -> str:
    """给 `_understand` 的便捷封装：直接返回可拼接文本（不可用返回空串）。"""
    return render_block(vision_brief(bvid, **kw))
