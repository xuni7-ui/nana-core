"""Bilibili public source adapter into original Memory/World/Concern/C.

The legacy C.5 reader's bounded metadata/subtitle semantics are preserved. Its
ambient cookie path and separate LLM are deliberately not imported into Core.
No platform brain, account discovery, social sender or second history database.
"""

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from ..contracts import CoreError
from ..storage import canonical, digest
from ..continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from ..continuity.memory import MemoryService
from ..continuity.records import RecordService


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def plain(text, bound):
    return html.unescape(re.sub(r"<[^>]*>", "", str(text or "")))[:bound]


@dataclass(frozen=True, repr=False)
class PublicReading:
    reference: str
    kind: str
    observed_at_us: int
    payload: dict = field(repr=False)
    origin: str = "REAL_PLATFORM_HTTP"


class BilibiliPublicTransport:
    """Fixed public endpoints, no cookies/auth/redirects or blind retries.

    A trusted caller supplies read authorization; production autonomous callers
    must additionally dispatch through the original Kernel/Grant boundary.
    """
    def __init__(self, *, authorized=False, request_limit=4):
        self.authorized = authorized
        self.request_limit = min(max(request_limit, 0), 16)
        self.calls = 0
        self.last_http_status = None
        self.opener = urllib.request.build_opener(NoRedirect())

    def _get(self, path, query):
        if not self.authorized:
            raise CoreError("BILIBILI_READ_NOT_AUTHORIZED")
        if self.calls >= self.request_limit:
            raise CoreError("BILIBILI_READ_BUDGET")
        if path not in {"/x/web-interface/search/type", "/x/web-interface/view", "/x/web-interface/archive/related"}:
            raise CoreError("BILIBILI_ENDPOINT_DENIED")
        self.calls += 1
        url = "https://api.bilibili.com" + path + "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "NanaCore/4 source-aware public reader"})
        try:
            with self.opener.open(request, timeout=5) as response:
                self.last_http_status = response.status
                raw = response.read(262145)
        except urllib.error.HTTPError as exc:
            self.last_http_status = exc.code
            raise CoreError("BILIBILI_HTTP_UNAVAILABLE") from None
        except OSError:
            raise CoreError("BILIBILI_READ_UNKNOWN_NO_RETRY") from None
        if len(raw) > 262144:
            raise CoreError("BILIBILI_RESPONSE_BOUND")
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            raise CoreError("BILIBILI_RESPONSE_INVALID") from None
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
                "coverage": "METADATA_ONLY_NOT_WATCHED", "transcript": None, "visual_frames": 0}

    def search(self, query):
        if type(query) is not str or not 1 <= len(query) <= 64 or any(ord(c) < 32 for c in query):
            raise CoreError("BILIBILI_QUERY_BOUND")
        data = self._get("/x/web-interface/search/type", {"search_type": "video", "keyword": query, "page": 1})
        if type(data) is not dict or type(data.get("result")) is not list:
            raise CoreError("BILIBILI_RESPONSE_INVALID")
        rows = [self._video(row) for row in data["result"][:8] if type(row) is dict]
        return PublicReading("search:" + digest(query)[:32], "DISCOVERY", time.time_ns() // 1000,
                             {"query": query, "candidates": rows, "selection": "REQUIRES_ORIGINAL_C_JUDGMENT"})

    def video(self, bvid):
        if not re.fullmatch(r"BV[A-Za-z0-9]{10}", bvid):
            raise CoreError("BILIBILI_VIDEO_ID_INVALID")
        data = self._get("/x/web-interface/view", {"bvid": bvid})
        if type(data) is not dict or data.get("bvid") != bvid:
            raise CoreError("BILIBILI_VIDEO_CORRELATION_MISMATCH")
        return PublicReading(bvid, "VIDEO_METADATA", time.time_ns() // 1000, self._video(data))


class BilibiliSourceAdapter:
    """Trusted platform receipts only; untrusted publication is still data."""
    def __init__(self, app):
        self.app = app

    def ingest(self, reading):
        if type(reading) is not PublicReading or reading.kind not in {"DISCOVERY", "VIDEO_METADATA"}:
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
        if len(body.encode()) > 16384:
            raise CoreError("BILIBILI_RECEIPT_BOUND")
        reference = digest([reading.reference, digest(body)])
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
                                         source_evidence_id=evidence, text=body))

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
                                   timeout_ms=cfg.provider_timeout_ms, cost_ceiling_micro=cfg.provider_cost_ceiling_micro))
        result = session.execute(request)
        if result["state"] != "PROPOSED":
            return {"state": result["state"], "request_id": request, "no_retry": True}
        return self.apply_proposal(memory_id, session, result["record_id"])

    def apply_proposal(self, memory_id, session, proposal_id):
        from ..continuity.world_loop.world import WorldModel, SourcedClaim
        from ..continuity.world_loop.attention import ConcernService
        from ..continuity.open_life.sources import remember
        runtime = self.app.runtime
        if memory_id not in RecordService(runtime.store).support(proposal_id):
            raise CoreError("BILIBILI_PROPOSAL_SOURCE_MISMATCH")
        reply = session.proposal(proposal_id)
        entity = "bili-reading:" + digest(memory_id)[:24]
        MemoryService(runtime.store).entity(entity, "OBJECT")
        claim = SourcedClaim(entity_id=entity, predicate="publication.interpretation", kind="MODEL_BELIEF",
                            value=reply.proposal.interpretation, valid_from_us=runtime.clock.utc_now_us(), confidence=reply.proposal.confidence)
        derived = remember(runtime, "bilibili-model:" + proposal_id, {"world_claim": claim.model_dump(mode="json"),
                           "coverage": "METADATA_ONLY_NOT_WATCHED", "proposal_record_id": proposal_id},
                           scope=runtime.config.scopes[0], privacy=RecordService(runtime.store).memory.read(memory_id)["privacy_class"],
                           kind="MODEL_DERIVATION", parents=(memory_id,))
        world = WorldModel(runtime.store, scopes=runtime.config.scopes, privacy_classes=runtime.config.privacy_classes)
        world.ingest(derived)
        concerns = ConcernService(runtime, resources=("project://bilibili/public",))
        ids = concerns.offer(proposal_id)
        event = concerns.opportunity()
        queue_id = runtime.submit(event) if event is not None else None
        return {"state": "INTERPRETED_NOT_WATCHED", "source_memory_id": memory_id, "derived_memory_id": derived,
                "concern_ids": ids, "queue_id": queue_id, "entity_id": entity,
                "subject_id": runtime.identity_id, "social_delivery": False, "grants_created": False}
