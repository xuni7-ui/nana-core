"""Read-only binding to original canonical activation and its operator scope.

This module cannot activate a subject, issue a Grant or record an approval.
Existing canonical receipt bytes/digests remain unchanged. The typed host binding
describes a channel/account; the original Manager and Grant authorize each action.
"""
from pathlib import Path
from typing import Literal

from pydantic import Field

from ..contracts import CoreError, DTO


class CanonicalActivation(DTO):
    subject_id: str = Field(min_length=1, max_length=128)
    lineage_binding: str = Field(pattern=r"^[a-f0-9]{64}$")
    old_writer_fence_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    approval_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    genesis_receipt_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    realm: Literal["PRODUCTION_SINGLE_SUBJECT"]


class PlatformActivation(DTO):
    canonical: CanonicalActivation
    binding_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    account_id: str | None = Field(default=None, pattern=r"^[0-9]{1,20}$")
    exclusive_writer_confirmed: bool = False


def require_platform_authority(app, activation, *, channel, exclusive_writer, account_id=None):
    """Verify original receipts and the exact host-bound channel; never mutate."""
    if type(activation) is not PlatformActivation or channel not in {"qq", "bilibili"}:
        raise CoreError("PLATFORM_CANONICAL_ACTIVATION_REQUIRED")
    from .live_api.canonical import verify_activation
    from .live_api.supervisor import existing_identity
    home = Path(app.home).absolute()
    if app.runtime.store.path.resolve() != (home / "subject/self.db").resolve():
        raise CoreError("PLATFORM_CANONICAL_STORE_MISMATCH")
    value = activation.canonical.model_dump()
    if value["subject_id"] != app.runtime.identity_id or app.runtime.store.identity["identity_id"] != app.runtime.identity_id:
        raise CoreError("PLATFORM_CANONICAL_IDENTITY_MISMATCH")
    identity, lineage, _ = existing_identity(home)
    if (identity, lineage) != (value["subject_id"], value["lineage_binding"]):
        raise CoreError("PLATFORM_CANONICAL_IDENTITY_MISMATCH")
    verify_activation(home, value)
    bindings = [b for b in app.config.surface_bindings if b.binding_id == activation.binding_id]
    platform = {"qq": "qq.onebot", "bilibili": "bilibili.account"}[channel]
    if (len(bindings) != 1 or not bindings[0].enabled or bindings[0].platform != platform
            or bindings[0].mode != "PLATFORM_ADAPTER_NO_SEND" or bindings[0].entity_id != app.runtime.config.entity_id
            or bindings[0].scope not in app.runtime.config.scopes):
        raise CoreError("PLATFORM_CHANNEL_UNBOUND")
    if account_id is not None and activation.account_id != str(account_id):
        raise CoreError("PLATFORM_ACCOUNT_SCOPE_MISMATCH")
    if exclusive_writer and activation.exclusive_writer_confirmed is not True:
        raise CoreError("PLATFORM_EXCLUSIVE_WRITER_SCOPE_REQUIRED")
    return {"subject_id": identity, "channel": channel, "binding_id": activation.binding_id,
            "source": "ORIGINAL_CANONICAL_ACTIVATION", "grants_created": False}
