"""Structured project revisions recover progress without replaying chat."""
import json
from typing import Annotated, Literal

from pydantic import Field

from ..contracts import CoreError, DTO
from ..actions import OperatorAuthority
from .records import RecordService

ShortText = Annotated[str, Field(min_length=1, max_length=2048)]


class Milestone(DTO):
    milestone_id: str = Field(min_length=1, max_length=96)
    title: str = Field(min_length=1, max_length=256)
    state: Literal["PENDING", "ACTIVE", "COMPLETED", "BLOCKED"]


class ProjectContent(DTO):
    goal: str = Field(min_length=1, max_length=2048)
    current_state: str = Field(min_length=1, max_length=2048)
    milestones: tuple[Milestone, ...] = Field(default=(), max_length=64)
    decisions: tuple[ShortText, ...] = Field(default=(), max_length=64)
    open_questions: tuple[ShortText, ...] = Field(default=(), max_length=64)
    blockers: tuple[ShortText, ...] = Field(default=(), max_length=64)
    recent_progress: tuple[ShortText, ...] = Field(default=(), max_length=64)
    next_actions: tuple[ShortText, ...] = Field(default=(), max_length=64)


class ProjectState(DTO):
    project_id: str
    revision: int
    state: Literal["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"]
    content: ProjectContent
    source_memory_ids: tuple[str, ...]
    support_current: bool


class ProjectService:
    def __init__(self, store, authority):
        if not isinstance(authority, OperatorAuthority):
            raise CoreError("OPERATOR_AUTHORITY_REQUIRED")
        self.store, self._authority, self.records = store, authority, RecordService(store)

    def save(self, *, project_id, entity_id, scope, content: ProjectContent,
             source_memory_ids, expected_revision, authority, state="ACTIVE"):
        if authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        if state not in {"ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"}:
            raise CoreError("INVALID_PROJECT_STATE")
        if not self.store.one("entities", entity_id):
            raise CoreError("ENTITY_BINDING_REQUIRED")
        with self.store.transaction("project.revised") as tx:
            old = self.store.one("projects", project_id)
            if type(expected_revision) is not int or (old["revision"] if old else 0) != expected_revision:
                raise CoreError("STALE_PROJECT_REVISION")
            if old and (old["entity_id"], old["scope"]) != (entity_id, scope):
                raise CoreError("PROJECT_BINDING_CONFLICT")
            record_id = self.records.create(tx, kind="PROJECT", scope=scope,
                payload=content.model_dump(mode="json"), memories=source_memory_ids,
                supersedes=old["record_id"] if old else None)
            now = self.store.clock.utc_now_us()
            tx.put("projects", {"project_id": project_id, "entity_id": entity_id, "scope": scope,
                "record_id": record_id, "revision": expected_revision + 1, "state": state,
                "created_at_us": old["created_at_us"] if old else now, "updated_at_us": now})
        return self.get(project_id)

    def get(self, project_id):
        row = self.store.one("projects", project_id)
        if not row:
            raise CoreError("PROJECT_MISSING")
        record = self.records.read(row["record_id"])
        return ProjectState(project_id=project_id, revision=row["revision"], state=row["state"],
            content=ProjectContent.model_validate_json(json.dumps(record["payload"])),
            source_memory_ids=self.records.support(row["record_id"]),
            support_current=self.records.current_support(row["record_id"]))
