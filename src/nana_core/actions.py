"""Authorized, budgeted actions. Unknown is a recoverable uncertainty, never a retry signal."""
import json
from .contracts import CAPABILITIES, VERIFY_CAPABILITY, CardArgs, CoreError, GrantSpec, Invocation, SourceArgs
from .storage import canonical, digest, uid

LEGAL = {
    "PROPOSED": {"READY", "BLOCKED", "CANCELLED"},
    "BLOCKED": {"READY", "BLOCKED", "CANCELLED"},
    "READY": {"DISPATCHING", "BLOCKED", "CANCELLED"},
    "DISPATCHING": {"PENDING_VERIFY", "UNKNOWN"},
    "PENDING_VERIFY": {"SUCCEEDED", "NOT_APPLIED", "FAILED_EFFECT", "UNKNOWN"},
    "UNKNOWN": {"SUCCEEDED", "NOT_APPLIED", "FAILED_EFFECT", "UNKNOWN"},
}


class OperatorAuthority:
    """Local operator boundary. Runtime keeps this object away from ModelPort."""
    def __init__(self, principal="offline-operator"):
        self.principal = principal


class ActionKernel:
    def _stored_payload(self,tx,payload,*,action=None):
        """Explicit v11 payloads inherit C provenance/erasure, not immutable prose."""
        from .continuity.records import RecordService
        support=getattr(self.store,'_governed_payload_support',None)
        if action and self.store.schema_target>=12:
            support=json.loads(action['args_json']).get('action_payload_record') or support
        if not support and action:
            support=json.loads(action['args_json']).get('action_payload_record')
            if not support:
                # A governed v9/v10 action may already need verification at an
                # explicit dev upgrade. Reuse its exact pre-existing provenance.
                link=self.store.db.execute("SELECT data_json FROM events WHERE kind='governance.action_linked' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(action['action_id'],)).fetchone()
                if link:support=json.loads(link[0])['data']['outcome_record_id']
        if not support:raise CoreError('ACTION_PAYLOAD_SUPPORT_REQUIRED')
        records=RecordService(self.store);parent=records.read(support)
        floor=self.registry.payload_privacy(payload) if self.store.schema_target>=12 and self.registry else None
        inputs=getattr(self.store,'_governed_input_memories',()) if action is None else ()
        rid=records.create(tx,kind='ACTION_PAYLOAD',scope=parent['scope'],payload=payload,records=(support,),memories=inputs,privacy_floor=floor)
        return rid,self.store.one('continuity_records',rid)['payload_artifact_id']

    def payload(self,action,field):
        raw=action[field]
        if raw is None:return None
        value=json.loads(raw)
        if self.store.schema_target>=11 and type(value) is dict and set(value)=={'action_payload_record'}:
            from .continuity.records import RecordService
            records=RecordService(self.store)
            if self.store.schema_target>=12 and not records.current_support(value['action_payload_record']):raise CoreError('ACTION_PAYLOAD_SOURCE_NOT_CURRENT')
            return canonical(records.read(value['action_payload_record'])['payload'])
        return raw

    def __init__(self, store, capability, authority: OperatorAuthority, *, registry=None):
        self.store, self.capability, self._authority = store, capability, authority
        # Trusted operator construction only. Default V1 remains closed reading.
        self.registry = registry
        self.capabilities = frozenset(registry.definitions) if registry else frozenset(CAPABILITIES)
        self.verify_capability = registry.verify_capability if registry else VERIFY_CAPABILITY
        if getattr(capability, "path", None) and capability.path.resolve() == store.path.resolve():
            raise CoreError("EXTERNAL_WORLD_MUST_BE_SEPARATE")

    def _offline_subject_fixture(self):
        if self.store.schema_target<9:return False
        from .continuity.autonomy.fixture_effects import OfflineEffectPort
        sealed = self.registry is None
        if self.store.schema_target>=12:
            from .continuity.open_agency.world import LocalWorldRegistry
            sealed = sealed or type(self.registry) is LocalWorldRegistry
        from .continuity.project_work.port import ProjectMaterialPort
        from .continuity.hands.port import OwnedApplicationPort
        if type(self.capability) is OwnedApplicationPort:
            self.capability.assert_owned()
            return self.capability.identity_id==self.store.identity['identity_id'] and sealed
        # Exact no-exec project adapter only; manifest is NOT execution authority.
        return type(self.capability) in {OfflineEffectPort,ProjectMaterialPort} and self.capability.identity_id==self.store.identity['identity_id'] and sealed

    def _execution_fence(self):
        if self.store.one('core_meta','cloud.shadow_runtime') and not self._offline_subject_fixture():
            raise CoreError('SHADOW_BLOCKED')
        if self.store.schema_target>=9:
            guard=getattr(self.store,'_governed_action_guard',None)
            if guard is None:raise CoreError('GOVERNANCE_FENCE_REQUIRED')
            guard()
        protocol=self.store.one('core_meta','cloud.execution_protocol')
        if protocol:
            phase=json.loads(protocol['value_json'])
            owner=self.store.one('core_meta','migration.execution_owner')
            owner=json.loads(owner['value_json']) if owner else None
            if not owner or owner['epoch']!=phase['epoch']:raise CoreError('HANDOFF_EPOCH_UNRECONCILED')
            actor=getattr(self.capability,'_actor',owner['actor'])
            allowed={'CORE_ACTIVE'} if actor=='core_simulator' else {'LEGACY_ACTIVE','SHADOW_CORE','CORE_READY','LEGACY_RESTORED'}
            if phase['state'] not in allowed:raise CoreError('HANDOFF_EXECUTION_FENCED')

    def _operator(self, authority):
        if authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")

    def set_budgets(self, values: dict, authority):
        self._operator(authority)
        if self.store.one('core_meta','cloud.shadow_runtime') and not self._offline_subject_fixture():raise CoreError('SHADOW_BLOCKED')
        if set(values) != {"write_attempts", "external_requests", "cost_micro_units"}:
            raise CoreError("INVALID_BUDGET_DIMENSIONS")
        with self.store.transaction("budget.configured", {"issuer": authority.principal}) as tx:
            for dimension, limit in values.items():
                if type(limit) is not int or limit < 0:
                    raise CoreError("INVALID_BUDGET")
                existing = self.store.one("budgets", dimension)
                tx.put("budgets", {"dimension": dimension, "limit_value": limit,
                    "held": existing["held"] if existing else 0, "spent": existing["spent"] if existing else 0})

    def grant(self, spec: GrantSpec, authority):
        self._operator(authority)
        if self.store.one('core_meta','cloud.shadow_runtime') and not self._offline_subject_fixture():raise CoreError('SHADOW_BLOCKED')
        if not set(spec.capabilities) <= self.capabilities | {self.verify_capability}:
            raise CoreError("UNKNOWN_CAPABILITY")
        if spec.expires_at_us <= spec.not_before_us:
            raise CoreError("INVALID_GRANT_TIME")
        grant_id = uid()
        with self.store.transaction("authorization.granted", {"issuer": authority.principal}) as tx:
            tx.put("grants", {"grant_id": grant_id, "issuer": authority.principal,
                "identity_id": self.store.identity["identity_id"], "not_before_us": spec.not_before_us,
                "expires_at_us": spec.expires_at_us, "revoked": 0, "body_json": spec.model_dump_json()})
        return grant_id

    def revoke(self, grant_id, authority):
        self._operator(authority)
        with self.store.transaction("authorization.revoked", {"grant_id": grant_id}) as tx:
            tx.update("grants", grant_id, revoked=1)

    def _grant_for(self, capability, resource, grant_id=None):
        now = self.store.clock.utc_now_us()
        high = self.store.one("core_meta", "auth_high_water_us")
        if high and now < json.loads(high["value_json"]) - 2_000_000:
            raise CoreError("CLOCK_ROLLBACK")
        effective_now = max(now, json.loads(high["value_json"]) if high else now)
        matching = []
        for grant in self.store.all("grants"):
            if grant_id is not None and grant["grant_id"] != grant_id:
                continue
            scope = json.loads(grant["body_json"])
            if capability in scope["capabilities"] and resource in scope["resources"]:
                matching.append(grant)
                if not grant["revoked"] and grant["not_before_us"] <= effective_now < grant["expires_at_us"]:
                    return grant
        if any(g["revoked"] for g in matching):
            raise CoreError("AUTH_REVOKED")
        if matching:
            raise CoreError("AUTH_EXPIRED")
        raise CoreError("AUTH_REQUIRED")

    def _stamp_auth_time(self, tx):
        high = self.store.one("core_meta", "auth_high_water_us")
        value = max(self.store.clock.utc_now_us(), json.loads(high["value_json"]) if high else 0)
        tx.put("core_meta", {"key": "auth_high_water_us", "value_json": canonical(value)})

    def _change(self, tx, action, state, **fields):
        if state not in LEGAL.get(action["state"], set()):
            raise CoreError("ILLEGAL_ACTION_TRANSITION")
        return tx.update("actions", action["action_id"], state=state,
                         version=action["version"] + 1, **fields)

    def _valid_args(self, capability, resource, args):
        if capability not in self.capabilities:
            raise CoreError("UNKNOWN_CAPABILITY")
        if self.registry:
            return self.registry.validate(capability, resource, args)
        model = CardArgs if capability == "reading.card.create" else SourceArgs
        parsed = model.model_validate(args)
        if capability.startswith("reading.source.") and parsed.source_id != resource:
            raise CoreError("RESOURCE_MISMATCH")
        return parsed.model_dump()

    def propose(self, capability, resource, args, goal_id=None, plan_id=None, effect_slot=None):
        self._execution_fence()
        args = self._valid_args(capability, resource, args)
        if effect_slot:
            old = self.store.db.execute("SELECT * FROM actions WHERE effect_slot=? AND state NOT IN ('CANCELLED','NOT_APPLIED')", (effect_slot,)).fetchone()
            if old:
                if (old["capability"], old["resource"], old["args_hash"]) != (capability, resource, digest(args)):
                    raise CoreError("EFFECT_SLOT_COLLISION")
                return old["action_id"]
        action_id = uid()
        with self.store.transaction("action.proposed", {"action_id": action_id}) as tx:
            stored_args=canonical(args)
            if self.store.schema_target>=11:
                rid,_=self._stored_payload(tx,args)
                stored_args=canonical({'action_payload_record':rid})
            tx.put("actions", {"action_id": action_id, "goal_id": goal_id, "plan_id": plan_id,
                "effect_slot": effect_slot, "idempotency_key": digest([self.store.identity["identity_id"], action_id]),
                "capability": capability, "resource": resource, "args_json": stored_args,
                "args_hash": digest(args), "state": "PROPOSED", "version": 1, "attempt_id": None,
                "result_json": None, "body_json": "{}"})
        return action_id

    def _reserve(self, tx, attempt_id, requirements):
        for dimension, amount in requirements.items():
            budget = self.store.one("budgets", dimension)
            if not budget or budget["spent"] + budget["held"] + amount > budget["limit_value"]:
                raise CoreError("BUDGET_EXHAUSTED")
            tx.update("budgets", dimension, held=budget["held"] + amount)
            tx.put("budget_holds", {"hold_id": uid(), "owner_id": attempt_id,
                "dimension": dimension, "amount": amount, "status": "HELD"})

    def _holds(self, tx, attempt_id, dimensions, release=False):
        for hold in self.store.all("budget_holds"):
            if hold["owner_id"] == attempt_id and hold["status"] == "HELD" and hold["dimension"] in dimensions:
                budget = self.store.one("budgets", hold["dimension"])
                tx.update("budgets", hold["dimension"], held=budget["held"] - hold["amount"],
                    spent=budget["spent"] + (0 if release else hold["amount"]))
                tx.update("budget_holds", hold["hold_id"], status="RELEASED" if release else "SPENT")

    def _attempt(self, tx, action, grant, kind):
        attempt_id = uid()
        count = sum(a["action_id"] == action["action_id"] for a in self.store.all("attempts"))
        tx.put("attempts", {"attempt_id": attempt_id, "action_id": action["action_id"],
            "grant_id": grant["grant_id"], "kind": kind, "attempt_no": count + 1,
            "started_at_us": None, "outcome": None, "receipt_event_id": None, "verification_event_id": None})
        return attempt_id

    def _invocation(self, action):
        args = json.loads(self.payload(action,'args_json'))
        if digest(args) != action["args_hash"]:
            raise CoreError("ACTION_ARGS_CORRUPT")
        return Invocation(action_id=action["action_id"], attempt_id=action["attempt_id"],
            capability=action["capability"], resource=action["resource"], args=args,
            args_hash=action["args_hash"], idempotency_key=action["idempotency_key"])

    def prepare(self, action_id):
        self._execution_fence()
        action = self.store.one("actions", action_id)
        if not action or action["state"] not in {"PROPOSED", "BLOCKED"}:
            raise CoreError("ILLEGAL_ACTION_TRANSITION")
        try:
            with self.store.transaction("action.reserved", {"action_id": action_id}) as tx:
                if json.loads(self.store.one("core_meta", "recovery_quarantine")["value_json"]):
                    raise CoreError("RESTORE_QUARANTINE")
                grant = self._grant_for(action["capability"], action["resource"])
                self._stamp_auth_time(tx)
                started = [a for a in self.store.all("attempts") if a["action_id"] == action_id
                           and a["kind"] == "EXECUTE" and a["started_at_us"] is not None]
                if len(started) >= json.loads(grant["body_json"])["max_attempts"]:
                    raise CoreError("ATTEMPTS_EXHAUSTED")
                attempt_id = self._attempt(tx, action, grant, "EXECUTE")
                requirements = {"external_requests": 1, "cost_micro_units": 1}
                if (self.registry.is_write(action["capability"]) if self.registry else action["capability"] == "reading.card.create"):
                    requirements["write_attempts"] = 1
                self._reserve(tx, attempt_id, requirements)
                self._change(tx, action, "READY", attempt_id=attempt_id, body_json="{}")
        except CoreError as exc:
            with self.store.transaction("action.blocked", {"reason": exc.code}) as tx:
                self._change(tx, action, "BLOCKED", body_json=canonical({"blocked_reason": exc.code}))
            raise

    def dispatch(self, action_id, fault=None):
        self._execution_fence()
        action = self.store.one("actions", action_id)
        if not action or action["state"] != "READY":
            raise CoreError("ILLEGAL_ACTION_TRANSITION")
        invocation = self._invocation(action)
        try:
            with self.store.transaction("action.dispatched", {"action_id": action_id}) as tx:
                if json.loads(self.store.one("core_meta", "recovery_quarantine")["value_json"]):
                    raise CoreError("RESTORE_QUARANTINE")
                attempt = self.store.one("attempts", action["attempt_id"])
                self._grant_for(action["capability"], action["resource"], attempt["grant_id"])
                self._holds(tx, action["attempt_id"], {"external_requests", "write_attempts"})
                tx.update("attempts", action["attempt_id"], started_at_us=self.store.clock.utc_now_us())
                self._stamp_auth_time(tx)
                self._change(tx, action, "DISPATCHING")
        except CoreError as exc:
            with self.store.transaction("action.blocked", {"reason": exc.code}) as tx:
                self._holds(tx, action["attempt_id"], {"external_requests", "write_attempts", "cost_micro_units"}, release=True)
                self._change(tx, action, "BLOCKED", body_json=canonical({"blocked_reason": exc.code}))
            raise
        if fault:
            fault("before_call")
        try:
            receipt = self.capability.execute(invocation)
            if fault:
                fault("after_effect")
        except Exception as exc:
            with self.store.transaction("action.unresolved", {"action_id": action_id, "error_type": type(exc).__name__}) as tx:
                self._change(tx, self.store.one("actions", action_id), "UNKNOWN")
            return "UNKNOWN"
        with self.store.transaction("action.receipt_received", {"action_id": action_id}) as tx:
            if self.store.schema_target>=11:
                _,tx.payload_id=self._stored_payload(tx,receipt.model_dump(mode='json'),action=self.store.one('actions',action_id))
            else:tx.payload_id = tx.artifact(receipt.model_dump_json().encode())
            tx.update("attempts", action["attempt_id"], receipt_event_id=tx.event_id)
            self._change(tx, self.store.one("actions", action_id), "PENDING_VERIFY")
        return "PENDING_VERIFY"

    def verify(self, action_id):
        if self.store.one('core_meta','cloud.shadow_runtime') and not self._offline_subject_fixture():raise CoreError('SHADOW_BLOCKED')
        action = self.store.one("actions", action_id)
        if action["state"] in {"SUCCEEDED", "NOT_APPLIED", "FAILED_EFFECT"}:
            return action["state"]
        if action["state"] not in {"PENDING_VERIFY", "UNKNOWN"}:
            raise CoreError("ILLEGAL_ACTION_TRANSITION")
        invocation = self._invocation(action)
        with self.store.transaction("action.verification_started", {"action_id": action_id}) as tx:
            grant = self._grant_for(self.verify_capability, action["resource"])
            self._stamp_auth_time(tx)
            verification_attempt = self._attempt(tx, action, grant, "VERIFY")
            self._reserve(tx, verification_attempt, {"external_requests": 1, "cost_micro_units": 1})
            self._holds(tx, verification_attempt, {"external_requests"})
            tx.update("attempts", verification_attempt, started_at_us=self.store.clock.utc_now_us())
        try:
            result = self.capability.verify(invocation)
        except Exception as exc:
            with self.store.transaction("action.unresolved", {"action_id": action_id, "error_type": type(exc).__name__}) as tx:
                tx.update("attempts", verification_attempt, outcome="UNKNOWN")
                self._change(tx, action, "UNKNOWN")
            return "UNKNOWN"
        state = {"MATCH": "SUCCEEDED", "FINAL_NO_EFFECT": "NOT_APPLIED", "EFFECT_MISMATCH": "FAILED_EFFECT", "INCONCLUSIVE": "UNKNOWN"}[result.verdict]
        with self.store.transaction("action.verified", {"action_id": action_id, "verdict": result.verdict}) as tx:
            if self.store.schema_target>=11:
                _,tx.payload_id=self._stored_payload(tx,result.model_dump(mode='json'),action=action)
                rid,_=self._stored_payload(tx,result.evidence.get('result'),action=action)
                stored_result=canonical({'action_payload_record':rid})
            else:
                tx.payload_id = tx.artifact(result.model_dump_json().encode())
                stored_result=canonical(result.evidence.get('result'))
            tx.update("attempts", verification_attempt, outcome=state, verification_event_id=tx.event_id)
            if state != "UNKNOWN":
                tx.update("attempts", action["attempt_id"], outcome=state, verification_event_id=tx.event_id)
                self._holds(tx, action["attempt_id"], {"cost_micro_units"})
            self._holds(tx, verification_attempt, {"cost_micro_units"})
            self._change(tx, action, state, result_json=stored_result,
                body_json=canonical({"verification_event_id": tx.event_id}))
        return state

    def run(self, action_id, fault=None):
        state = self.store.one("actions", action_id)["state"]
        if state in {"PROPOSED", "BLOCKED"}:
            self.prepare(action_id)
            state = "READY"
        if state == "READY":
            self.dispatch(action_id, fault=fault)
            state = self.store.one("actions", action_id)["state"]
        if state in {"UNKNOWN", "PENDING_VERIFY"}:
            return self.verify(action_id)
        return state

    def recover(self):
        results = {}
        for action in self.store.all("actions"):
            if action["state"] == "DISPATCHING":
                with self.store.transaction("action.recovery_unknown", {"action_id": action["action_id"]}) as tx:
                    self._change(tx, action, "UNKNOWN")
                action = self.store.one("actions", action["action_id"])
            if action["state"] in {"PENDING_VERIFY", "UNKNOWN"}:
                try:
                    results[action["action_id"]] = self.verify(action["action_id"])
                except CoreError as exc:
                    results[action["action_id"]] = exc.code
        return results

    def cancel(self, action_id):
        action = self.store.one("actions", action_id)
        with self.store.transaction("action.cancelled", {"action_id": action_id}) as tx:
            self._change(tx, action, "CANCELLED")
            if action["attempt_id"]:
                self._holds(tx, action["attempt_id"], {"external_requests", "write_attempts", "cost_micro_units"}, release=True)
