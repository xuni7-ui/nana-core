"""A bounded Bilibili activity source on the ONE original Runtime safe point.

D offers existing sourced interests. Original C endorses (or declines) each
search and selected video separately. Original Manager/Grant/Kernel dispatch;
H1/World/Concern carry learning back. Jobs and receipts use the original Store.
No thread, periodic model burner, first-result selection, separate planner or
independent account identity is introduced here.
"""

import json

from pydantic import Field

from ..contracts import CoreError, DTO
from ..storage import digest, uid
from ..continuity.records import RecordService
from ..continuity.world_loop.attention import ConcernService
from ..continuity.world_loop.cognition import CognitionBudget
from ..presence.contracts import DAY, SECOND
from .bilibili import BilibiliPublicTransport, BilibiliReadRealization, PublicReading
from .platform_authority import PlatformActivation
from .live_api.contracts import ApiError


class BilibiliLifeConfig(DTO):
    enabled: bool = False
    read_authorized: bool = False
    activation: PlatformActivation | None = None
    max_reads_per_day: int = Field(default=2, ge=0, le=16)
    review_interval_seconds: int = Field(default=300, ge=30, le=86400)
    visual_samples: bool = False
    interpret_materials: bool = False


class BilibiliLife:
    def __init__(self, app, previous, config, *, transport=None):
        self.app, self.runtime, self.previous, self.config = app, app.runtime, previous, config
        self.store = app.runtime.store
        self.records = RecordService(self.store)
        self.transport = transport or BilibiliPublicTransport(authorized=config.read_authorized, request_limit=16)
        self.read = BilibiliReadRealization(app, self.transport, activation=config.activation)
        self.concerns = ConcernService(app.runtime, resources=(self.read.port.registry.resource,))
        self.next_at = 0
        self.last_state = "NO_PUBLIC_INTEREST_YET"

    def _finish(self, row, body, state, *, phase=None, **values):
        payload = {**body, **values, "phase": phase or body["phase"]}
        with self.store.transaction("life.bilibili_progress", {"work_id": row["job_id"], "state": state}) as tx:
            rid = self.records.create(
                tx,
                kind="RUNTIME_WORK",
                scope=self.runtime.config.scopes[0],
                payload=payload,
                records=(row["record_id"],),
                target_id=row["occurrence_key"],
            )
            tx.update(
                "jobs",
                row["job_id"],
                state=state,
                record_id=rid,
                revision=row["revision"] + 1,
                updated_at_us=self.store.clock.utc_now_us(),
            )
        self.last_state = values.get("result", phase or state)
        return {
            "bilibili_work_id": row["job_id"],
            "state": state,
            "phase": payload["phase"],
            "result": self.last_state,
            "social_delivery": False,
        }

    def _complete_intention(self, cycle):
        row = self.store.one("subject_intentions", cycle.intention_id)
        if row and row["state"] == "PENDING":
            self.runtime.subject.transition_intention(
                row["intention_id"], expected_revision=row["revision"], state="COMPLETED"
            )

    def maintenance_slice(self):
        if self.runtime.work.paused:
            return None
        row = self.store.db.execute(
            "SELECT * FROM jobs WHERE work_kind='BILIBILI_LIFE' AND state='WAITING' ORDER BY rowid LIMIT 1"
        ).fetchone()
        if row:
            if not self.records.current_support(row["record_id"]):
                with self.store.transaction("life.bilibili_source_retired", {"work_id": row["job_id"]}) as tx:
                    tx.update(
                        "jobs",
                        row["job_id"],
                        state="CANCELLED",
                        revision=row["revision"] + 1,
                        updated_at_us=self.store.clock.utc_now_us(),
                    )
                return {"bilibili_work_id": row["job_id"], "state": "CANCELLED", "result": "SOURCE_RETIRED"}
            body = self.records.read(row["record_id"])["payload"]
            try:
                if body["phase"] == "JUDGMENT":
                    return self._judged(row, body)
                if body["phase"] == "MATERIALS":
                    return self._interpret(row, body)
            except CoreError as exc:
                if exc.code in {"RUNTIME_LEASE_LOST", "PRIVACY_ANCHOR_INVALID", "PRIVACY_ANCHOR_UNAVAILABLE"}:
                    raise
                unknown = self.store.db.execute(
                    "SELECT 1 FROM actions WHERE effect_slot=? AND state IN ('DISPATCHING','UNKNOWN','PENDING_VERIFY')",
                    ("subject:" + body.get("intention_id", ""),),
                ).fetchone()
                unknown = (
                    unknown
                    or self.store.db.execute(
                        "SELECT 1 FROM cognitive_requests WHERE state IN ('CALLING','UNKNOWN') LIMIT 1"
                    ).fetchone()
                )
                return self._finish(row, body, "UNKNOWN" if unknown else "BLOCKED", result=exc.code)
        callback = getattr(self.previous, "maintenance_slice", None)
        return callback() if callback else None

    def _judged(self, row, body):
        cycle_row = self.store.db.execute(
            "SELECT c.* FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id "
            "WHERE e.source_key=?",
            (body["event_key"],),
        ).fetchone()
        if not cycle_row:
            from ..presence.contracts import RuntimeEvent

            # Crash between job commit and queue admission: submit the identical
            # durable envelope; original queue/cycle source key handles dedupe.
            self.runtime.submit(RuntimeEvent.model_validate(body["runtime_event"]))
            return None
        cycle = self.runtime.subject.result(dict(cycle_row))
        if not cycle.evaluation or cycle.evaluation.normative != "ENDORSED" or cycle.intention.kind != "EXPLORE":
            self._complete_intention(cycle)
            return self._finish(row, body, "DONE", result="C_CHOSE_" + cycle.intention.behavior)
        intention = self.store.one("subject_intentions", cycle.intention_id)
        existing = self.store.db.execute(
            "SELECT action_id FROM actions WHERE effect_slot=?", ("subject:" + cycle.intention_id,)
        ).fetchone()
        if existing:
            action_id = existing[0]
        else:
            args = self.read.port.args_for_cycle(cycle.cycle_id, body["source_memory_id"])
            _, action_id = self.read.propose(
                cycle.intention_id,
                expected_revision=intention["revision"],
                args=args,
                input_memory_ids=(body["source_memory_id"],),
            )
        if action_id is None:
            return self._finish(row, body, "BLOCKED", result="MANAGER_DENIED")
        # Transport's per-attempt ceiling resets only for a new, never-dispatched
        # Kernel action. Original cumulative budget reservations never reset.
        action = self.store.one("actions", action_id)
        if action["state"] in {"PROPOSED", "BLOCKED", "READY"}:
            self.transport.calls = 0
        state = self.read.dispatch(cycle.intention_id, action_id, expected_revision=intention["revision"])
        if state != "SUCCEEDED":
            return self._finish(
                row,
                body,
                "UNKNOWN" if state in {"UNKNOWN", "PENDING_VERIFY", "DISPATCHING"} else "BLOCKED",
                result=state,
                action_id=action_id,
                intention_id=cycle.intention_id,
            )
        result = json.loads(self.read.kernel.payload(self.store.one("actions", action_id), "result_json"))
        self._complete_intention(cycle)
        return self._finish(
            row,
            body,
            "WAITING",
            phase="MATERIALS",
            action_id=action_id,
            source_result=result["source_memory_id"],
            frame_memory_ids=result.get("frame_memory_ids", []),
        )

    def _interpret(self, row, body):
        source = self.records.memory.read(body["source_result"])
        raw = json.loads(source["text"])
        if not self.config.interpret_materials:
            return self._finish(row, body, "DONE", result="MATERIALS_RETAINED_SEMANTICS_NOT_AUTHORIZED")
        session = self.app._session(source["privacy_class"])
        mids = [body["source_result"]]
        if raw["kind"] == "DISCOVERY":
            for candidate in raw["data"].get("candidates", [])[:8]:
                mid = self.read.port.sources.ingest(
                    PublicReading(
                        candidate["bvid"], "VIDEO_METADATA", source["observed_time_us"], candidate, raw["origin"]
                    ),
                    parents=(body["source_result"],),
                )
                mids.append(mid)
        if body.get("frame_memory_ids"):
            from .bilibili_frames import BilibiliFrameService

            visual = BilibiliFrameService(self.app).interpret(body["frame_memory_ids"][0])
            if visual["state"] != "SAMPLED_FRAME_INTERPRETED":
                return self._finish(
                    row, body, "UNKNOWN" if visual["state"] == "UNKNOWN" else "BLOCKED", result=visual["state"]
                )
            mids.extend(visual["semantic_memory_ids"][:8])
        cfg = self.app.config
        request = session.prepare(
            "bilibili-life:" + row["job_id"],
            "INTERPRET",
            tuple(mids),
            pinned_only=True,
            budget=CognitionBudget(
                input_tokens=cfg.provider_context_tokens,
                output_tokens=cfg.provider_output_tokens,
                timeout_ms=cfg.provider_timeout_ms,
                cost_ceiling_micro=cfg.provider_cost_ceiling_micro,
            ),
        )
        outcome = session.execute(request)
        if outcome["state"] != "PROPOSED":
            return self._finish(
                row, body, "UNKNOWN" if outcome["state"] == "UNKNOWN" else "BLOCKED", result=outcome["state"]
            )
        # Selecting a video must be an explicit model-proposed cited interest,
        # and a separate original C judgment. No first candidate is preferred.
        reply = session.proposal(outcome["record_id"])
        if raw["kind"] == "DISCOVERY":
            choices = set(mids[1:])
            if any(len(set(i.source_memory_ids) & choices) != 1 for i in reply.proposal.interests):
                return self._finish(row, body, "DONE", result="NO_UNAMBIGUOUS_CITED_VIDEO_SELECTION")
        self.read.port.sources.apply_proposal(body["source_result"], session, outcome["record_id"], enqueue=False)
        return self._finish(
            row, body, "DONE", result="SOURCED_INTERPRETATION_REQUIRES_NEXT_C", proposal_record_id=outcome["record_id"]
        )

    def opportunity(self):
        now = self.runtime.clock.utc_now_us()
        if not self.config.enabled or not self.config.read_authorized or self.runtime.work.paused:
            return self.previous.opportunity() if self.previous else None
        if now < self.next_at:
            return self.previous.opportunity() if self.previous else None
        self.next_at = now + self.config.review_interval_seconds * SECOND
        try:
            self.read.port.assert_owned()
        except (CoreError,ApiError) as exc:
            self.last_state = exc.code
            return self.previous.opportunity() if self.previous else None
        if self.store.db.execute(
            "SELECT 1 FROM jobs WHERE work_kind='BILIBILI_LIFE' AND state IN ('WAITING','UNKNOWN') LIMIT 1"
        ).fetchone():
            return self.previous.opportunity() if self.previous else None
        day = now // DAY * DAY
        count = self.store.db.execute(
            "SELECT count(*) FROM jobs WHERE work_kind='BILIBILI_LIFE' AND due_at_us>=?", (day,)
        ).fetchone()[0]
        if count >= self.config.max_reads_per_day:
            self.last_state = "DAILY_ACTIVITY_CEILING"
            return self.previous.opportunity() if self.previous else None
        for row in self.store.db.execute(
            "SELECT * FROM open_concerns WHERE state='INTEREST' ORDER BY updated_at_us DESC LIMIT 16"
        ):
            try:
                head = self.records.read(row["record_id"])
                if head["privacy_class"] != "PUBLIC" and not (
                    self.transport.origin == "SYNTHETIC_FIXTURE" and head["privacy_class"] == "PROJECT"
                ):
                    continue
                body = head["payload"]
                if (
                    body.get("objective")
                    or body.get("skill_task")
                    or body["motivation_source"] not in {"CURIOSITY", "UNRESOLVED_QUESTION"}
                    or not self.records.current_support(row["record_id"])
                ):
                    continue
                key = "bilibili-life:" + digest(row["record_id"])
                if self.store.db.execute("SELECT 1 FROM jobs WHERE occurrence_key=?", (key,)).fetchone():
                    continue
                sources = [self.records.memory.read(mid) for mid in body["source_memory_ids"]]
                video = [
                    m
                    for m in sources
                    if m["source_provenance"]["source_namespace"]
                    in {"recorded.bilibili.public", "recorded.project.bilibili"}
                    and json.loads(m["text"])["kind"] == "VIDEO_METADATA"
                ]
                if len(video) > 1:
                    continue
                source = video[0] if video else next((m for m in sources if m["privacy_class"] == "PUBLIC"), None)
                if source is None:
                    continue
                event = self.concerns.opportunity(concern_ids=(row["concern_id"],))
                if event is None:
                    continue
                bound = self.read.port.bind_event(
                    event.input,
                    source["memory_id"],
                    discover=not video,
                    visual=bool(video and self.config.visual_samples),
                )
                job_id = uid()
                payload = {
                    "kind": "BILIBILI_LIFE",
                    "phase": "JUDGMENT",
                    "event_key": bound.source_key,
                    "source_memory_id": source["memory_id"],
                    "concern_id": row["concern_id"],
                    "realization_target": bound.realization_target.model_dump(mode="json"),
                }
                runtime_event = event.model_copy(update={"input": bound})
                payload["runtime_event"] = runtime_event.model_dump(mode="json")
                with self.store.transaction("life.bilibili_opportunity", {"work_id": job_id}) as tx:
                    rid = self.records.create(
                        tx,
                        kind="RUNTIME_WORK",
                        scope=head["scope"],
                        payload=payload,
                        records=(row["record_id"],),
                        memories=(source["memory_id"],),
                        target_id=key,
                    )
                    tx.put(
                        "jobs",
                        {
                            "job_id": job_id,
                            "occurrence_key": key,
                            "due_at_us": now,
                            "state": "WAITING",
                            "body_json": "{}",
                            "work_kind": "BILIBILI_LIFE",
                            "record_id": rid,
                            "revision": 1,
                            "cursor": 0,
                            "owner_epoch": None,
                            "updated_at_us": now,
                        },
                    )
                queue_id = self.runtime.submit(runtime_event)
                return {"bilibili_work_id": job_id, "queue_id": queue_id, "not_dispatched": True}
            except CoreError as exc:
                if exc.code in {"RUNTIME_LEASE_LOST", "PRIVACY_ANCHOR_INVALID", "PRIVACY_ANCHOR_UNAVAILABLE"}:
                    raise
                self.last_state = exc.code
        return self.previous.opportunity() if self.previous else None

    def view(self):
        return {
            "enabled": self.config.enabled,
            "state": self.last_state,
            "source": "ORIGINAL_STORE_C_AND_KERNEL",
            "visual_samples": self.config.visual_samples,
            "social_delivery": False,
            "new_authority": False,
        }
