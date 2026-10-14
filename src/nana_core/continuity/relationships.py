"""Relationship is a sourced projection, with no affection counter or identity write."""
from ..contracts import DTO
from .memory import MemoryService
from .records import RecordService


class RelationshipView(DTO):
    entity_id: str
    memory_ids: tuple[str, ...]
    shared_history: tuple[str, ...]
    known_preferences: tuple[str, ...]
    interaction_norms: tuple[str, ...]
    boundaries: tuple[str, ...]
    unresolved_topics: tuple[str, ...]
    adopted_commitment_ids: tuple[str, ...]
    shared_project_ids: tuple[str, ...]


def relationship_view(store, entity_id, *, scopes, privacy_classes):
    memory = MemoryService(store)
    items = memory.query(entity_ids=(entity_id,), scopes=scopes, privacy_classes=privacy_classes)
    relational = [r for r in items if r["memory_type"] in {"RELATIONAL", "EPISODIC", "SEMANTIC"}]
    def selected(prefix):
        return tuple(r["text"] for r in relational if (r["predicate_key"] or "").startswith(prefix))
    records = RecordService(store)
    def visible(row):
        record = store.one("continuity_records", row["record_id"])
        return (record["lifecycle"] == "ACTIVE" and record["scope"] in scopes
            and record["privacy_class"] in privacy_classes and records.current_support(row["record_id"]))
    commitments = tuple(r["commitment_id"] for r in store.all("commitments") if r["entity_id"] == entity_id
        and r["state"] in {"ADOPTED", "ACTIVE"} and visible(r))
    projects = tuple(r["project_id"] for r in store.all("projects") if r["entity_id"] == entity_id
        and r["state"] in {"ACTIVE", "PAUSED"} and visible(r))
    return RelationshipView(entity_id=entity_id, memory_ids=tuple(r["memory_id"] for r in relational),
        shared_history=tuple(r["text"] for r in relational if r["memory_type"] == "EPISODIC"),
        known_preferences=selected("preference."), interaction_norms=selected("relationship.norm"),
        boundaries=selected("relationship.boundary"), unresolved_topics=selected("relationship.open"),
        adopted_commitment_ids=commitments, shared_project_ids=projects)
