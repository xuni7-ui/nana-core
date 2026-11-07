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
    # Each established family gets a bounded slice before unrelated facts can
    # consume its retrieval budget. This is a projection of the original Store,
    # not another relationship authority or a strength/affection counter.
    query = dict(entity_ids=(entity_id,), scopes=scopes, privacy_classes=privacy_classes)
    selected_rows = {}
    for prefix in ("preference.", "relationship.norm", "relationship.boundary", "relationship.open"):
        for row in memory.query(**query, predicate_prefixes=(prefix,),
                                memory_types=("RELATIONAL", "EPISODIC", "SEMANTIC"), limit=24):
            selected_rows[row["memory_id"]] = row
    for kind, limit in (("EPISODIC", 24), ("RELATIONAL", 8)):
        for row in memory.query(**query, memory_types=(kind,), limit=limit):
            selected_rows.setdefault(row["memory_id"], row)
    relational = list(selected_rows.values())
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
