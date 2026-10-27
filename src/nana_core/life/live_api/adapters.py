"""Host-bound ingress and legacy dry-run; neither platform nor text grants roles.

The connector authenticates a platform sender OUTSIDE the untrusted message.
A fixed host map supplies Subject/entity/scope. This V1 deliberately has no live
social transport: an existing Core delivery Grant plus separate cutover approval
must be qualified before a future sender may consume a candidate.
"""

from pydantic import Field
from ...contracts import DTO
from ...storage import digest, canonical
from .contracts import ApiError, MessageRequest, Role
from .auth import Principal


class ConnectorBinding(DTO):
    connector_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    sender_reference: str = Field(min_length=1, max_length=256, repr=False)
    subject_id: str
    surface_binding_id: str
    cutoff_us: int = Field(ge=0)
    enabled: bool = True


class PlatformEvent(DTO):
    event_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    thread_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    occurred_at_us: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=2048, repr=False)
    privacy_class: str = Field(pattern=r"^(PUBLIC|PROJECT)$")


class InboundConnector:
    def __init__(self, service, binding):
        self.service = service
        self.binding = binding
        from ..config import load_config

        config = load_config(service.supervisor.home)
        matches = [x for x in config.surface_bindings if x.binding_id == binding.surface_binding_id]
        if (
            binding.subject_id != service.binding.subject_id
            or len(matches) != 1
            or matches[0].entity_id != service.binding.entity_id
            or matches[0].scope != service.binding.scope
        ):
            raise ApiError("CONNECTOR_SUBJECT_OR_SCOPE_UNBOUND", 403)

    def receive(self, event, *, authenticated_sender_reference):
        # authenticated_sender_reference comes from a trusted signed platform
        # session, not message JSON or an "I am your sister" text assertion.
        b = self.binding
        if not b.enabled or authenticated_sender_reference != b.sender_reference:
            raise ApiError("PLATFORM_SENDER_UNBOUND", 403)
        event = PlatformEvent.model_validate(event)
        if event.occurred_at_us < b.cutoff_us:
            raise ApiError("PRE_CUTOVER_EVENT_NO_REPLAY", 409)
        key = "platform." + digest([b.connector_id, event.event_id])[:48]
        principal = Principal(
            "connector." + digest([b.connector_id, event.model_dump(mode="json")]),
            (Role.READER, Role.CONVERSATION),
            "CONNECTOR",
            None,
            self.service.auth.generation,
        )
        # Duplicate requests preserve the exact original envelope so a route or
        # epoch change cannot turn replay into a fresh Core dispatch.
        with self.service.write_lock:
            prior = self.service.ledger.document.read()["receipts"].get(key)
            if prior:
                # Stored request digest contains no body. Compare the platform
                # observation independently before returning a receipt.
                if prior["principal"] != principal.principal_id:
                    raise ApiError("PLATFORM_EVENT_COLLISION", 409)
                return self.service.receipt(principal, key)
            body = MessageRequest(
                client_request_id=key,
                idempotency_key=key,
                expected_revision=self.service.ledger.revision,
                run_generation=self.service.generation,
                owner_epoch=self.service.supervisor.status()["owner_epoch"],
                text=event.text,
                thread_id=event.thread_id,
                privacy_class=event.privacy_class,
            )
            result = self.service.send(principal, body, surface_binding_id=b.surface_binding_id)
            return result

    @staticmethod
    def deliver(*args, **kwargs):
        raise ApiError("REAL_SOCIAL_DELIVERY_NOT_AUTHORIZED", 403)


def reconcile_legacy(bundles):
    """Hash-only reconciliation over explicitly supplied bounded exporter output.

    Does not read Iris, a live DB, a private body, credentials or another machine.
    Does not import truth, relationship roles, old Grants or old action success.
    A real exporter capture/import still needs the separate scoped authorization.
    """
    if not 1 <= len(bundles) <= 64:
        raise ApiError("LEGACY_BATCH_BOUND")
    sources = {}
    seen = {}
    conflicts = []
    duplicates = 0
    gaps = set()
    for bundle in bundles:
        if bundle.get("mode") != "hash-only" or bundle.get("total_records", 100000) > 100:
            raise ApiError("HASH_ONLY_BOUNDED_EXPORT_REQUIRED", 403)
        check = dict(bundle)
        claimed = check.pop("manifest_hash", None)
        if digest(check) != claimed:
            raise ApiError("LEGACY_MANIFEST_MISMATCH", 409)
        source = bundle["source_identity"]
        sources[source] = sources.get(source, 0) + bundle["total_records"]
        if len(bundle["records"]) != bundle["total_records"]:
            raise ApiError("LEGACY_COUNT_MISMATCH", 409)
        for row in bundle["records"]:
            if row["payload"] is not None:
                raise ApiError("PRIVATE_BODY_NOT_AUTHORIZED", 403)
            key = canonical([source, row["stable_legacy_id"]])
            value = row["payload_hash"]
            if key in seen:
                if seen[key] != value:
                    conflicts.append(key)
                else:
                    duplicates += 1
            seen[key] = value
            if row["time_quality"] != "EXACT":
                gaps.add("NON_EXACT_LEGACY_TIME")
            for relation in row.get("relationship", {}).values():
                if relation["status"] != "RESOLVED":
                    gaps.add("UNRESOLVED_LEGACY_RELATION")
    return {
        "state": "CONFLICT_REVIEW_REQUIRED" if conflicts else "DRY_RUN_RECONCILED_NOT_IMPORTED",
        "source_counts": sources,
        "unique_records": len(seen),
        "duplicate_rows": duplicates,
        "conflict_ids": sorted(set(conflicts)),
        "known_gaps": sorted(gaps),
        "history_imported": False,
        "relationship_authority_imported": False,
        "core_identity_created": False,
        "external_effects_replayed": 0,
        "private_text_read": False,
    }
