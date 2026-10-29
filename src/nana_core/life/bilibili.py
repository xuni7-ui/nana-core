"""Bilibili public source adapter into original Memory/World/Concern/C.

The legacy C.5 reader's bounded metadata/subtitle semantics are preserved. Its
ambient cookie path and separate LLM are deliberately not imported into Core.
No platform brain, account discovery, social sender or second history database.
"""

import html
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from types import MappingProxyType
from pydantic import Field

from ..contracts import CoreError, DTO, Invocation, Receipt, Verification
from ..storage import canonical, digest
from ..continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from ..continuity.memory import MemoryService
from ..continuity.records import RecordService


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class BilibiliLoopbackOpener:
    """Explicit synthetic HTTP counterpart; never discovers a remote endpoint."""
    def __init__(self, endpoint):
        parsed = urllib.parse.urlsplit(endpoint)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}
                or parsed.username or parsed.password or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or not parsed.port or any(c in endpoint for c in "\\\r\n")):
            raise CoreError("BILIBILI_LITERAL_LOOPBACK_REQUIRED")
        self.endpoint = endpoint.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def open(self, request, timeout):
        parsed = urllib.parse.urlsplit(request.full_url)
        suffix = parsed.path + ("?" + parsed.query if parsed.query else "")
        forwarded = urllib.request.Request(self.endpoint + suffix, data=request.data,
            headers=dict(request.header_items()), method=request.get_method())
        return self.opener.open(forwarded, timeout=timeout)


def plain(text, bound):
    return html.unescape(re.sub(r"<[^>]*>", "", str(text or "")))[:bound]


@dataclass(frozen=True, repr=False)
class PublicReading:
    reference: str
    kind: str
    observed_at_us: int
    payload: dict = field(repr=False)
    origin: str = "REAL_PLATFORM_HTTP"
    frames: tuple = field(default=(), repr=False)


class BilibiliPublicTransport:
    """Fixed public endpoints, no cookies/auth/redirects or blind retries.

    A trusted caller supplies read authorization; production autonomous callers
    must additionally dispatch through the original Kernel/Grant boundary.
    """
    def __init__(self, *, authorized=False, request_limit=8, origin="REAL_PLATFORM_HTTP", loopback_endpoint=None):
        if origin not in {"REAL_PLATFORM_HTTP", "SYNTHETIC_FIXTURE"}:
            raise CoreError("BILIBILI_SOURCE_ORIGIN_UNVERIFIED")
        self.authorized = authorized is True
        self.origin = origin
        self.request_limit = min(max(request_limit, 0), 16)
        self.calls = 0
        self.last_http_status = None
        self.last_api_code = None
        if loopback_endpoint is not None and origin != "SYNTHETIC_FIXTURE":
            raise CoreError("BILIBILI_LOOPBACK_ORIGIN_REQUIRED")
        self.opener = (BilibiliLoopbackOpener(loopback_endpoint) if loopback_endpoint is not None
                       else urllib.request.build_opener(NoRedirect()))

    def _raw(self, url, *, image=False):
        if not self.authorized:
            raise CoreError("BILIBILI_READ_NOT_AUTHORIZED")
        if self.calls >= self.request_limit:
            raise CoreError("BILIBILI_READ_BUDGET")
        try:
            parsed = urllib.parse.urlsplit(url)
            invalid = parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port
        except ValueError:
            raise CoreError("BILIBILI_ENDPOINT_DENIED") from None
        hosts = {'i0.hdslb.com', 'i1.hdslb.com', 'i2.hdslb.com'} if image else {"api.bilibili.com", "aisubtitle.hdslb.com"}
        if invalid or parsed.hostname not in hosts or (image and (parsed.query or not parsed.path.lower().endswith(('.jpg', '.jpeg', '.png')))):
            raise CoreError("BILIBILI_ENDPOINT_DENIED")
        self.calls += 1
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "NanaCore/4 source-aware public reader"})
        try:
            with self.opener.open(request, timeout=5) as response:
                self.last_http_status = response.status
                raw = response.read((1048576 if image else 262144) + 1)
        except urllib.error.HTTPError as exc:
            self.last_http_status = exc.code
            raise CoreError("BILIBILI_HTTP_UNAVAILABLE") from None
        except (OSError, http.client.HTTPException):
            raise CoreError("BILIBILI_READ_UNKNOWN_NO_RETRY") from None
        if len(raw) > (1048576 if image else 262144):
            raise CoreError("BILIBILI_RESPONSE_BOUND")
        return raw

    def _get(self, path, query):
        if path not in {"/x/web-interface/search/type", "/x/web-interface/view", "/x/web-interface/archive/related",
                        "/x/player/v2", "/x/player/videoshot", "/x/v2/reply"}:
            raise CoreError("BILIBILI_ENDPOINT_DENIED")
        raw = self._raw("https://api.bilibili.com" + path + "?" + urllib.parse.urlencode(query))
        try:
            from ..continuity.privacy import _json_object
            value = json.loads(raw, object_pairs_hook=_json_object)
        except (ValueError, UnicodeError):
            raise CoreError("BILIBILI_RESPONSE_INVALID") from None
        self.last_api_code = value.get("code") if type(value) is dict else None
        if type(value) is not dict or value.get("code") != 0:
            raise CoreError("BILIBILI_API_UNAVAILABLE")
        return value.get("data")

    @staticmethod
    def _video(item):
        bvid = item.get("bvid")
        if type(bvid) is not str or not re.fullmatch(r"BV[A-Za-z0-9]{10}", bvid):
            raise CoreError("BILIBILI_VIDEO_ID_INVALID")
        return {"bvid": bvid, "title": plain(item.get("title"), 192),
                "description": plain(item.get("desc", item.get("description")), 1024),
                "publisher": plain((item.get("owner") or {}).get("name", item.get("author")), 96),
                "aid": item.get("aid"), "cid": item.get("cid") or ((item.get("pages") or [{}])[0].get("cid")),
                "duration_seconds": item.get("duration"),
                "coverage": "METADATA_ONLY_NOT_WATCHED", "transcript": None, "visual_frames": 0}

    def search(self, query):
        if type(query) is not str or not 1 <= len(query) <= 64 or any(ord(c) < 32 for c in query):
            raise CoreError("BILIBILI_QUERY_BOUND")
        data = self._get("/x/web-interface/search/type", {"search_type": "video", "keyword": query, "page": 1})
        if type(data) is not dict or type(data.get("result")) is not list:
            raise CoreError("BILIBILI_RESPONSE_INVALID")
        rows = []
        omitted = 0
        for row in data["result"][:8]:
            if (type(row) is not dict or type(row.get("bvid")) is not str
                    or not re.fullmatch(r"BV[A-Za-z0-9]{10}", row["bvid"])):
                omitted += 1
                continue
            rows.append(self._video(row))
        return PublicReading("search:" + digest(query)[:32], "DISCOVERY", time.time_ns() // 1000,
                             {"query": query, "candidates": rows, "omitted_non_video_rows": omitted,
                              "selection": "REQUIRES_ORIGINAL_C_JUDGMENT"}, self.origin)

    def video(self, bvid):
        if type(bvid) is not str or not re.fullmatch(r"BV[A-Za-z0-9]{10}", bvid):
            raise CoreError("BILIBILI_VIDEO_ID_INVALID")
        data = self._get("/x/web-interface/view", {"bvid": bvid})
        if type(data) is not dict or data.get("bvid") != bvid:
            raise CoreError("BILIBILI_VIDEO_CORRELATION_MISMATCH")
        return PublicReading(bvid, "VIDEO_METADATA", time.time_ns() // 1000, self._video(data), self.origin)

    def read_video(self, bvid, *, subtitles=True, comments=True, danmaku=True, visual=False):
        """Fetch bounded actual materials, preserving which part was observed.

        Subtitle text is an excerpt with timestamps, comments are attributed to
        commenters, and no download or model call is disguised as visual viewing.
        Each optional source is tried once; failures do not repeat another call.
        """
        metadata = self.video(bvid)
        body = dict(metadata.payload)
        body.update(subtitle_segments=[], comment_samples=[], danmaku_samples=[], notes=[],
                    timeline_basis="NONE", watched=False)
        aid, cid = body.get("aid"), body.get("cid")
        if type(aid) is not int or type(cid) is not int or min(aid, cid) < 1:
            body["notes"].append("MATERIAL_IDENTITY_UNAVAILABLE")
            return PublicReading(bvid, "VIDEO_READING", metadata.observed_at_us, body, self.origin)
        operations = []
        if subtitles:
            operations.append(("subtitle_segments", lambda: self._subtitles(bvid, aid, cid)))
        if comments:
            operations.append(("comment_samples", lambda: self.comments(aid)))
        if danmaku:
            operations.append(("danmaku_samples", lambda: self.danmaku(cid)))
        for name, read in operations:
            try:
                body[name] = read()
            except CoreError as exc:
                body["notes"].append(name.upper() + ":" + exc.code)
        if body["subtitle_segments"]:
            body["coverage"] = "SUBTITLE_EXCERPT_NOT_VISUAL_VIEWING"
            body["timeline_basis"] = "PUBLISHER_SUBTITLE_TIMESTAMPS"
            body["transcript"] = " ".join(row["text"] for row in body["subtitle_segments"])
        elif body["comment_samples"] or body["danmaku_samples"]:
            body["coverage"] = "SOCIAL_CONTEXT_ONLY_NOT_VIDEO_CONTENT"
        frames = ()
        if visual:
            try:
                from .bilibili_frames import acquire_frames
                frames = acquire_frames(self, bvid, cid)
                body['visual_frames'] = len(frames)
                body['frame_timestamps_seconds'] = [f.at_seconds for f in frames]
                body['coverage'] = 'SAMPLED_VIDEO_FRAMES_NOT_FULL_WATCH'
            except (CoreError, ImportError) as exc:
                body['notes'].append('VISUAL_FRAMES:' + (exc.code if isinstance(exc, CoreError) else 'FRAME_DECODER_UNAVAILABLE'))
        return PublicReading(bvid, "VIDEO_READING", metadata.observed_at_us, body, self.origin, frames)

    def _subtitles(self, bvid, aid, cid):
        info = self._get("/x/player/v2", {"bvid": bvid, "aid": aid, "cid": cid})
        if type(info) is not dict:
            raise CoreError("BILIBILI_RESPONSE_INVALID")
        subtitle = info.get("subtitle") or {}
        if type(subtitle) is not dict:
            raise CoreError("BILIBILI_SUBTITLE_INVALID")
        rows = subtitle.get("subtitles") or []
        if not rows:
            return []
        if type(rows) is not list or type(rows[0]) is not dict or type(rows[0].get("subtitle_url")) is not str:
            raise CoreError("BILIBILI_SUBTITLE_INVALID")
        url = rows[0].get("subtitle_url", "")
        if url.startswith("//"):
            url = "https:" + url
        if urllib.parse.urlsplit(url).hostname != "aisubtitle.hdslb.com":
            raise CoreError("BILIBILI_SUBTITLE_HOST_DENIED")
        try:
            value = json.loads(self._raw(url))
            segments = value["body"]
        except (ValueError, KeyError, TypeError):
            raise CoreError("BILIBILI_SUBTITLE_INVALID") from None
        out = []
        if type(segments) is not list:
            raise CoreError("BILIBILI_SUBTITLE_INVALID")
        for item in segments[:20]:
            if type(item) is not dict:
                raise CoreError("BILIBILI_SUBTITLE_INVALID")
            start, end = item.get("from"), item.get("to")
            if type(start) not in (int, float) or type(end) not in (int, float) or not 0 <= start <= end <= 86400:
                raise CoreError("BILIBILI_SUBTITLE_TIMELINE_INVALID")
            text = plain(item.get("content"), 96)
            if text:
                out.append({"from_seconds": start, "to_seconds": end, "text": text, "source": "PUBLISHER_SUBTITLE"})
        return out

    def comments(self, aid):
        if type(aid) is not int or aid < 1:
            raise CoreError("BILIBILI_MATERIAL_IDENTITY_REQUIRED")
        data = self._get("/x/v2/reply", {"type": 1, "oid": aid, "pn": 1, "ps": 8, "sort": 2})
        if type(data) is not dict:
            raise CoreError("BILIBILI_RESPONSE_INVALID")
        return [{"reply_id": str(row.get("rpid", "")), "author_id": str((row.get("member") or {}).get("mid", "")),
                 "text": plain((row.get("content") or {}).get("message"), 128), "source": "PUBLIC_COMMENT_NOT_PUBLISHER_FACT"}
                for row in (data.get("replies") or [])[:6] if type(row) is dict]

    def danmaku(self, cid):
        if type(cid) is not int or cid < 1:
            raise CoreError("BILIBILI_MATERIAL_IDENTITY_REQUIRED")
        raw = self._raw("https://api.bilibili.com/x/v1/dm/list.so?" + urllib.parse.urlencode({"oid": cid}))
        if b"\x00" in raw or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise CoreError("BILIBILI_DANMAKU_XML_DENIED")
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(raw)
            if root.tag != "i":
                raise ValueError()
            rows = []
            for node in root.findall("d")[:16]:
                offset = float(node.get("p", "").split(",")[0])
                if not 0 <= offset <= 86400:
                    raise ValueError()
                rows.append({"at_seconds": offset, "text": plain(node.text, 64), "source": "PUBLIC_DANMAKU_NOT_PUBLISHER_FACT"})
            return rows
        except (ET.ParseError, ValueError):
            raise CoreError("BILIBILI_DANMAKU_INVALID") from None


class BilibiliSourceAdapter:
    """Trusted platform receipts only; untrusted publication is still data."""
    def __init__(self, app):
        self.app = app

    def ingest(self, reading, *, parents=()):
        if type(reading) is not PublicReading or reading.kind not in {"DISCOVERY", "VIDEO_METADATA", "VIDEO_READING"}:
            raise CoreError("BILIBILI_TYPED_RECEIPT_REQUIRED")
        if type(reading.payload) is not dict or type(reading.reference) is not str or not 1 <= len(reading.reference) <= 128:
            raise CoreError("BILIBILI_TYPED_RECEIPT_REQUIRED")
        runtime = self.app.runtime
        memory = MemoryService(runtime.store)
        fixture = reading.origin == "SYNTHETIC_FIXTURE"
        if reading.origin not in {"REAL_PLATFORM_HTTP", "SYNTHETIC_FIXTURE"}:
            raise CoreError("BILIBILI_SOURCE_ORIGIN_UNVERIFIED")
        body = canonical({"platform": "bilibili", "kind": reading.kind, "origin": reading.origin,
                          "data": reading.payload,
                          "publication_is_not_authority": True, "watched": False})
        if len(body.encode()) > 24576:
            raise CoreError("BILIBILI_RECEIPT_BOUND")
        reference = digest([reading.reference, digest(body), list(parents)]) if parents else digest([reading.reference, digest(body)])
        namespace = "recorded.project.bilibili" if fixture else "recorded.bilibili.public"
        old = runtime.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace=? AND source_reference=?", (namespace, reference)).fetchone()
        evidence = memory.capture(EvidenceInput(
            provenance=Provenance(domain="DEVELOPMENT_PROJECT" if fixture else "RECORDED_PUBLIC",
                                  source_namespace=namespace, source_reference=reference,
                                  source_kind="DIRECT_OBSERVATION", coverage="EXCERPT"),
            text=body, privacy_class="PROJECT" if fixture else "PUBLIC",
            observed_time_us=old[0] if old else reading.observed_at_us,
        ))
        prior = runtime.store.db.execute("SELECT memory_id FROM memories WHERE source_evidence_id=?", (evidence,)).fetchone()
        if prior:
            memory.read(prior[0])  # Tombstone remains authoritative.
            return prior[0]
        return memory.add(MemoryCandidate(entity_id=runtime.config.entity_id, scope=runtime.config.scopes[0],
                                         memory_type=MemoryType.EPISODIC, epistemic_kind="OBSERVATION",
                                         source_evidence_id=evidence, text=body, derived_from=parents))

    def interpret(self, memory_id):
        """One original budgeted cognition; interpretation never claims viewing."""
        source = RecordService(self.app.runtime.store).memory.read(memory_id)
        if source["source_provenance"]["source_namespace"] not in {"recorded.project.bilibili", "recorded.bilibili.public"}:
            raise CoreError("BILIBILI_SOURCE_BINDING_REQUIRED")
        session = self.app._session(source["privacy_class"])
        from ..continuity.world_loop.cognition import CognitionBudget
        cfg = self.app.config
        request = session.prepare("bilibili.interpret." + memory_id, "INTERPRET", (memory_id,),
            budget=CognitionBudget(input_tokens=cfg.provider_context_tokens, output_tokens=cfg.provider_output_tokens,
                                   timeout_ms=cfg.provider_timeout_ms, cost_ceiling_micro=cfg.provider_cost_ceiling_micro),
            pinned_only=True)
        result = session.execute(request)
        if result["state"] != "PROPOSED":
            return {"state": result["state"], "request_id": request, "no_retry": True}
        return self.apply_proposal(memory_id, session, result["record_id"])

    def apply_proposal(self, memory_id, session, proposal_id, *, enqueue=True):
        from ..continuity.world_loop.world import WorldModel, SourcedClaim
        from ..continuity.world_loop.attention import ConcernService
        from ..continuity.open_life.sources import remember
        runtime = self.app.runtime
        if memory_id not in RecordService(runtime.store).support(proposal_id):
            raise CoreError("BILIBILI_PROPOSAL_SOURCE_MISMATCH")
        reply = session.proposal(proposal_id)
        records = RecordService(runtime.store)
        proposal = records.read(proposal_id)
        if proposal["privacy_class"] not in {"PUBLIC", "PROJECT"}:
            raise CoreError("BILIBILI_DERIVATION_PRIVACY_DENIED")
        entity = "bili-reading:" + digest(memory_id)[:24]
        MemoryService(runtime.store).entity(entity, "OBJECT")
        claim = SourcedClaim(entity_id=entity, predicate="publication.interpretation", kind="MODEL_BELIEF",
                            value=reply.proposal.interpretation, valid_from_us=runtime.clock.utc_now_us(), confidence=reply.proposal.confidence)
        source = RecordService(runtime.store).memory.read(memory_id)
        coverage = json.loads(source["text"])["data"].get("coverage", "METADATA_ONLY_NOT_WATCHED")
        parents = tuple(dict.fromkeys((memory_id, *records.support(proposal_id))))
        derived = remember(runtime, "bilibili-model:" + proposal_id, {"world_claim": claim.model_dump(mode="json"),
                           "coverage": coverage, "proposal_record_id": proposal_id},
                           scope=runtime.config.scopes[0], privacy=proposal["privacy_class"],
                           kind="MODEL_DERIVATION", parents=parents)
        world = WorldModel(runtime.store, scopes=runtime.config.scopes, privacy_classes=runtime.config.privacy_classes)
        world.ingest(derived)
        concerns = ConcernService(runtime, resources=("project://bilibili/public",))
        ids = concerns.offer(proposal_id)
        event = concerns.opportunity() if enqueue else None
        queue_id = runtime.submit(event) if event is not None else None
        return {"state": "INTERPRETED_NOT_WATCHED", "source_memory_id": memory_id, "derived_memory_id": derived,
                "concern_ids": ids, "queue_id": queue_id, "entity_id": entity,
                "subject_id": runtime.identity_id, "coverage": coverage, "social_delivery": False, "grants_created": False}

    def history(self, *, limit=16, privacy=None, scope=None, entity_id=None):
        """Read original Memory only. Withdrawal removes entries immediately."""
        out = []
        runtime = self.app.runtime
        records = RecordService(runtime.store)
        allowed = set(self.app.policy.readable_privacy) & set(self.app.policy.readable_privacy if privacy is None else privacy)
        scope = runtime.config.scopes[0] if scope is None else scope
        entity_id = runtime.config.entity_id if entity_id is None else entity_id
        rows = runtime.store.db.execute("SELECT m.* FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id "
            "WHERE m.entity_id=? AND m.lifecycle='ACTIVE' AND e.source_namespace IN ('recorded.project.bilibili','recorded.bilibili.public') "
            "ORDER BY m.created_at_us DESC,m.rowid DESC LIMIT 64", (entity_id,))
        for row in rows:
            if row["scope"] != scope or row["scope"] not in self.app.policy.allowed_scopes or row["privacy_class"] not in allowed:
                continue
            try:
                item = records.memory.read(row["memory_id"])
                body = json.loads(item["text"])
            except (CoreError, ValueError):
                continue
            data = body["data"]
            if not re.fullmatch(r"BV[A-Za-z0-9]{10}", data.get("bvid", "")):
                continue
            candidate = {"source_memory_id": row["memory_id"], "bvid": data["bvid"], "title": plain(data.get("title"), 96),
                        "coverage": plain(data.get("coverage", "DISCOVERY_CANDIDATES"), 64), "watched": False,
                        "subtitle_segments": len(data.get("subtitle_segments") or []),
                        "comment_samples": len(data.get("comment_samples") or []), "danmaku_samples": len(data.get("danmaku_samples") or []),
                        "visual_frames": 0, "source_origin": body["origin"],
                        "missing_sources": [plain(note, 96) for note in data.get("notes", [])[:3]],
                        "interpreted": self._interpreted(row["memory_id"]),
                        "observed_at_us": runtime.store.one("continuity_evidence", row["source_evidence_id"])["observed_time_us"]}
            from .bilibili_frames import BilibiliFrameService
            candidate.update(BilibiliFrameService(self.app).coverage(row['memory_id']))
            if len(canonical(out + [candidate]).encode()) > 10000:
                break
            out.append(candidate)
            if len(out) >= min(max(limit, 1), 16):
                break
        return {"items": out, "network_calls": 0, "second_memory_authority": False}

    def _interpreted(self, memory_id):
        return self.app.runtime.store.db.execute("SELECT 1 FROM memory_dependencies d JOIN memories m ON m.memory_id=d.memory_id "
            "JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE d.parent_kind='MEMORY' AND d.parent_id=? "
            "AND m.lifecycle='ACTIVE' AND m.assessment IN ('CURRENT','UNASSESSED') AND e.source_kind='MODEL_DERIVATION' "
            "AND e.source_namespace='recorded.project.material' AND e.source_reference LIKE 'open-life:bilibili-model:%' LIMIT 1",
            (memory_id,)).fetchone() is not None


class BilibiliReadArgs(DTO):
    cycle_id: str = Field(min_length=1, max_length=128)
    source_memory_id: str = Field(min_length=1, max_length=128)
    query: str | None = Field(default=None, min_length=1, max_length=64)
    bvid: str | None = Field(default=None, pattern=r"^BV[A-Za-z0-9]{10}$")


class BilibiliReadRegistry:
    """Finite public reads; neither description nor interest grants authority."""
    definitions = MappingProxyType({"bilibili.public.discover": BilibiliReadArgs,
                                    "bilibili.public.read": BilibiliReadArgs,
                                    "bilibili.public.watch": BilibiliReadArgs})
    verify_capability = "bilibili.public.verify"
    resource = "project://bilibili/public"

    @staticmethod
    def is_write(capability):
        return False

    @staticmethod
    def request_count(capability):
        if capability not in BilibiliReadRegistry.definitions:
            raise CoreError("BILIBILI_READ_CAPABILITY_DENIED")
        return 1 if capability == "bilibili.public.discover" else 9 if capability == 'bilibili.public.watch' else 5

    @staticmethod
    def payload_privacy(payload):
        return "PUBLIC"

    def validate(self, capability, resource, args):
        if capability not in self.definitions or resource != self.resource:
            raise CoreError("BILIBILI_READ_CAPABILITY_DENIED")
        body = BilibiliReadArgs.model_validate(args).model_dump()
        discovery = capability == "bilibili.public.discover"
        if (discovery and (body["query"] is None or body["bvid"] is not None)) or (
                not discovery and (body["bvid"] is None or body["query"] is not None)):
            raise CoreError("BILIBILI_READ_TARGET_REQUIRED")
        return body


class BilibiliReadPort:
    """Original C→Manager→Kernel public reads, with no platform scheduler.

    bind_event adds a finite target description BEFORE C judges the opportunity.
    A discovery receipt is another source for interpretation/C, never a command
    to open its first candidate. Reading a selected video requires a separate
    source-linked C cycle. All receipts use the original Memory authority.
    """
    def __init__(self, app, transport, *, activation=None):
        self.app, self.store, self.transport = app, app.runtime.store, transport
        self.identity_id = app.runtime.identity_id
        self.activation = activation
        self.sources = BilibiliSourceAdapter(app)
        self.registry = BilibiliReadRegistry()

    def assert_owned(self):
        if (self.transport.origin == "SYNTHETIC_FIXTURE" and type(self.transport.opener) is BilibiliLoopbackOpener):
            # Re-validate mutable host configuration at every Kernel boundary.
            BilibiliLoopbackOpener(self.transport.opener.endpoint)
            return
        if self.activation is not None and self.transport.origin == "REAL_PLATFORM_HTTP":
            from .platform_authority import require_platform_authority
            require_platform_authority(self.app, self.activation, channel="bilibili", exclusive_writer=False)
            return
        raise CoreError("BILIBILI_CANONICAL_ACTIVATION_REQUIRED")

    def _source(self, memory_id, *, interest=False):
        source = RecordService(self.store).memory.read(memory_id)
        if source["scope"] not in self.app.runtime.config.scopes or source["privacy_class"] not in self.app.policy.readable_privacy:
            raise CoreError("BILIBILI_READ_SOURCE_DENIED")
        if source["source_provenance"]["source_namespace"] not in {
                "recorded.project.bilibili", "recorded.bilibili.public"}:
            if not interest or source['privacy_class'] != 'PUBLIC':
                raise CoreError("BILIBILI_SOURCE_BINDING_REQUIRED")
            return source, {'kind': 'SOURCED_INTEREST', 'origin': 'ORIGINAL_PUBLIC_CONCERN', 'data': {}}
        if source["scope"] not in self.app.runtime.config.scopes or source["privacy_class"] not in self.app.policy.readable_privacy:
            raise CoreError("BILIBILI_READ_SOURCE_DENIED")
        reading = json.loads(source["text"])
        if source["privacy_class"] != "PUBLIC" and not (
                source["privacy_class"] == "PROJECT" and reading["origin"] == "SYNTHETIC_FIXTURE"
                and self.transport.origin == "SYNTHETIC_FIXTURE"):
            raise CoreError("BILIBILI_QUERY_PRIVACY_DENIED")
        return source, reading

    def bind_event(self, event, source_memory_id, *, discover=True, visual=False):
        """Describe an opportunity; the caller still submits it to original C."""
        from ..continuity.autonomy.contracts import RealizationTarget
        if not event.world_concern_id:
            raise CoreError("BILIBILI_CONCERN_REQUIRED")
        row = self.store.one("open_concerns", event.world_concern_id)
        records = RecordService(self.store)
        if not row or source_memory_id not in records.support(row["record_id"]) or not records.current_support(row["record_id"]):
            raise CoreError("BILIBILI_CONCERN_SOURCE_MISMATCH")
        _, reading = self._source(source_memory_id, interest=discover)
        if not discover and (reading["kind"] not in {"VIDEO_METADATA", "VIDEO_READING"} or
                            not re.fullmatch(r"BV[A-Za-z0-9]{10}", reading["data"].get("bvid", ""))):
            raise CoreError("BILIBILI_ORIGINAL_SELECTION_REQUIRED")
        capability = "bilibili.public.discover" if discover else 'bilibili.public.watch' if visual else "bilibili.public.read"
        return event.model_copy(update={"realization_target": RealizationTarget(
            capability=capability, resource=self.registry.resource, operation="READ", resource_class="ORDINARY")})

    def args_for_cycle(self, cycle_id, source_memory_id):
        records = RecordService(self.store)
        row = self.store.one("subject_cycles", cycle_id)
        if not row or not records.current_support(row["record_id"]):
            raise CoreError("BILIBILI_CURRENT_C_REQUIRED")
        cycle = self.app.runtime.subject.result(row)
        target = cycle.realization_target
        if (not cycle.evaluation or cycle.evaluation.normative != "ENDORSED" or cycle.intention.kind != "EXPLORE"
                or not target or target.capability not in self.registry.definitions or target.resource != self.registry.resource
                or target.operation != "READ" or target.resource_class != "ORDINARY"):
            raise CoreError("BILIBILI_ORIGINAL_C_DID_NOT_ENDORSE_READ")
        intention = self.store.one("subject_intentions", cycle.intention_id)
        if not intention or intention["state"] != "PENDING" or intention["expires_at_us"] <= self.store.clock.utc_now_us():
            raise CoreError("BILIBILI_CURRENT_C_REQUIRED")
        if source_memory_id not in records.support(row["record_id"]):
            raise CoreError("BILIBILI_C_SOURCE_MISMATCH")
        source, reading = self._source(source_memory_id, interest=target.capability == 'bilibili.public.discover')
        event = records.read(self.store.one("subject_events", row["subject_event_id"])["record_id"])["payload"]["input"]
        concern = self.store.one("open_concerns", event.get("world_concern_id"))
        if (not concern or not records.current_support(concern["record_id"]) or
                source_memory_id not in records.support(concern["record_id"])):
            raise CoreError("BILIBILI_CONCERN_SOURCE_MISMATCH")
        privacy = records.read(concern["record_id"])["privacy_class"]
        if privacy != "PUBLIC" and not (privacy == "PROJECT" and self.transport.origin == "SYNTHETIC_FIXTURE"):
            raise CoreError("BILIBILI_QUERY_PRIVACY_DENIED")
        args = {"cycle_id": cycle_id, "source_memory_id": source_memory_id}
        if target.capability == "bilibili.public.discover":
            args["query"] = records.read(concern["record_id"])["payload"]["topic"].replace("-", " ")[:64]
        else:
            if reading["kind"] not in {"VIDEO_METADATA", "VIDEO_READING"}:
                raise CoreError("BILIBILI_ORIGINAL_SELECTION_REQUIRED")
            args["bvid"] = reading["data"].get("bvid")
        return self.registry.validate(target.capability, target.resource, args)

    def _bound(self, invocation, *, verifying=False):
        if type(invocation) is not Invocation:
            raise CoreError("BILIBILI_KERNEL_INVOCATION_REQUIRED")
        row = self.store.one("actions", invocation.action_id)
        states = {"PENDING_VERIFY", "UNKNOWN", "SUCCEEDED"} if verifying else {"DISPATCHING"}
        if not row or row["state"] not in states or any(row[key] != getattr(invocation, key)
                for key in ("attempt_id", "capability", "resource", "args_hash", "idempotency_key")):
            raise CoreError("BILIBILI_KERNEL_ACTION_UNBOUND")
        if digest(invocation.args) != invocation.args_hash:
            raise CoreError("BILIBILI_KERNEL_ARGS_MISMATCH")
        body = self.registry.validate(invocation.capability, invocation.resource, invocation.args)
        if not verifying and self.args_for_cycle(body["cycle_id"], body["source_memory_id"]) != body:
            raise CoreError("BILIBILI_C_TARGET_MISMATCH")
        self._source(body["source_memory_id"], interest=body['query'] is not None)
        return body

    def execute(self, invocation):
        body = self._bound(invocation)
        reading = (self.transport.search(body["query"]) if body["query"] is not None
                   else self.transport.read_video(body["bvid"], visual=invocation.capability == 'bilibili.public.watch'))
        frames = reading.frames
        reading = PublicReading(reading.reference, reading.kind, reading.observed_at_us,
            {**reading.payload, "kernel_action_id": invocation.action_id, "kernel_args_hash": invocation.args_hash}, reading.origin)
        memory_id = self.sources.ingest(reading)
        frame_ids = ()
        if frames:
            from .bilibili_frames import BilibiliFrameService
            frame_ids = BilibiliFrameService(self.app).capture(memory_id, frames)
        return Receipt(external_id=memory_id, result={"source_memory_id": memory_id, "watched": False,
                       'frame_memory_ids': list(frame_ids), "selection": "REQUIRES_ORIGINAL_C_JUDGMENT"})

    def verify(self, invocation):
        self._bound(invocation, verifying=True)
        rows = self.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id "
            "WHERE m.lifecycle='ACTIVE' AND e.source_namespace IN ('recorded.project.bilibili','recorded.bilibili.public') "
            "ORDER BY m.created_at_us DESC,m.rowid DESC LIMIT 64")
        for row in rows:
            try:
                _, source = self._source(row[0])
            except CoreError:
                continue
            data = source["data"]
            if data.get("kernel_action_id") == invocation.action_id and data.get("kernel_args_hash") == invocation.args_hash:
                from .bilibili_frames import BilibiliFrameService
                coverage = BilibiliFrameService(self.app).coverage(row[0])
                return Verification(verdict="MATCH", evidence={"original_memory_readback": True,
                    "network_repeated": False, "result": {"source_memory_id": row[0], "watched": False,
                    'frame_memory_ids': [f['source_memory_id'] for f in coverage['frame_samples']]}})
        return Verification(verdict="INCONCLUSIVE", evidence={"no_blind_retry": True, "network_calls": 0})


from ..continuity.autonomy.realization import GovernedRealization


class BilibiliReadRealization(GovernedRealization):
    """Narrow host binding; reuse original Manager/Kernel handoff unchanged."""
    def __init__(self, app, transport, *, activation=None):
        from ..actions import ActionKernel
        from ..continuity.autonomy.governance import ManagerConstraintGate
        if app.runtime.store.schema_target < 13 or type(transport) is not BilibiliPublicTransport:
            raise CoreError("BILIBILI_ORIGINAL_RUNTIME_REQUIRED")
        self.store, self.gate = app.runtime.store, ManagerConstraintGate(app.runtime.store)
        self.port = BilibiliReadPort(app, transport, activation=activation)
        self.kernel = ActionKernel(self.store, self.port, app.runtime.authority, registry=self.port.registry)
