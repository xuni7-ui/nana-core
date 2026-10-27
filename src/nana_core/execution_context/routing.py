"""Host-local target selection, never a planner, credential source or Grant.

Channels are explicit trusted runtime objects. The router does not discover SSH,
Docker sockets, mounts or credentials, and cannot turn a path into authority.
An external adapter must authenticate its peer before exposing this interface.
Only metadata diagnostics may choose a different available pre-dispatch channel;
actual actions keep the channel/context pinned by the original Kernel.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Protocol
import time

from pydantic import Field, model_validator

from ..contracts import CoreError, DTO
from ..ports import CapabilityPort
from ..storage import canonical, digest
from .contracts import ExecutionContext, PathObservation
from .probe import _path_parts


class TargetBinding(DTO):
    target_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    context_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    scope: Literal["HOST", "CONTAINER", "EXTERNAL_DEVICE", "UNKNOWN"]
    channel_ids: tuple[str, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.channel_ids)) != len(self.channel_ids):
            raise ValueError("DUPLICATE_EXECUTION_CHANNEL")
        return self


class ResourceBinding(DTO):
    """Exact existing capability resource -> target/path; not an arbitrary path API."""

    resource: str = Field(min_length=1, max_length=512)
    target_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    path: str = Field(min_length=1, max_length=4096)
    capabilities: tuple[str, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def valid(self):
        _path_parts(self.path)
        if self.path != "/" + "/".join(_path_parts(self.path)):
            raise ValueError("CANONICAL_EXECUTION_PATH_REQUIRED")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("DUPLICATE_EXECUTION_CAPABILITY")
        return self


class RouteSnapshot(DTO):
    version: Literal[1] = 1
    source_context: ExecutionContext
    target_context: ExecutionContext
    target_id: str
    channel_id: str
    transport: Literal["LOCAL", "HOST_OPERATOR", "SSH"]
    resource: str
    path: str
    binding_digest: str
    selected_at_us: int
    path_observation: PathObservation | None = None
    grants_authority: Literal[False] = False


class ContextProbe(Protocol):
    """Trusted peer-side observation API, not a model-produced context report."""

    def capture(self) -> ExecutionContext: ...
    def observe(self, path: str) -> PathObservation: ...


@dataclass(frozen=True)
class ExecutionChannel:
    """Injected authenticated adapter; its peer-side probe and port share context.

    LOCAL uses LocalContextProbe and the existing CapabilityPort. HOST_OPERATOR
    and SSH require explicit host-side authenticated implementations; their mere
    labels never establish a connection. No transport commands are constructed.
    """

    channel_id: str
    kind: Literal["LOCAL", "HOST_OPERATOR", "SSH"]
    probe: ContextProbe
    port: CapabilityPort | None = None

    def __post_init__(self):
        if not self.channel_id or len(self.channel_id) > 128 or self.kind not in {"LOCAL", "HOST_OPERATOR", "SSH"}:
            raise CoreError("EXECUTION_CHANNEL_INVALID")


def require_identity(context: ExecutionContext):
    if (type(context) is not ExecutionContext or context.unknown_fields
        or context.user_namespace is None or context.mount_namespace is None
        or context.root_device is None or context.root_inode is None
        or context.mount_table_digest is None
        or not context.uid_map or not context.gid_map):
        raise CoreError("EXECUTION_CONTEXT_UNKNOWN")


def _require_current_capture(context, now_us):
    require_identity(context)
    if context.observed_at_us > now_us or now_us - context.observed_at_us > 5_000_000:
        raise CoreError("EXECUTION_CONTEXT_STALE")


def _require_matching_path(evidence, observation, expected_path):
    requested = evidence["requested_path"]
    if requested != observation.requested_path or (expected_path is not None and requested != expected_path):
        raise ValueError("path mismatch")
    try:
        normalized = "/" + "/".join(_path_parts(requested))
    except CoreError:
        raise ValueError("invalid observed path") from None
    actual = normalized if observation.status == "PRESENT" else None
    if observation.actual_path != actual:
        raise ValueError("actual path mismatch")


def require_fresh(evidence: dict, *, expected_target: str, max_age_us: int,
                  now_us: int | None = None, expected_path: str | None = None):
    """Validate metadata evidence, not an assertion that a former check is current."""
    now = time.time_ns() // 1000 if now_us is None else now_us
    try:
        observation = PathObservation.model_validate_json(canonical(evidence["observation"]))
        source = ExecutionContext.model_validate_json(canonical(evidence["source_context"]))
        require_identity(source)
        require_identity(observation.context)
        _require_matching_path(evidence, observation, expected_path)
        times = (evidence["observed_at_us"], observation.observed_at_us,
                 source.observed_at_us, observation.context.observed_at_us)
        if (evidence["target_id"] != expected_target
            or observation.context.target_id != expected_target
            or evidence["target_context_id"] != observation.context.context_id
            or not evidence["channel_id"] or type(max_age_us) is not int or max_age_us < 0
            or any(type(t) is not int or t > now or now - t > max_age_us for t in times)):
            raise ValueError("stale or mismatched")
    except (KeyError, TypeError, ValueError):
        raise CoreError("EXECUTION_EVIDENCE_STALE_OR_MISMATCHED") from None
    return observation


class ExecutionContextRouter:
    """Resolve explicit targets, preserving UNKNOWN and namespace boundaries."""

    def __init__(self, source_probe, *, targets, channels, resources=(), clock_us=None):
        if len(targets) > 64 or len(channels) > 64 or len(resources) > 256:
            raise CoreError("EXECUTION_CONFIGURATION_BOUND")
        self.source_probe = source_probe
        self.clock_us = clock_us or (lambda: time.time_ns() // 1000)
        self.targets = MappingProxyType({item.target_id: item for item in targets})
        self.channels = MappingProxyType({item.channel_id: item for item in channels})
        self.resources = MappingProxyType({item.resource: item for item in resources})
        if (any(type(x) is not TargetBinding for x in targets)
            or any(type(x) is not ExecutionChannel for x in channels)
            or any(type(x) is not ResourceBinding for x in resources)
            or len(self.targets) != len(targets) or len(self.channels) != len(channels)
            or len(self.resources) != len(resources)
            or any(x.target_id not in self.targets for x in resources)):
            raise CoreError("EXECUTION_CONFIGURATION_INVALID")
        # A declared channel may be unavailable; don't fabricate it from a name.

    def _target(self, target_id):
        target = self.targets.get(target_id)
        if target is None:
            raise CoreError("EXECUTION_TARGET_UNBOUND")
        return target

    def _capture(self, channel, target):
        try:
            context = channel.probe.capture()
        except (OSError, TimeoutError):
            raise CoreError("EXECUTION_CHANNEL_UNAVAILABLE") from None
        require_identity(context)
        if (context.context_id != target.context_id or context.target_id != target.target_id
            or context.scope != target.scope):
            raise CoreError("EXECUTION_TARGET_CONTEXT_MISMATCH")
        try:
            source = self.source_probe.capture()
        except (OSError, TimeoutError):
            raise CoreError("EXECUTION_SOURCE_CONTEXT_UNAVAILABLE") from None
        now = self.clock_us()
        _require_current_capture(source, now)
        _require_current_capture(context, now)
        if channel.kind == "LOCAL" and (source.context_id != context.context_id or source.scope != context.scope):
            raise CoreError("EXECUTION_LOCAL_TARGET_MISMATCH")
        if (source.context_id == context.context_id and source.scope != context.scope
            and "UNKNOWN" not in {source.scope, context.scope}):
            raise CoreError("EXECUTION_SCOPE_IDENTITY_CONFLICT")
        if target.scope == "HOST" and context.observed_kind == "CONTAINER_HINTS":
            raise CoreError("EXECUTION_HOST_CONTAINER_CONTRADICTION")
        return source, context

    def _choose(self, target, *, require_port=False):
        rank = {"LOCAL": 0, "HOST_OPERATOR": 1, "SSH": 2}
        choices = [self.channels[key] for key in target.channel_ids if key in self.channels]
        choices.sort(key=lambda ch: rank[ch.kind])
        reasons = []
        for channel in choices:
            if require_port and channel.port is None:
                reasons.append("EXECUTION_CAPABILITY_CHANNEL_UNAVAILABLE")
                continue
            try:
                source, context = self._capture(channel, target)
                return channel, source, context
            except CoreError as exc:
                reasons.append(exc.code)
        if reasons:
            # Preserve a mismatch as a diagnostic cause, not a missing host file.
            raise CoreError(reasons[0])
        raise CoreError("EXECUTION_CHANNEL_UNAVAILABLE")

    def select(self, resource, capability):
        binding = self.resources.get(resource)
        if binding is None or capability not in binding.capabilities:
            raise CoreError("EXECUTION_RESOURCE_UNBOUND")
        channel, source, context = self._choose(self._target(binding.target_id), require_port=True)
        return RouteSnapshot(source_context=source, target_context=context,
                             target_id=binding.target_id, channel_id=channel.channel_id,
                             transport=channel.kind, resource=resource, path=binding.path,
                             binding_digest=digest(binding.model_dump(mode="json")), selected_at_us=self.clock_us())

    def channel_for(self, snapshot: RouteSnapshot):
        """Recheck the exact pinned channel. No fallback after action reservation."""
        binding = self.resources.get(snapshot.resource)
        channel = self.channels.get(snapshot.channel_id)
        if (binding is None or channel is None or channel.kind != snapshot.transport
            or snapshot.channel_id not in self._target(snapshot.target_id).channel_ids
            or binding.target_id != snapshot.target_id or binding.path != snapshot.path
            or digest(binding.model_dump(mode="json")) != snapshot.binding_digest):
            raise CoreError("EXECUTION_ROUTE_CHANGED")
        source, context = self._capture(channel, self._target(snapshot.target_id))
        if (source.context_id != snapshot.source_context.context_id
            or context.context_id != snapshot.target_context.context_id):
            raise CoreError("EXECUTION_CONTEXT_CHANGED")
        return channel, source, context

    def observe_selected(self, snapshot: RouteSnapshot):
        """Read only the exact action-selected channel, including after UNKNOWN."""
        channel, source, context = self.channel_for(snapshot)
        result = self._observe(channel, source, context, snapshot.path)
        self.channel_for(snapshot)
        return result

    def _observe(self, channel, source, context, path):
        try:
            observation = channel.probe.observe(path)
        except (OSError, TimeoutError):
            raise CoreError("EXECUTION_DIAGNOSTIC_UNKNOWN") from None
        if (type(observation) is not PathObservation or observation.context.context_id != context.context_id
            or observation.context.target_id != context.target_id or observation.requested_path != path):
            raise CoreError("EXECUTION_DIAGNOSTIC_CONTEXT_MISMATCH")
        result = {"source_context": source.model_dump(mode="json"), "target_id": context.target_id,
                  "target_context_id": context.context_id, "requested_path": path,
                  "channel_id": channel.channel_id, "transport": channel.kind,
                  "observed_at_us": self.clock_us(), "observation": observation.model_dump(mode="json"),
                  "execution_authority": False, "host_path_equivalence": "UNKNOWN"}
        require_fresh(result, expected_target=context.target_id, expected_path=path,
                      max_age_us=5_000_000, now_us=self.clock_us())
        return result

    def diagnose(self, target_id, path):
        """Explicit metadata-only diagnostic; missing is scoped to this target."""
        _path_parts(path)
        channel, source, context = self._choose(self._target(target_id))
        result = self._observe(channel, source, context, path)
        self._capture(channel, self._target(target_id))
        return result
