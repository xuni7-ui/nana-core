"""Identity revisions require trusted application authority and compare-and-swap.

Models receive a snapshot, never this service or its authority object. Charter
changes are deliberately absent: memory/learning cannot expand governance.
"""
import json
from typing import Literal

from pydantic import Field

from ..contracts import CoreError, DTO
from ..actions import OperatorAuthority
from ..storage import canonical, uid


class IdentityProvenance(DTO):
    source: Literal["ORIGINAL_STORE_BOOTSTRAP", "OPERATOR_REVIEW"]
    reference_id: str = Field(min_length=1, max_length=128)


class IdentityRevision(DTO):
    revision_id: str
    identity_id: str
    schema_version: Literal[1] = 1
    revision: int
    supersedes: str | None
    change_reason: str
    provenance: IdentityProvenance
    authority: Literal["BOOTSTRAP", "OPERATOR_REVIEW"]
    created_at_us: int


class CanonicalIdentity(DTO):
    identity_id: str
    schema_version: Literal[1] = 1
    revision: int
    name: str
    charter: tuple[str, ...]
    expression_defaults: dict[str, str]
    created_at_us: int
    updated_at_us: int
    provenance: IdentityProvenance
    authority: Literal["BOOTSTRAP", "OPERATOR_REVIEW"]
    supersedes: str | None
    change_reason: str


class IdentityService:
    def __init__(self, store, authority):
        if not isinstance(authority, OperatorAuthority):
            raise CoreError("OPERATOR_AUTHORITY_REQUIRED")
        self.store, self._authority = store, authority
        if not store.all("identity_revisions"):
            body = store.identity
            event = store.event(body["created_event_id"])
            with store.transaction("self.identity_adopted") as tx:
                reason = tx.artifact(b"Adopt existing Store identity without creating another subject")
                tx.put("identity_revisions", {
                    "revision_id": uid(), "identity_id": body["identity_id"],
                    "revision": body["revision"], "schema_version": 1, "supersedes": None,
                    "body_json": body["body_json"],
                    "provenance_json": IdentityProvenance(source="ORIGINAL_STORE_BOOTSTRAP",
                        reference_id=body["created_event_id"]).model_dump_json(),
                    "authority": "BOOTSTRAP", "reason_artifact_id": reason,
                    "created_at_us": event["recorded_at_us"], "event_id": tx.event_id})
        if "entities" in store.keys and not store.one("entities", store.identity["identity_id"]):
            with store.transaction("self.entity_bound") as tx:
                tx.put("entities", {"entity_id": store.identity["identity_id"], "entity_type": "SELF",
                                    "created_at_us": store.clock.utc_now_us()})

    def current(self):
        row = self.store.all("identity_revisions")[-1]
        body = json.loads(row["body_json"])
        return CanonicalIdentity(identity_id=row["identity_id"], revision=row["revision"],
            name=body["name"], charter=tuple(body["charter"]),
            expression_defaults=body["expression_defaults"],
            created_at_us=self.store.all("identity_revisions")[0]["created_at_us"],
            updated_at_us=row["created_at_us"],
            provenance=IdentityProvenance.model_validate_json(row["provenance_json"]),
            authority=row["authority"], supersedes=row["supersedes"],
            change_reason=self.store.artifact(row["reason_artifact_id"]).decode())

    def revise_expression(self, *, expected_revision, style: str, reason: str,
                          provenance: IdentityProvenance, authority):
        if authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        if (type(expected_revision) is not int or type(style) is not str or
                not 1 <= len(style) <= 128 or type(reason) is not str or not 1 <= len(reason) <= 1024
                or provenance.source != "OPERATOR_REVIEW"):
            raise CoreError("INVALID_IDENTITY_CHANGE")
        with self.store.transaction("self.identity_revised") as tx:
            old = self.store.all("identity_revisions")[-1]
            if old["revision"] != expected_revision:
                raise CoreError("STALE_IDENTITY_REVISION")
            body = json.loads(old["body_json"])
            body["expression_defaults"] = {"style": style}
            tx.put("identity_revisions", {**old, "revision_id": uid(),
                "revision": old["revision"] + 1, "supersedes": old["revision_id"],
                "body_json": canonical(body), "provenance_json": provenance.model_dump_json(),
                "authority": "OPERATOR_REVIEW", "reason_artifact_id": tx.artifact(reason.encode()),
                "created_at_us": self.store.clock.utc_now_us(), "event_id": tx.event_id})
            tx.update("identities", old["identity_id"], revision=old["revision"] + 1,
                      body_json=canonical(body))
        return self.current()

