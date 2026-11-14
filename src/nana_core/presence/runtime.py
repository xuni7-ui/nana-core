"""One standalone event-driven runtime schedules the existing C SubjectLoop."""

import json
from pathlib import Path
from ..actions import OperatorAuthority
from ..clock import Clock
from ..contracts import CoreError
from ..storage import canonical, digest
from ..continuity import ContinuityStore, IdentityService
from ..continuity.context import ContextPolicy
from ..continuity.subject import SubjectLoop, SubjectInput
from ..continuity.subject.projections import project_self, Environment
from .contracts import RuntimeConfig, RuntimeEvent, RuntimeHealth, ScheduleSpec, Cause
from .authority import RuntimeClock, RuntimeLease
from .queue import EventQueue
from .scheduler import Scheduler
from .cognition import CognitionCoordinator
from .cadence import Cadence, CognitionPreempted


class NanaRuntime:
    def __init__(self, path, config: RuntimeConfig, *, clock=None):
        self.config, self.stopped, self.stop_requested = config, False, False
        self.cadence = Cadence(
            config.queue_capacity, config.living.max_idle_seconds if config.living else config.poll_seconds
        )
        self._processing = None
        self.perception = None
        self.store = ContinuityStore(path, clock or Clock(), schema_target=config.schema_target)
        try:
            old = self.store.one("runtime_lease", self.store.identity["identity_id"])
            history_floor = self.store.db.execute("SELECT coalesce(max(recorded_at_us),0) FROM events").fetchone()[0]
            self.clock = RuntimeClock(
                clock or self.store.clock, max(history_floor, old["clock_high_water_us"] if old else 0)
            )
            self.store.clock = self.clock
            self.lease = RuntimeLease(self.store, config)
            self.lease.acquire()
            self.identity_id = self.store.identity["identity_id"]
            self.authority = OperatorAuthority()
            IdentityService(self.store, self.authority)
            if not self.store.one("entities", config.entity_id):
                raise CoreError("RUNTIME_ENTITY_BINDING_REQUIRED")
            self.subject = SubjectLoop(self.store, scopes=config.scopes, privacy_classes=config.privacy_classes)
            self.queue = EventQueue(self.store, config, self.lease)
            self.scheduler = Scheduler(self.store, config, self.queue)
            self.cognition = CognitionCoordinator(self.store, config, self.lease)
            self.cognition.progress = self._model_progress
            from .living import LivingWork

            self.work = LivingWork(self) if config.living else None
            self.queue.recover()
            persisted = self.store.one("core_meta", "runtime.health")
            self.oper = (
                json.loads(persisted["value_json"])
                if persisted
                else {
                    "last_event": None,
                    "last_wake_us": None,
                    "last_cognition_us": None,
                    "last_successful_checkpoint_us": None,
                    "last_interaction_us": None,
                    "last_activity_us": self.clock.utc_now_us(),
                }
            )
            if self.oper["last_interaction_us"] is None:
                self.oper["last_interaction_us"] = self.store.db.execute(
                    "SELECT max(observed_at_us) FROM subject_events WHERE origin='USER'"
                ).fetchone()[0]
            self.next_scan_us = 0
            self._install_review()
            self._save_oper()
        except BaseException:
            if hasattr(self, "lease") and self.lease.epoch is not None:
                self.lease.release()
            self.store.close()
            raise

    def _save_oper(self):
        self.lease.assert_current()
        value = canonical(self.oper)
        old = self.store.one("core_meta", "runtime.health")
        if not old or old["value_json"] != value:
            self.store.db.execute("BEGIN IMMEDIATE")
            try:
                self.lease.assert_current()
                self.store._put("core_meta", {"key": "runtime.health", "value_json": value})
                self.lease.assert_current()
                self.store.db.execute("COMMIT")
            except BaseException:
                self.store.db.execute("ROLLBACK")
                raise

    def _install_review(self):
        now = self.clock.utc_now_us()
        for scope in self.config.scopes:
            key = "runtime-review-" + digest(scope)[:24]
            if self.store.db.execute("SELECT 1 FROM runtime_schedules WHERE dedupe_key=?", (key,)).fetchone():
                continue
            inp = SubjectInput(
                source_key="synthetic.runtime.review-template",
                kind="WAKE",
                origin="SELF_WAKE",
                entity_id=self.config.entity_id,
                scope=scope,
                observed_at_us=now,
            )
            event = RuntimeEvent(
                event_type="TIME_EVENT",
                trigger="TIME_TRIGGER",
                input=inp,
                causes=(Cause(kind="CANONICAL_SELF", reference_id=self.store.identity["identity_id"]),),
                due_at_us=now + self.config.review_interval_us,
                priority=0,
            )
            self.scheduler.add(
                ScheduleSpec(
                    dedupe_key=key,
                    kind="PERIODIC",
                    due_at_us=event.due_at_us,
                    interval_us=self.config.review_interval_us,
                    event=event,
                )
            )

    def submit(self, event: RuntimeEvent):
        self.cadence.assert_owner()
        result = self.queue.enqueue(event)
        self.next_scan_us = 0
        self.cadence.notify()
        return result

    def post(self, event: RuntimeEvent):
        """Thread-safe producer API; receipt is durable only after wait() succeeds."""
        return self.cadence.post(event)

    def post_surface(self, envelope, event):
        from ..continuity.surfaces import surface_input

        event = surface_input(envelope, event, identity_id=self.identity_id)
        wrapped = RuntimeEvent(
            event_type="USER_EVENT" if event.origin == "USER" else "WORLD_EVENT",
            trigger="INCOMING_EVENT",
            input=event,
            causes=(Cause(kind="CANONICAL_SELF", reference_id=self.identity_id),),
            due_at_us=event.observed_at_us,
            priority=3 if event.origin == "USER" else 1,
        )
        return self.post(wrapped)

    def application(self, *, providers, bootstrap_authority=None, provider_settings=None, perception_settings=None):
        from ..continuity.application import SubjectApplication
        from .projections import runtime_projection

        return SubjectApplication(
            self.store,
            self.subject,
            self.authority,
            providers=providers,
            bootstrap_authority=bootstrap_authority,
            health=self.health,
            runtime_views=lambda kind, policy, **kw: runtime_projection(self, kind, policy, **kw),
            ingress=self.post_surface,
            provider_settings=provider_settings,
            perception_settings=perception_settings,
        )

    def request_stop(self):
        self.stop_requested = True
        self.cadence.notify()

    def _model_progress(self):
        self.lease.heartbeat()
        self.cadence.drain(self.submit)
        row = self._processing
        if self.stop_requested or (
            self.config.living and row and row["event_type"] != "USER_EVENT" and self.queue.has_reactive()
        ):
            raise CognitionPreempted()

    def next_wait_seconds(self):
        now = self.clock.utc_now_us()
        deadlines = [now + self.cadence.max_wait * 1_000_000, now + self.config.heartbeat_us]
        for table in ("runtime_queue", "runtime_schedules"):
            states = "('READY','DEFERRED')" if table == "runtime_queue" else "('ACTIVE')"
            due = self.store.db.execute(f"SELECT min(due_at_us) FROM {table} WHERE state IN {states}").fetchone()[0]
            if due is not None:
                deadlines.append(max(now + 10000, due))
        if self.work:
            due = self.store.db.execute(
                "SELECT min(due_at_us) FROM jobs WHERE state IN ('WAITING','RUNNING','UNKNOWN') AND work_kind IN ('SCAN','GOAL')"
            ).fetchone()[0]
            if due is not None:
                deadlines.append(max(now + 10000, due))
        idle = min(self.cadence.max_wait, self.config.poll_seconds * (2 ** min(self.cadence.idle_rounds, 8)))
        return max(0.001, min(idle, (min(deadlines) - now) / 1_000_000))

    def refresh_attention(self):
        self.lease.assert_current()
        self.next_scan_us = 0

    def _watch_sources(self):
        """D installs source-bound checks. C decides relevance and intentions."""
        now = self.clock.utc_now_us()
        if now < self.next_scan_us:
            return
        self.next_scan_us = now + min(self.config.review_interval_us, self.config.idle_recall_us)
        # The generic C opportunity collector is added by the C integration
        # milestone. This compatibility check keeps clock/deadline infrastructure
        # useful independently; it is not a hidden second judgment engine.
        collector = getattr(self.subject, "background_opportunities", None)
        if collector:
            opportunities = collector(
                entity_id=self.config.entity_id,
                now_us=now,
                quiet_since_us=self.oper["last_activity_us"],
                quiet_window_us=self.config.idle_recall_us,
            )
            for opportunity in opportunities:
                inp = SubjectInput(
                    source_key="synthetic.runtime.attention-template",
                    private_thought_ref=getattr(opportunity,"private_thought_ref",None),
                    communication_method_record_id=getattr(opportunity,"communication_method_record_id",None),
                    privacy_class=max(self.config.privacy_classes,key=lambda p: {'PUBLIC':0,'PROJECT':1,'PERSONAL':2}[p],default='PUBLIC'),
                    kind="WAKE",
                    origin="SELF_WAKE",
                    entity_id=opportunity.entity_id,
                    scope=opportunity.scope,
                    observed_at_us=now,
                    source_memory_ids=opportunity.memory_ids[:32],
                    task_class=opportunity.task_class,
                    reflection_experience_id=opportunity.reflection_experience_id,
                    growth_assessment_id=opportunity.growth_assessment_id,
                    commitment_check_id=opportunity.commitment_check_id,
                )
                if inp.private_thought_ref is not None or inp.communication_method_record_id is not None or inp.task_class=="private.feedback.review":
                    if self.queue.has_reactive() or now<max(self.oper['last_activity_us'],(self.oper['last_interaction_us'] or 0))+self.config.idle_recall_us:continue
                    if self.cognition.preview_private(inp,self.subject)[0]!='FULL_COGNITION':continue
                event = RuntimeEvent(
                    event_type=opportunity.event_type,
                    trigger=opportunity.wake_trigger,
                    input=inp,
                    causes=(
                        Cause(
                            kind=opportunity.source_kind,
                            reference_id=opportunity.source_id,
                            revision=opportunity.source_revision,
                        ),
                    ),
                    due_at_us=opportunity.due_at_us,
                    priority=opportunity.priority,
                )
                spec = ScheduleSpec(
                    dedupe_key=opportunity.key,
                    kind="CALENDAR" if opportunity.calendar else "CONDITION",
                    due_at_us=opportunity.due_at_us,
                    event=event,
                    calendar=opportunity.calendar,
                )
                if self.store.db.execute(
                    "SELECT 1 FROM runtime_schedules WHERE dedupe_key=?", (opportunity.key,)
                ).fetchone():
                    continue
                try:
                    self.scheduler.add(spec)
                except CoreError as exc:
                    if str(exc) == "RUNTIME_SCHEDULE_BACKPRESSURE":
                        break
                    raise

    def _private_resources_ready(self, row):
        """Offer the existing method later; resource absence is not abandonment.

        No model is called here. Original C still owns the eventual choice;
        source invalidity and prior attempts must reach normal retirement or
        UNKNOWN handling instead of being hidden behind a resource pause.
        """
        try:
            provider_background=self.cognition.provider_factory is not None and row['event_type']!='USER_EVENT'
            if not provider_background and json.loads(row['metadata_json']).get('private_thought_ref') is None:
                return True
            event = self.queue.input(row)
            if not provider_background and event.private_thought_ref is None:
                return True
            if self.store.db.execute(
                'SELECT 1 FROM runtime_cognition_calls WHERE queue_id=?', (row['queue_id'],)
            ).fetchone():
                return True
            mode, reason = self.cognition.choose(row, event, self.subject)
            return mode == 'FULL_COGNITION' or reason in {
                'C_POLICY_SUFFICIENT', 'MODEL_ATTEMPT_ALREADY_RESERVED', 'NONRETENTION_NO_MODEL',
            }
        except CoreError:
            return True

    def step(self):
        self.cadence.assert_owner()
        self.cadence.drain(self.submit)
        self.lease.heartbeat()
        if not self.queue.has_reactive() and not (self.work and self.work.paused):
            recovered = self._recover_followup()
            if recovered:
                return recovered
        if self.perception:
            self.perception.poll()
        if not (self.work and self.work.paused):
            self._watch_sources()
            self.scheduler.due()
            if not self.queue.has_reactive() and self.scheduler.routine_pending():
                self.subject.maintain()
                checkpoint=self.store.db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                if checkpoint[0]==0:self.oper['last_successful_checkpoint_us']=self.clock.utc_now_us()
                self.scheduler.acknowledge_routine()
        work_activity = self.work.opportunity() if self.work and not self.queue.has_reactive() else None
        row = self.queue.claim(
            user_only=bool(self.work and self.work.paused), ready=self._private_resources_ready,
        )
        if row is None:
            if work_activity and ("recovered" in work_activity or "blocked" in work_activity):
                self._save_oper()
                return {
                    "queue_id": None,
                    "mode": "NO_COGNITION",
                    "reason": "RECOVERED_WORK_SAFE_POINT",
                    "cycle": None,
                    "work": work_activity,
                }
            if self.work:
                activity = self.work.maintenance_slice()
                if activity:
                    self._save_oper()
                    return {
                        "queue_id": None,
                        "mode": "NO_COGNITION",
                        "reason": "BOUNDED_MAINTENANCE_SLICE",
                        "cycle": None,
                        "maintenance": activity,
                    }
            self.cadence.idle_rounds = min(8, self.cadence.idle_rounds + 1)
            self._save_oper()
            return None
        self.cadence.idle_rounds = 0
        self._processing = row
        self.oper["last_event"] = row["queue_id"]
        self.oper["last_wake_us"] = self.clock.utc_now_us()
        try:
            if self.perception:
                observed = self.perception.handle_queue(row)
                if observed is not None:
                    self.queue.finish(row, "DONE", "PERCEPTION_OPPORTUNITY_HANDLED")
                    self._save_oper()
                    return {
                        "queue_id": row["queue_id"],
                        "mode": "NO_COGNITION",
                        "reason": "PERCEPTION_OPPORTUNITY_HANDLED",
                        "cycle": None,
                        "perception": observed,
                    }
            event = self.queue.input(row)
            self.queue.cause_memories(
                tuple(Cause.model_validate_json(canonical(x)) for x in json.loads(row["cause_json"])), event.scope
            )
            if event.origin == "USER":
                self.oper["last_interaction_us"] = event.observed_at_us
            if event.private_thought_ref is not None:
                from ..continuity.autonomy.private_intent import continuation_target

                continuation_target(
                    self.store, event.private_thought_ref,
                    scope=event.scope, privacy_classes=self.config.privacy_classes,
                )
                quiet_until = max(
                    self.oper['last_activity_us'], self.oper['last_interaction_us'] or 0
                ) + self.config.idle_recall_us
                if self.clock.utc_now_us() < quiet_until:
                    expired = row['expires_at_us'] is not None and quiet_until >= row['expires_at_us']
                    reason = 'PRIVATE_THOUGHT_WINDOW_EXPIRED' if expired else 'PRIVATE_THOUGHT_WAITING_FOR_QUIET'
                    self.queue.finish(
                        row, 'EXPIRED' if expired else 'DEFERRED', reason,
                        defer_until_us=None if expired else quiet_until,
                    )
                    self._save_oper()
                    return {'queue_id': row['queue_id'], 'mode': 'NO_COGNITION', 'reason': reason, 'cycle': None}
            mode, reason = self.cognition.choose(row, event, self.subject,preview=False)
            result = None
            if mode == "NO_COGNITION":
                maintenance = getattr(self.subject, "maintain", None)
                if maintenance:
                    maintenance()
            elif mode == 'FULL_COGNITION' and self.cognition.provider_factory is not None:
                try:
                    port=self.cognition.provider_factory(event)
                    result=self.subject.cognize(event,model=port,authority=self.authority,policy=port.session.policy,
                        capabilities=self.config.capability_snapshot.capabilities,limitations=('NO_EXTERNAL_EXECUTION_IN_C_D',))
                except CoreError as exc:
                    if exc.code in {'RUNTIME_LEASE_LOST','PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE'}:raise
                    key='subject-cognition.'+row['subject_event_id']
                    attempted=self.store.db.execute('SELECT state FROM cognitive_requests WHERE request_key=?',(key,)).fetchone()
                    if not attempted:
                        # A source race is retirement, not resource pressure.
                        self.queue.cause_memories(tuple(Cause.model_validate_json(canonical(x)) for x in json.loads(row['cause_json'])),event.scope)
                        self.subject.situation(event,self.store.one('subject_events',row['subject_event_id']))
                        self.queue.finish(row,'DEFERRED','PROVIDER_RESOURCE_WAIT')
                    elif exc.code=='PREEMPTED_NO_AUTOMATIC_RETRY':
                        self.queue.finish(row,'DEFERRED','PREEMPTED_PROVIDER_UNKNOWN_NO_RETRY')
                    else:
                        self.queue.finish(row,'DONE','PROVIDER_CANDIDATE_UNAVAILABLE_NO_REPLAY')
                    self._save_oper()
                    return {'queue_id':row['queue_id'],'mode':'NO_COGNITION','reason':exc.code,'cycle':None}
                self.oper['last_cognition_us']=self.clock.utc_now_us()
            elif mode == "FULL_COGNITION":
                call = self.cognition.reserve(row)
                try:
                    policy = ContextPolicy(
                        policy_id="runtime-local-fixture",
                        allowed_scopes=self.config.scopes,
                        readable_privacy=self.config.privacy_classes,
                    )
                    result = self.subject.cognize(
                        event,
                        model=self.cognition.port(call),
                        authority=self.authority,
                        policy=policy,
                        capabilities=self.config.capability_snapshot.capabilities,
                        limitations=("NO_EXTERNAL_EXECUTION_IN_C_D",),
                    )
                    self.cognition.finish(call, "SUCCEEDED")
                except CognitionPreempted:
                    self.cognition.finish(call, "CANCELLED" if self.store.schema_target >= 11 else "FAILED")
                    self.queue.finish(row, "DEFERRED", "PREEMPTED_AT_NO_EFFECT_SAFE_POINT")
                    return {"queue_id": row["queue_id"], "mode": "NO_COGNITION", "reason": "PREEMPTED", "cycle": None}
                except TimeoutError:
                    self.cognition.finish(call, "TIMED_OUT")
                    result = self.subject.run(event)
                    reason = "MODEL_TIMEOUT_LIGHT_FALLBACK"
                except Exception as exc:
                    if isinstance(exc, CoreError) and str(exc) == "RUNTIME_LEASE_LOST":
                        raise
                    self.cognition.finish(call, "FAILED")
                    result = self.subject.run(event)
                    reason = "MODEL_FAILED_LIGHT_FALLBACK"
                self.oper["last_cognition_us"] = self.clock.utc_now_us()
            else:
                result = self.subject.run(event)
            if result and result.intention.kind != "NO_ACTION":
                self.oper["last_activity_us"] = self.clock.utc_now_us()
            if result:
                self._followup(row, event, result)
            self.queue.finish(row, "DONE", reason, result.cycle_id if result else None)
            checkpoint = self.store.db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
            if checkpoint[0] == 0:
                self.oper["last_successful_checkpoint_us"] = self.clock.utc_now_us()
            self._save_oper()
            return {"queue_id": row["queue_id"], "mode": mode, "reason": reason, "cycle": result}
        except CoreError as exc:
            if str(exc) == "RUNTIME_LEASE_LOST":
                raise
            # Retired/deleted sources and malformed semantic proposals do not
            # become new history, external replies or unlimited retries.
            self.queue.finish(row, "IGNORED", "SOURCE_RETIRED_OR_INVALID")
            self._save_oper()
            return {
                "queue_id": row["queue_id"],
                "mode": "NO_COGNITION",
                "reason": "SOURCE_RETIRED_OR_INVALID",
                "cycle": None,
            }
        finally:
            self._processing = None

    def _followup(self, row, event, result):
        key = row["queue_id"]
        if self.store.db.execute(
            "SELECT 1 FROM events WHERE source_namespace='runtime.followup' AND source_key=?", (key,)
        ).fetchone():
            return
        if result.intention.kind == "REFLECTION" and event.reflection_experience_id:
            self.subject.reflect(
                event.reflection_experience_id, authority=self.authority, apply=False, intention_id=result.intention_id
            )
        if self.work:
            self.work.after_cycle(result, event)
        with self.store.transaction(
            "runtime.cycle_followup_completed",
            {"cycle_id": result.cycle_id},
            source_namespace="runtime.followup",
            source_key=key,
        ):
            pass

    def _recover_followup(self):
        # C committed before a process died, but work adoption/settlement may not
        # have committed. Reuse that decision and the existing idempotent work
        # services. Never run C/model again or resend an uncertain effect.
        row = self.store.db.execute(
            "SELECT q.* FROM runtime_queue q WHERE q.outcome_code='RECOVERED_COMMITTED_CYCLE' AND NOT EXISTS (SELECT 1 FROM events e WHERE e.source_namespace='runtime.followup' AND e.source_key=q.queue_id) ORDER BY q.sequence_no LIMIT 1"
        ).fetchone()
        if not row:
            return None
        row = dict(row)
        try:
            event = self.queue.input(row)
            cycle = self.subject.result(self.store.one("subject_cycles", row["cycle_id"]))
            self._followup(row, event, cycle)
            code = "RECOVERED_SUBJECT_FOLLOWUP"
        except CoreError as exc:
            if exc.code == "RUNTIME_LEASE_LOST":
                raise
            code = "FOLLOWUP_REQUIRES_SOURCE_OR_PERMISSION_REVIEW"
            with self.store.transaction(
                "runtime.cycle_followup_review_required",
                {"queue_id": row["queue_id"], "code": exc.code},
                source_namespace="runtime.followup",
                source_key=row["queue_id"],
            ):
                pass
        self._save_oper()
        return {"queue_id": row["queue_id"], "mode": "NO_COGNITION", "reason": code, "cycle": None}

    def drain(self, limit=256):
        results = []
        for _ in range(limit):
            result = self.step()
            if result is None:
                break
            results.append(result)
        return results

    def living(self, scope=None):
        return project_self(
            self.store,
            entity_id=self.config.entity_id,
            scope=scope or self.config.scopes[0],
            privacy_classes=self.config.privacy_classes,
            environment=Environment(
                capabilities=self.config.capability_snapshot.capabilities,
                devices=self.config.capability_snapshot.devices,
                platforms=self.config.capability_snapshot.platforms,
                cognition_available=False if self.cognition.availability in {"DEGRADED", "UNAVAILABLE"} else None,
            ),
        )

    def health(self):
        now = self.clock.utc_now_us()
        lease = self.store.one("runtime_lease", self.store.identity["identity_id"])
        lost = False
        try:
            self.lease.assert_current()
        except CoreError:
            lost = True
        status = (
            "STOPPED"
            if self.stopped
            else "LOST"
            if lost
            else "DEGRADED"
            if self.cognition.availability in {"DEGRADED", "UNAVAILABLE"}
            else "WATCHING"
        )
        return RuntimeHealth(
            status=status,
            runtime_instance_id=self.lease.instance_id,
            epoch=self.lease.epoch,
            lease_status="LOST" if lost and not self.stopped else lease["state"],
            identity_id=self.store.identity["identity_id"],
            last_event=self.oper["last_event"],
            last_wake_us=self.oper["last_wake_us"],
            last_cognition_us=self.oper["last_cognition_us"],
            queue_depth=self.queue.depth(),
            deferred_count=self.store.db.execute(
                "SELECT count(*) FROM runtime_queue WHERE state='DEFERRED'"
            ).fetchone()[0],
            model_availability=self.cognition.availability,
            subject_revision=self.subject.revision,
            last_successful_checkpoint_us=self.oper["last_successful_checkpoint_us"],
            clock_us=now,
            time_since_interaction_us=None
            if self.oper["last_interaction_us"] is None
            else max(0, now - self.oper["last_interaction_us"]),
            time_since_activity_us=max(0, now - self.oper["last_activity_us"]),
        )

    def run(self, max_seconds=30):
        deadline = None if max_seconds == 0 else self.clock.monotonic_ns() + int(max_seconds * 1_000_000_000)
        try:
            while not self.stop_requested and (deadline is None or self.clock.monotonic_ns() < deadline):
                stamp = self.cadence.stamp()
                result = self.step()
                if result is None:
                    wait = self.next_wait_seconds()
                    if deadline is not None:
                        wait = min(wait, max(0, (deadline - self.clock.monotonic_ns()) / 1_000_000_000))
                    self.cadence.wait(wait, stamp)
        finally:
            self.stop()

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        self.cadence.close()
        self.queue.clear_transient()
        try:
            try:
                self._save_oper()
            except CoreError:
                pass
            self.lease.release()
        finally:
            self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
