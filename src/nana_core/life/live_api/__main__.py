"""Explicit host-bound BFF/Supervisor; never auto-init a canonical identity.

TLS is supplied by a separately approved private proxy. The service binds ONLY
loopback. Password/optional provider secret enter from explicitly inherited FDs,
never environment discovery, files, argument values or an APK.
"""

import argparse
import json
import os
import signal
import threading
from pathlib import Path
from pydantic import Field
from ...contracts import DTO, CoreError
from ..provider import ExplicitFDResolver
from ..secret_binding import MemorySecretResolver
from .auth import AuthService
from .bridge import GatewayService
from .contracts import Binding, Role, ApiError
from .server import ApiServer
from .supervisor import Supervisor, Release


class HostConfiguration(DTO):
    schema_version: int = Field(default=1, ge=1, le=1)
    home: str
    host_state: str
    binding: Binding
    releases: tuple[Release, ...] = Field(min_length=1, max_length=8)
    active_release: str
    public_origin: str
    web_root: str
    port: int = Field(default=18765, ge=1024, le=65535)
    roles: tuple[Role, ...] = (Role.READER, Role.CONVERSATION)
    activation: dict[str, str] | None = None
    allow_provider_configuration: bool = False


def read_private(path):
    p = Path(path).absolute()
    if p.resolve() != p or p.stat().st_uid != os.getuid() or p.stat().st_mode & 0o077 or p.stat().st_size > 65536:
        raise ApiError("PRIVATE_HOST_CONFIGURATION_REQUIRED")
    return HostConfiguration.model_validate_json(p.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--password-fd", type=int)
    p.add_argument("--live-provider-authorized", action="store_true")
    p.add_argument("--secret-fd", type=int)
    p.add_argument("--secret-ref")
    a = p.parse_args()
    resolver = MemorySecretResolver()
    supervisor = None
    server = None
    try:
        cfg = read_private(a.config)
        password = None
        if a.password_fd is not None:
            raw = os.read(a.password_fd, 513)
            os.close(a.password_fd)
            if len(raw) > 512:
                raise ApiError("PASSWORD_BOUND")
            password = raw.decode().rstrip("\r\n")
            del raw
        auth = AuthService(Path(cfg.host_state) / "auth.json", password=password, roles=cfg.roles)
        password = None
        binding = resolver.inherited_fd if a.live_provider_authorized else None
        if a.live_provider_authorized:
            if (a.secret_fd is None) != (a.secret_ref is None):
                raise ApiError("EXPLICIT_SECRET_RESOLVER_REQUIRED")
            if a.secret_fd is not None:
                initial = ExplicitFDResolver(a.secret_fd, a.secret_ref)
                try:
                    value = initial.resolve(a.secret_ref)
                    try:
                        resolver.bind(a.secret_ref, value.reveal_for_header())
                    finally:
                        value.clear()
                finally:
                    initial.clear()
                    os.close(a.secret_fd)
        elif a.secret_fd is not None or a.secret_ref is not None:
            raise ApiError("LIVE_PROVIDER_NOT_AUTHORIZED", 403)
        supervisor = Supervisor(
            cfg.home,
            cfg.host_state,
            cfg.binding,
            cfg.releases,
            active_release=cfg.active_release,
            activation=cfg.activation,
            provider_binding=binding,
        )
        service = GatewayService(supervisor, auth, cfg.host_state, allow_provider_configuration=cfg.allow_provider_configuration,
                                 credential_resolver=resolver)
        server = ApiServer(("127.0.0.1", cfg.port), service, public_origin=cfg.public_origin, web_root=cfg.web_root)
        stopping = threading.Event()

        def monitor():
            while not stopping.wait(5):
                try:
                    supervisor.monitor_once()
                except (ApiError, CoreError, OSError):
                    pass  # status exposes the existing state; no retry of requests

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

        def stop(*unused):
            stopping.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        print(
            json.dumps(
                {
                    "state": "BFF_READY",
                    "contract": "nana-space-live/v2",
                    "subject_id": cfg.binding.subject_id,
                    "realm": cfg.binding.realm,
                    "core": "EXISTING_HOME_ONLY",
                    "new_identity_created": False,
                }
            ),
            flush=True,
        )
        try:
            server.serve_forever(poll_interval=0.5)
        finally:
            stopping.set()
            thread.join(timeout=2)
    except (ApiError, CoreError, OSError, ValueError):
        print(json.dumps({"state": "BLOCKED", "code": "HOST_BINDING_OR_CONFIGURATION_UNAVAILABLE"}), flush=True)
        raise SystemExit(2) from None
    finally:
        if server:
            server.server_close()
        if supervisor:
            supervisor.close()
        if resolver:
            resolver.clear()


if __name__ == "__main__":
    main()
