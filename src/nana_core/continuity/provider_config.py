"""Host-local configuration, separate from authoritative Subject state.

No secret values, Store, model discovery or environmental credential lookup.
"""

import fcntl, ipaddress, json, os, re, stat, tempfile
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlsplit, urlunsplit
from pydantic import Field, model_validator
from ..contracts import DTO, CoreError
from ..storage import canonical
from .providers import ProviderDescriptor, Modality, Operation
from .extensions import NAME_PATTERN

Privacy = Literal["PUBLIC", "PROJECT", "PERSONAL", "SECRET"]
ProtocolKind = Literal[
    "OPENAI_COMPATIBLE_CHAT",
    "LOCAL",
    "SYNTHETIC_LOOPBACK",
    "OPENAI_RESPONSES",
    "ANTHROPIC",
    "GEMINI_NATIVE",
    "QWEN_NATIVE",
    "CUSTOM",
]


def endpoint(base, locality, protocol):
    if protocol == "LOCAL":
        if base is not None or locality == "REMOTE":
            raise ValueError("local construction only")
        return None
    if type(base) != str or len(base) > 512 or any(x in base for x in ["\\", "%", "\n", "\r", "\t", " "]):
        raise ValueError("invalid endpoint")
    u = urlsplit(base)
    if u.username or u.password or u.query or u.fragment or not u.hostname:
        raise ValueError("invalid endpoint")
    port = u.port
    path = u.path.rstrip("/")
    if (
        "//" in path
        or any(x in {".", ".."} for x in path.split("/"))
        or not re.fullmatch(r"(?:/[A-Za-z0-9_-]+)*", path)
    ):
        raise ValueError("invalid base path")
    if path.endswith("/chat/completions"):
        raise ValueError("base URL required, not completion endpoint")
    if protocol == "SYNTHETIC_LOOPBACK":
        if locality != "LOCAL_FIXTURE" or u.scheme != "http" or u.hostname != "127.0.0.1" or port is None:
            raise ValueError("explicit loopback only")
    else:
        if locality != "REMOTE" or u.scheme != "https" or port not in {None, 443}:
            raise ValueError("remote HTTPS only")
        h = u.hostname
        try:
            ipaddress.ip_address(h)
        except ValueError:
            pass
        else:
            raise ValueError("remote literal IP denied")
        if (
            len(h) > 253
            or "." not in h
            or not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", x) for x in h.split("."))
            or h.lower().endswith((".localhost", ".local", ".internal"))
        ):
            raise ValueError("invalid remote host")
    return urlunsplit((u.scheme, u.netloc.lower(), path, "", ""))


class ConfigDTO(DTO):
    model_config = {"hide_input_in_errors": True}


class ProviderProfile(ConfigDTO):
    provider_profile_id: str = Field(pattern=NAME_PATTERN)
    display_name: str = Field(min_length=1, max_length=96)
    protocol: ProtocolKind
    chat_thinking_mode: Literal["PROVIDER_DEFAULT", "DISABLED"] = "PROVIDER_DEFAULT"
    base_url: str | None = None
    locality: Literal["LOCAL_FIXTURE", "LOCAL", "REMOTE"]
    secret_ref: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9._-]{0,95}$")
    enabled: bool = True
    permitted_privacy: tuple[Privacy, ...] = Field(default=("PUBLIC",), min_length=1, max_length=4)
    default_timeout_ms: int = Field(default=3000, ge=50, le=30000)
    default_cost_ceiling: int = Field(default=1000, ge=0, le=1000000)
    tags: tuple[str, ...] = Field(default=(), max_length=16)
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def valid(self):
        if self.locality == "REMOTE" and "SECRET" in self.permitted_privacy:
            raise ValueError("remote secret forbidden")
        if self.locality != "REMOTE" and self.secret_ref is not None:
            raise ValueError("local credential forbidden")
        if self.base_url != endpoint(self.base_url, self.locality, self.protocol):
            raise ValueError("noncanonical base URL")
        return self


class ModelProfile(ConfigDTO):
    model_profile_id: str = Field(pattern=NAME_PATTERN)
    provider_profile_id: str = Field(pattern=NAME_PATTERN)
    remote_model_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}$")
    model_version: str = Field(min_length=1, max_length=96)
    operations: tuple[Operation, ...] = Field(min_length=1, max_length=9)
    input_modalities: tuple[Modality, ...] = Field(min_length=1, max_length=5)
    output_modalities: tuple[Modality, ...] = Field(min_length=1, max_length=5)
    context_limit: int = Field(ge=256, le=2000000)
    output_limit: int = Field(ge=1, le=131072)
    tool_proposals: bool = False
    latency_class: Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"] = "UNKNOWN"
    cost_class: Literal["FIXTURE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"] = "UNKNOWN"
    enabled: bool = True
    tags: tuple[str, ...] = Field(default=(), max_length=16)
    revision: int = Field(default=1, ge=1)

    def descriptor(self, provider):
        return ProviderDescriptor(
            provider_id=provider.provider_profile_id,
            model_id=self.remote_model_id,
            model_profile_id=self.model_profile_id,
            model_version=self.model_version,
            operations=self.operations,
            input_modalities=self.input_modalities,
            output_modalities=self.output_modalities,
            context_limit=self.context_limit,
            output_limit=self.output_limit,
            tool_proposals=self.tool_proposals,
            locality=provider.locality,
            permitted_privacy=provider.permitted_privacy,
            latency_class=self.latency_class,
            cost_class=self.cost_class,
            tags=self.tags,
        )


class CapabilityRoute(ConfigDTO):
    operation: Operation
    primary_model_profile_id: str = Field(pattern=NAME_PATTERN)
    fallback_model_profile_ids: tuple[str, ...] = Field(default=(), max_length=8)
    enabled: bool = True
    timeout_ceiling_ms: int = Field(default=3000, ge=50, le=30000)
    cost_ceiling: int = Field(default=1000, ge=0, le=1000000)
    context_ceiling: int = Field(default=2000000, ge=256, le=2000000)
    output_ceiling: int = Field(default=131072, ge=1, le=131072)
    permitted_privacy: tuple[Privacy, ...] = Field(default=("PUBLIC",), min_length=1, max_length=4)
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def unique(self):
        ids = (self.primary_model_profile_id, *self.fallback_model_profile_ids)
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate route model")
        return self


class ProviderConfiguration(ConfigDTO):
    schema_version: Literal[1] = 1
    revision: int = Field(default=0, ge=0)
    providers: tuple[ProviderProfile, ...] = Field(default=(), max_length=64)
    models: tuple[ModelProfile, ...] = Field(default=(), max_length=256)
    routes: tuple[CapabilityRoute, ...] = Field(default=(), max_length=9)

    @model_validator(mode="after")
    def links(self):
        ps = {p.provider_profile_id for p in self.providers}
        ms = {m.model_profile_id for m in self.models}
        if (
            len(ps) != len(self.providers)
            or len(ms) != len(self.models)
            or len({r.operation for r in self.routes}) != len(self.routes)
        ):
            raise ValueError("duplicate profile/route")
        if any(m.provider_profile_id not in ps for m in self.models) or any(
            not {r.primary_model_profile_id, *r.fallback_model_profile_ids} <= ms for r in self.routes
        ):
            raise ValueError("dangling configuration")
        return self


class SecretResolver(Protocol):
    def available(self, secret_ref: str) -> bool: ...
    def resolve(self, secret_ref: str): ...


class ResolvedSecret:
    """Memory-only, non-DTO handle. No serialization or revealing str/repr."""

    __slots__ = ("__value",)

    def __init__(self, value):
        if type(value) != str or not value or "\n" in value or "\r" in value:
            raise CoreError("SECRET_UNAVAILABLE")
        self.__value = value

    def reveal_for_header(self):
        return self.__value

    def clear(self):
        self.__value = None

    def __repr__(self):
        return "<ResolvedSecret REDACTED>"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("SECRET_SERIALIZATION_DENIED")


class ProviderConfigurationAuthority:
    pass


class ProviderCommand(ConfigDTO):
    operation: Literal[
        "UPSERT_PROVIDER",
        "REMOVE_PROVIDER",
        "UPSERT_MODEL",
        "REMOVE_MODEL",
        "SET_CAPABILITY_ROUTE",
        "REMOVE_CAPABILITY_ROUTE",
        "ENABLE_PROVIDER",
        "DISABLE_PROVIDER",
    ]
    expected_revision: int = Field(ge=0)
    target_id: str | None = None
    provider: ProviderProfile | None = None
    model: ModelProfile | None = None
    route: CapabilityRoute | None = None

    @model_validator(mode="after")
    def shape(self):
        expected = {"UPSERT_PROVIDER": "provider", "UPSERT_MODEL": "model", "SET_CAPABILITY_ROUTE": "route"}.get(
            self.operation, "target_id"
        )
        if getattr(self, expected) is None or any(
            getattr(self, k) is not None for k in ["target_id", "provider", "model", "route"] if k != expected
        ):
            raise ValueError("command shape")
        return self


class ProviderConfigService:
    """A single host JSON document; flock+CAS+atomic replace, no Subject writes."""

    document_type = ProviderConfiguration

    def __init__(self, path, authority):
        if type(authority) is not ProviderConfigurationAuthority:
            raise CoreError("PROVIDER_CONFIG_AUTHORITY_REQUIRED")
        self._path = Path(path)
        self.__authority = authority
        self._path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        s = self._path.parent.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.geteuid() or s.st_mode & 0o077:
            raise CoreError("PROVIDER_CONFIG_PRIVATE_DIRECTORY_REQUIRED")

    def _file(self, path, flags, mode=0o600):
        fd = os.open(path, flags | os.O_NOFOLLOW, mode)
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.geteuid() or s.st_nlink != 1 or s.st_mode & 0o077:
            os.close(fd)
            raise CoreError("PROVIDER_CONFIG_FILE_UNSAFE")
        return fd

    def _load(self):
        try:
            fd = self._file(self._path, os.O_RDONLY)
            with os.fdopen(fd, "rb") as f:
                raw = f.read(262145)
            if len(raw) > 262144:
                raise ValueError()
            from .privacy import _json_object

            obj = json.loads(raw, object_pairs_hook=_json_object)
            return self.document_type.model_validate_json(canonical(obj))
        except FileNotFoundError:
            raise CoreError("PROVIDER_CONFIG_UNAVAILABLE") from None
        except CoreError:
            raise
        except (ValueError, TypeError, OSError):
            raise CoreError("PROVIDER_CONFIG_INVALID") from None

    def load(self):
        return self._load()

    def _atomic(self, config):
        raw = config.model_dump_json().encode()
        if len(raw) > 262144:
            raise CoreError("PROVIDER_CONFIG_BOUND")
        fd, name = tempfile.mkstemp(prefix=".provider-config-", dir=self._path.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            self._checkpoint("TEMP_FSYNCED")
            os.replace(name, self._path)
            self._checkpoint("REPLACED")
            d = os.open(self._path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(d)
            finally:
                os.close(d)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _checkpoint(self, stage):
        pass  # Fault injection seam, no runtime/env switch.

    def _lock(self):
        fd = self._file(str(self._path) + ".lock", os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    def initialize(self, authority):
        self._check(authority)
        fd = self._lock()
        try:
            if os.path.lexists(self._path):
                return self._load()
            c = self.document_type()
            self._atomic(c)
            return c
        finally:
            os.close(fd)

    def _check(self, authority):
        if authority is not self.__authority:
            raise CoreError("PROVIDER_CONFIG_AUTHORITY_REQUIRED")

    def update(self, command, authority):
        self._check(authority)
        if type(command) is not ProviderCommand:
            raise CoreError("PROVIDER_CONFIG_TYPED_COMMAND_REQUIRED")
        command = ProviderCommand.model_validate_json(command.model_dump_json())
        fd = self._lock()
        try:
            c = self._load()
            if c.revision != command.expected_revision:
                raise CoreError("PROVIDER_CONFIG_REVISION_CONFLICT")
            ps = {p.provider_profile_id: p for p in c.providers}
            ms = {m.model_profile_id: m for m in c.models}
            rs = {r.operation: r for r in c.routes}
            op = command.operation
            target = command.target_id
            if op.startswith("UPSERT_") or op == "SET_CAPABILITY_ROUTE":
                obj = command.provider or command.model or command.route
                table, key = (
                    (ps, obj.provider_profile_id)
                    if command.provider
                    else (ms, obj.model_profile_id)
                    if command.model
                    else (rs, obj.operation)
                )
                obj = obj.model_copy(update={"revision": table[key].revision + 1 if key in table else 1})
                table[key] = obj
            elif op == "REMOVE_PROVIDER":
                if any(m.provider_profile_id == target for m in ms.values()):
                    raise CoreError("PROVIDER_PROFILE_IN_USE")
                if target not in ps:
                    raise CoreError("PROVIDER_PROFILE_UNKNOWN")
                del ps[target]
            elif op == "REMOVE_MODEL":
                if any(target in (r.primary_model_profile_id, *r.fallback_model_profile_ids) for r in rs.values()):
                    raise CoreError("MODEL_PROFILE_IN_USE")
                if target not in ms:
                    raise CoreError("MODEL_PROFILE_UNKNOWN")
                del ms[target]
            elif op == "REMOVE_CAPABILITY_ROUTE":
                if target not in rs:
                    raise CoreError("CAPABILITY_ROUTE_UNKNOWN")
                del rs[target]
            else:
                if target not in ps:
                    raise CoreError("PROVIDER_PROFILE_UNKNOWN")
                ps[target] = ps[target].model_copy(
                    update={"enabled": op == "ENABLE_PROVIDER", "revision": ps[target].revision + 1}
                )
            try:
                updated = ProviderConfiguration(
                    revision=c.revision + 1,
                    providers=tuple(ps.values()),
                    models=tuple(ms.values()),
                    routes=tuple(rs.values()),
                )
            except ValueError:
                raise CoreError("PROVIDER_CONFIG_INVALID") from None
            self._atomic(updated)
            return updated
        finally:
            os.close(fd)
