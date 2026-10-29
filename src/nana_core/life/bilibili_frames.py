"""Bounded publisher storyboard frames and original H1 semantic grounding.

No whole-video download, ffmpeg shell or ambient account. A storyboard is a
sampled frame excerpt; subtitles/comments do not substitute for visual evidence.
Pillow is an explicit optional Runtime dependency and missing support fails closed.
All image bytes, timestamps and later model beliefs depend on original Memory.
"""

import base64
from dataclasses import dataclass, field
import hashlib
import io
import json
import math
import warnings

from ..contracts import CoreError
from ..continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from ..continuity.memory import MemoryService
from ..storage import canonical, digest


@dataclass(frozen=True, repr=False)
class VideoFrame:
    bvid: str
    cid: int
    at_seconds: float
    png: bytes = field(repr=False)
    origin: str


def acquire_frames(transport, bvid, cid, *, limit=3):
    from PIL import Image

    if type(limit) is not int or not 1 <= limit <= 3:
        raise CoreError("BILIBILI_FRAME_BOUND")
    data = transport._get("/x/player/videoshot", {"bvid": bvid, "cid": cid, "index": 1})
    try:
        times, images = data["index"], data["image"]
        width, height, columns, rows = [data[k] for k in ("img_x_size", "img_y_size", "img_x_len", "img_y_len")]
        if (
            type(times) is not list
            or not 1 <= len(times) <= 10000
            or type(images) is not list
            or not 1 <= len(images) <= 64
            or any(type(v) is not int or not 1 <= v <= 4096 for v in (width, height, columns, rows))
            or width * height * columns * rows > 4_000_000
            or any(type(t) not in (int, float) or not math.isfinite(t) or not 0 <= t <= 86400 for t in times)
            or times != sorted(set(times))
            or len(times) > len(images) * columns * rows
        ):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise CoreError("BILIBILI_STORYBOARD_INVALID") from None
    # Same bounded coverage selection as legacy C5-V's uniform fallback; the
    # actual timestamps remain explicit and gaps never become observed video.
    picks = sorted({round(i * (len(times) - 1) / max(1, limit - 1)) for i in range(limit)})
    cache, output = {}, []
    try:
        for index in picks:
            sheet_index, tile = divmod(index, columns * rows)
            if sheet_index not in cache:
                url = images[sheet_index]
                if type(url) is not str:
                    raise ValueError()
                if url.startswith("//"):
                    url = "https:" + url
                raw = transport._raw(url, image=True)
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(raw), formats=("JPEG", "PNG")) as image:
                        if image.size != (width * columns, height * rows):
                            raise ValueError()
                        image.load()
                        cache[sheet_index] = image.convert("RGB")
            x, y = tile % columns * width, tile // columns * height
            frame = cache[sheet_index].crop((x, y, x + width, y + height))
            frame.thumbnail((192, 128))
            out = io.BytesIO()
            frame.save(out, format="PNG")
            if len(out.getvalue()) > 49152:
                raise CoreError("BILIBILI_FRAME_BYTE_BOUND")
            output.append(VideoFrame(bvid, cid, float(times[index]), out.getvalue(), transport.origin))
    except (OSError, ValueError, SyntaxError, Warning):
        raise CoreError("BILIBILI_STORYBOARD_IMAGE_INVALID") from None
    return tuple(output)


class BilibiliFrameService:
    def __init__(self, app):
        self.app, self.runtime = app, app.runtime
        self.memory = MemoryService(app.runtime.store)

    def coverage(self, source_memory_id):
        out = []
        for row in self.runtime.store.db.execute(
            "SELECT m.memory_id FROM memory_dependencies d JOIN memories m ON d.memory_id=m.memory_id "
            "JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE d.parent_kind='MEMORY' AND d.parent_id=? "
            "AND m.lifecycle='ACTIVE' AND e.source_namespace IN ('recorded.bilibili.public.frames','recorded.project.bilibili.frames') LIMIT 3",
            (source_memory_id,),
        ):
            try:
                source = self.memory.read(row[0])
                out.append(
                    {"source_memory_id": row[0], "at_seconds": json.loads(source["text"])["source"]["at_seconds"]}
                )
            except CoreError:
                continue
        return {"visual_frames": len(out), "frame_samples": out, "full_video_watched": False}

    def capture(self, source_memory_id, frames):
        from ..continuity.world_loop.perception import MediaDecoder

        source = self.memory.read(source_memory_id)
        body = json.loads(source["text"])
        if (
            source["source_provenance"]["source_namespace"]
            not in {"recorded.bilibili.public", "recorded.project.bilibili"}
            or body["kind"] != "VIDEO_READING"
            or not 1 <= len(frames) <= 3
        ):
            raise CoreError("BILIBILI_FRAME_SOURCE_REQUIRED")
        result = []
        for frame in frames:
            if (
                type(frame) is not VideoFrame
                or frame.bvid != body["data"]["bvid"]
                or frame.cid != body["data"]["cid"]
                or frame.origin != body["origin"]
                or not math.isfinite(frame.at_seconds)
                or not 0 <= frame.at_seconds <= 86400
                or type(frame.png) is not bytes
                or not 1 <= len(frame.png) <= 49152
            ):
                raise CoreError("BILIBILI_FRAME_CORRELATION_MISMATCH")
            decoded = MediaDecoder().decode(frame.png, "IMAGE")
            text = canonical(
                {
                    "source_byte_digest": hashlib.sha256(frame.png).hexdigest(),
                    "decoded": decoded,
                    "source": {
                        "bvid": frame.bvid,
                        "cid": frame.cid,
                        "at_seconds": frame.at_seconds,
                        "origin": frame.origin,
                        "coverage": "PUBLISHER_STORYBOARD_SAMPLE_NOT_FULL_WATCH",
                    },
                    "png_b64": base64.b64encode(frame.png).decode(),
                }
            )
            reference = digest([source_memory_id, frame.at_seconds, hashlib.sha256(frame.png).hexdigest()])
            p = source["source_provenance"]
            prior = self.runtime.store.db.execute(
                "SELECT evidence_id FROM continuity_evidence WHERE source_namespace=? AND source_reference=?",
                (p["source_namespace"] + ".frames", reference),
            ).fetchone()
            eid = (
                prior[0]
                if prior
                else self.memory.capture(
                    EvidenceInput(
                        provenance=Provenance(
                            domain=p["domain"],
                            source_namespace=p["source_namespace"] + ".frames",
                            source_reference=reference,
                            source_kind="DIRECT_OBSERVATION",
                            coverage="EXCERPT",
                        ),
                        text=text,
                        privacy_class=source["privacy_class"],
                        observed_time_us=source["observed_time_us"],
                    )
                )
            )
            result.append(
                self.memory.add(
                    MemoryCandidate(
                        entity_id=source["entity_id"],
                        scope=source["scope"],
                        memory_type=MemoryType.EPISODIC,
                        epistemic_kind="OBSERVATION",
                        text=text,
                        source_evidence_id=eid,
                        derived_from=(source_memory_id,),
                    )
                )
            )
        return tuple(result)

    def interpret(self, frame_memory_id):
        """One original budgeted VISION call; H1 owns interpretation and World."""
        from ..continuity.provider_routing import RouteRequest
        from ..continuity.world_loop.semantics import MediaSemanticService
        from ..continuity.world_loop.cognition import CognitionBudget
        from .readiness import budget

        source = self.memory.read(frame_memory_id)
        if source["source_provenance"]["source_namespace"] not in {
            "recorded.bilibili.public.frames",
            "recorded.project.bilibili.frames",
        }:
            raise CoreError("BILIBILI_FRAME_SOURCE_REQUIRED")
        if self.app.router is None:
            raise CoreError("LIVE_PROVIDER_NOT_RUN_OFFLINE_MODE")
        from ..presence.resources import resource_state

        if resource_state(self.runtime.store, self.runtime.config).unresolved_calls:
            raise CoreError("UNRESOLVED_PROVIDER_CALL_NO_RETRY")
        cfg = self.app.config
        target = self.app.router.resolve(
            RouteRequest(
                operation="VISION",
                input_modalities=("IMAGE",),
                privacy_class=source["privacy_class"],
                timeout_ms=cfg.provider_timeout_ms,
                cost_ceiling=cfg.provider_cost_ceiling_micro,
                context_limit=cfg.provider_context_tokens,
                output_limit=cfg.provider_output_tokens,
            ),
            self.app.policy,
        )
        budget(self.app, target.snapshot)
        session = target.cognition_session(self.runtime)
        session.recover()
        if resource_state(self.runtime.store, self.runtime.config).unresolved_calls:
            raise CoreError("UNRESOLVED_PROVIDER_CALL_NO_RETRY")
        semantic = MediaSemanticService(session)
        data = base64.b64decode(json.loads(source["text"])["png_b64"], validate=True)
        request = semantic.prepare(
            "bilibili-frame:" + frame_memory_id,
            frame_memory_id,
            data,
            budget=CognitionBudget(
                input_tokens=cfg.provider_context_tokens,
                output_tokens=cfg.provider_output_tokens,
                timeout_ms=cfg.provider_timeout_ms,
                cost_ceiling_micro=cfg.provider_cost_ceiling_micro,
            ),
        )
        result = semantic.execute(request)
        if result["state"] != "PROPOSED":
            return {"state": result["state"], "request_id": request, "no_retry": True}
        grounded = semantic.ground(
            request, entity_id="bili-frame:" + digest(frame_memory_id)[:24], predicate="publication.visual"
        )
        return {"state": "SAMPLED_FRAME_INTERPRETED", "request_id": request, **grounded, "full_video_watched": False}
