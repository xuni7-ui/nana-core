import json
from nana_core.storage import canonical


class ScriptedTransport:
    """Engineering protocol fixture. Never a real model or semantic proof."""
    is_real_transport = False

    def __init__(self, omit_learned_step=False, mutate=None):
        self.calls = 0
        self.payloads = []
        self.omit_learned_step, self.mutate = omit_learned_step, mutate

    def send(self, endpoint, payload):
        self.calls += 1
        self.payloads.append(payload)
        envelope = json.loads(payload)
        data = json.loads(envelope["messages"][1]["content"])
        req, context = data["request"], data["continuity"]
        active = context["active_experiences"] if data["observation_kind"] == "reading" else []
        identity = req["identity_snapshot"]
        proposal = None
        if data["observation_kind"] == "reading":
            steps = [{"capability": "reading.source.read", "resource": req["source_id"]}]
            if active and not self.omit_learned_step:
                steps.append({"capability": "reading.source.locate", "resource": req["source_id"]})
            steps.append({"capability": "reading.card.create", "resource": req["card_resource"]})
            proposal = {"purpose": "Engineering fixture reading note.", "steps": steps}
        reply = {"identity": {"identity_id": req["identity_id"], "revision": req["identity_revision"],
            "identity_snapshot": identity,
            "charter": identity["charter"], "permission_source": "operator_grant",
            "history_refs": [context["memories"][0]["created_event_id"]]},
            "experience": {"rule_refs": [s["ref"] for s in active],
                "scope": "reading_card" if active else "none", "required_output": "locator" if active else "none",
                "support_refs": list(dict.fromkeys(r for s in active for r in s["support_refs"])),
                "authorizes_new_permissions": False},
            "proposal": proposal, "rationale": "Explicitly scripted transport fixture; not semantic model evidence."}
        if self.mutate:
            self.mutate(reply)
        return canonical({"id": "fixture-response", "model": "fixture-protocol-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 100},
            "choices": [{"finish_reason": "stop", "message": {"content": canonical(reply)}}]}).encode()
