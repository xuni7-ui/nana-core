"""Actual Core + TLS v2/Web qualification only. Explicit fresh DEV identity.

This is a separate development harness, not the production startup command.
A self-signed loopback certificate is acceptable ONLY for browser tests that
explicitly mark ignoreHTTPSErrors. Never install its trust into an APK or host.
"""

import argparse
import importlib.util
import json
import signal
import ssl
import subprocess
import sys
import threading
from pathlib import Path
from nana_core.life.live_api.auth import AuthService
from nana_core.life.live_api.bridge import GatewayService
from nana_core.life.live_api.contracts import Binding, Role
from nana_core.life.live_api.server import ApiServer
from nana_core.life.live_api.supervisor import Supervisor, Release, existing_identity

ROOT = Path(__file__).resolve().parents[2]
PW = "TEST_ONLY_NOT_SECRET_web_password"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18445)
    parser.add_argument("--allow-provider-configuration", action="store_true", help="Explicit synthetic development-only config test opt-in")
    a = parser.parse_args()
    work = a.work.absolute()
    if work.exists():
        raise ValueError("FRESH_DEVELOPMENT_DIRECTORY_REQUIRED")
    work.mkdir(mode=0o700, parents=True)
    spec = importlib.util.spec_from_file_location("owned_development", ROOT / "apps/nana-space/gateway/dev_instance.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = work / "home"
    module.initialize(home)
    identity, lineage, _ = existing_identity(home)
    binding = Binding(subject_id=identity, lineage_binding=lineage)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    release = Release(release_id="owned-dev", source_commit=source, root=str(ROOT), python=sys.executable)
    supervisor = Supervisor(home, work / "host", binding, [release], active_release="owned-dev")
    supervisor.start()
    auth = AuthService(work / "auth.json", password=PW, roles=tuple(Role))
    service = GatewayService(supervisor, auth, work / "host", allow_provider_configuration=a.allow_provider_configuration)
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-keyout",
            str(work / "tls.key"),
            "-out",
            str(work / "tls.crt"),
            "-subj",
            "/CN=127.0.0.1",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (work / "tls.key").chmod(0o600)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(work / "tls.crt", work / "tls.key")
    server = ApiServer(
        ("127.0.0.1", a.port),
        service,
        public_origin=f"https://127.0.0.1:{a.port}",
        web_root=ROOT / "apps/nana-space/dist",
        tls_context=tls,
    )
    (work / "target.json").write_text(
        json.dumps(
            {
                "subject_id": identity,
                "lineage_binding": lineage,
                "origin": f"https://127.0.0.1:{a.port}",
                "realm": "OWNED_DEVELOPMENT_ONLY",
            }
        )
    )

    def stop(*args):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(
        json.dumps({"state": "OWNED_DEVELOPMENT_READY", "subject_id": identity, "paid_provider_calls": 0}), flush=True
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        supervisor.stop()
        supervisor.close()


if __name__ == "__main__":
    main()
