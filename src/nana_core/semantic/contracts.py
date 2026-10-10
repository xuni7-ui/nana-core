"""Non-secret operator configuration and untrusted semantic responses."""
import re
from pathlib import Path
from urllib.parse import urlsplit
from typing import Literal
from pydantic import Field, model_validator
from ..contracts import CoreError, DTO, PlanProposal


class Endpoint(DTO):
    alias: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    base_url: str
    model: str = Field(min_length=1, max_length=128)
    account_scope: Literal["development", "local_offline"]
    funding: Literal["existing_quota", "local_offline"]
    # Operator declaration; successful HTTP alone is not evidence of inference.
    service_kind: Literal["real_model", "protocol_simulator", "unverified"] = "unverified"
    credential_env: str | None = None
    timeout_seconds: int = Field(default=45, ge=1, le=120)
    max_input_bytes: int = Field(default=48_000, ge=1024, le=100_000)
    max_output_tokens: int = Field(default=1200, ge=256, le=4096)
    # Conservative operator-supplied upper rates, micro currency units / token.
    input_rate_micro: int = Field(default=0, ge=0)
    output_rate_micro: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def endpoint_boundary(self):
        url = urlsplit(self.base_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("endpoint must not contain credentials, query or fragment")
        if url.scheme != "https" and not (url.scheme == "http" and local):
            raise ValueError("HTTPS required except loopback development servers")
        if self.account_scope == "local_offline" and (not local or self.funding != "local_offline"):
            raise ValueError("local_offline requires loopback and local funding")
        if self.service_kind == "protocol_simulator" and not local:
            raise ValueError("protocol simulator must be loopback")
        if self.account_scope == "development" and self.funding != "existing_quota":
            raise ValueError("development uses existing quota only")
        if self.credential_env and not re.fullmatch(r"NANA_S5_DEV_[A-Z0-9_]+", self.credential_env):
            raise ValueError("only dedicated development credential bindings are accepted")
        if not local and not self.credential_env:
            raise ValueError("remote endpoint requires explicit development binding")
        return self


class ModelBudget(DTO):
    max_calls: int = Field(default=16, ge=1, le=32)
    max_reserved_input_bytes: int = Field(default=768_000, ge=1)
    max_reserved_output_tokens: int = Field(default=19_200, ge=1)
    max_reserved_cost_micro: int = Field(default=0, ge=0)
    currency: str = Field(default="operator_quota", min_length=1, max_length=32)


class RunConfig(DTO):
    schema_version: Literal[1] = 1
    endpoints: tuple[Endpoint, ...] = Field(default=(), max_length=2)
    budget: ModelBudget = Field(default_factory=ModelBudget)

    @model_validator(mode="after")
    def distinct_models(self):
        if len({e.alias for e in self.endpoints}) != len(self.endpoints):
            raise ValueError("endpoint aliases must be distinct")
        if len({(e.base_url, e.model) for e in self.endpoints}) != len(self.endpoints):
            raise ValueError("two identical endpoints/models are not model migration")
        return self


def load_run_config(path=None):
    """Only explicit non-secret development config; errors never echo input values."""
    if path is None:
        return RunConfig()
    try:
        file = Path(path)
        if file.is_symlink() or file.stat().st_size > 32_768:
            raise ValueError("config boundary")
        return RunConfig.model_validate_json(file.read_bytes())
    except Exception:
        raise CoreError("MODEL_CONFIG_REJECTED") from None


class IdentityUnderstanding(DTO):
    identity_id: str
    revision: int
    identity_snapshot: dict
    charter: tuple[str, ...]
    permission_source: Literal["operator_grant"]
    history_refs: tuple[str, ...]


class ExperienceUnderstanding(DTO):
    rule_refs: tuple[str, ...]
    scope: Literal["reading_card", "none"]
    required_output: Literal["locator", "none"]
    support_refs: tuple[str, ...]
    authorizes_new_permissions: Literal[False]


class SemanticReply(DTO):
    identity: IdentityUnderstanding
    experience: ExperienceUnderstanding
    proposal: PlanProposal | None
    rationale: str = Field(min_length=1, max_length=2000)


class EvaluationCase(DTO):
    case_id: str
    kind: Literal["reading", "unrelated"]
    raw_text: str
    source_id: str
    card_resource: str
    occurred_at: str
    locate_authorized: bool = True
