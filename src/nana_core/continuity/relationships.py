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
    # Select authorized metadata once, then reserve each established family a
    # bounded slice. Six independent scans regress long-lived large Stores.
    # Payloads stay behind the same original MemoryService.read source fence.
    memory._fresh()
    where, args = memory._query_filter((entity_id,), scopes, privacy_classes, False,
                                      ("RELATIONAL", "EPISODIC", "SEMANTIC"))
    prefixes = ("preference.", "relationship.norm", "relationship.boundary", "relationship.open")
    matches = ["substr(m.predicate_key,1,length(?))=?" for _ in prefixes]
    prefix_args = [value for prefix in prefixes for value in (prefix, prefix)]
    family = "CASE " + " ".join(
        f"WHEN {condition} THEN {index}" for index, condition in enumerate(matches)
    ) + " WHEN m.memory_type='EPISODIC' THEN 4 ELSE 5 END"
    eligible = "(m.memory_type IN ('RELATIONAL','EPISODIC') OR (m.predicate_key IS NOT NULL AND (" + " OR ".join(matches) + ")))"
    rows = store.db.execute(
        "WITH eligible AS MATERIALIZED (SELECT m.memory_id,m.authority,m.importance,"
        "m.significance,m.event_time_us,m.rowid AS ordinal," + family + " AS family "
        "FROM memories m WHERE " + where + " AND " + eligible + "), "
        "ranked AS (SELECT *,ROW_NUMBER() OVER (PARTITION BY family ORDER BY "
        "(authority='DIRECT') DESC,importance DESC,significance DESC,event_time_us DESC,ordinal) AS position "
        "FROM eligible) SELECT memory_id FROM ranked WHERE position<=CASE WHEN family=5 THEN 8 ELSE 24 END "
        "ORDER BY family,position", [*prefix_args, *args, *prefix_args]
    ).fetchall()
    relational = [memory.read(row[0]) for row in rows]
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
