"""Finite infrastructure entry. Default verify never initializes a Subject.

The system Python is used only to inspect/exec the explicitly fixed private
runtime. It must never become an alternate SQLite binding for the Core.
"""

import http.client
import json
import os
import subprocess
import sys
from pathlib import Path

RUNTIME = Path("/opt/nana-core/runtime")
DATA = Path("/opt/nana-core/data")


def verify():
    python = RUNTIME / "bin/python3"
    if not python.is_file():
        return {"state": "BLOCKED_RUNTIME_ARTIFACT_MISSING", "subject_opened": False}
    code = "import sys,ssl,hashlib,sqlite3,ctypes,json;print(json.dumps({'python':list(sys.version_info[:3]),'prefix':sys.prefix,'sqlite':sqlite3.sqlite_version,'openssl':ssl.OPENSSL_VERSION,'ca_count':len(ssl.create_default_context().get_ca_certs()),'sha256':hashlib.sha256(b'PUBLIC_RUNTIME_PROBE').hexdigest(),'native_modules':'IMPORTED','supported':sys.version_info[:3]==(3,12,14) and sqlite3.sqlite_version=='3.51.3' and sys.prefix=='/opt/nana-core/runtime' and len(ssl.create_default_context().get_ca_certs())>0}))"
    try:
        p = subprocess.run(
            [str(python), "-I", "-B", "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC"},
        )
        if p.returncode:
            return {
                "state": "BLOCKED_RUNTIME_DYNAMIC_LINK_OR_IMPORT",
                "exit_code": p.returncode,
                "subject_opened": False,
            }
        value = json.loads(p.stdout)
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return {"state": "BLOCKED_RUNTIME_PROBE_UNKNOWN", "subject_opened": False}
    return {
        "state": "PRIVATE_RUNTIME_COMPATIBLE" if value["supported"] else "BLOCKED_RUNTIME_VERSION",
        "runtime": value,
        "uid": os.geteuid(),
        "groups": os.getgroups(),
        "subject_opened": False,
        "code_skills": "BLOCKED_UNQUALIFIED_SANDBOX_NO_FALLBACK",
        "provider_calls": 0,
    }


def health():
    # Reachability/liveness only. Core readiness/identity/owner stays in the
    # authenticated original projection and is not inferred from HTTP401.
    config = DATA / "host/host.json"
    if not config.is_file():
        return {"state": "NOT_ACTIVATED", "core_readiness": "NOT_QUALIFIED"}
    try:
        import urllib.parse

        obj = json.loads(config.read_bytes())
        origin = urllib.parse.urlsplit(obj["public_origin"])
        conn = http.client.HTTPConnection("127.0.0.1", obj.get("port", 18765), timeout=2)
        conn.request("GET", "/api/nana-space/v2/bootstrap", headers={"Host": origin.netloc})
        response = conn.getresponse()
        response.read(4096)
        conn.close()
        return {
            "state": "BFF_AUTH_LIVE" if response.status == 401 else "BFF_LIVENESS_UNVERIFIED",
            "core_readiness": "CHECK_AUTHENTICATED_SUPERVISOR",
        }
    except (OSError, ValueError, KeyError):
        return {"state": "BFF_UNAVAILABLE", "core_readiness": "UNKNOWN"}


def main():
    operation = sys.argv[1:]
    if operation == ["health"]:
        value = health()
        print(json.dumps(value))
        return 0 if value["state"] == "BFF_AUTH_LIVE" else 2
    value = verify()
    if operation == ["verify"]:
        print(json.dumps(value))
        return 0 if value["state"] == "PRIVATE_RUNTIME_COMPATIBLE" else 2
    allowed = {("serve",), ("preflight",), ("serve", "--password-fd", "0"),
               ("serve", "--live-provider-authorized"),
               ("serve", "--password-fd", "0", "--live-provider-authorized"),
               ('serve','--platform-bindings-authorized'),
               ('serve','--password-fd','0','--platform-bindings-authorized'),
               ('serve','--live-provider-authorized','--platform-bindings-authorized'),
               ('serve','--password-fd','0','--live-provider-authorized','--platform-bindings-authorized')}
    password_stdin = "--password-fd" in operation
    if tuple(operation) not in allowed:
        print(json.dumps({"state": "OPERATION_DENIED"}))
        return 2
    if password_stdin and os.isatty(0):
        print(json.dumps({"state": "BLOCKED_PASSWORD_PIPE_REQUIRED"}))
        return 2
    if value["state"] != "PRIVATE_RUNTIME_COMPATIBLE" or os.geteuid() == 0:
        print(json.dumps({"state": "BLOCKED_PRIVATE_NONROOT_RUNTIME_REQUIRED"}))
        return 2
    # Public fixed release selector, baked into the image, never a credential.
    root = Path(os.environ.get("NANA_CORE_RELEASE", ""))
    if not root.is_absolute() or root.resolve() != root or not root.is_relative_to(RUNTIME / "core-releases"):
        print(json.dumps({"state": "BLOCKED_PINNED_RELEASE_REQUIRED"}))
        return 2
    config = DATA / "host/host.json"
    if not config.is_file():
        print(json.dumps({"state": "BLOCKED_EXPLICIT_HOST_BINDING_REQUIRED"}))
        return 2
    # Main BFF/Supervisor independently validates canonical receipts and binding.
    # No init, credential lookup, old writer shutdown, network change or QQ send.
    # Only infrastructure forwarding: one original BFF/Supervisor remains the
    # sole owner. Verify/health never start the relay or any child process.
    command = [str(root / ".venv/bin/python"), "-I", "-B", str(root / "host_gateway.py"), "--config", str(config)]
    if operation == ["preflight"]:
        command.append("--check-only")
        os.execv(command[0], command)  # No relay, authentication or lifecycle change.
    if password_stdin:
        # The original gateway alone reads its bounded password from stdin.
        # The infrastructure relay never reads or persists credential bytes.
        command.extend(["--password-fd", "0"])
    if "--live-provider-authorized" in operation:
        # Separate operator opt-in; credentials arrive later via the explicit
        # native/admin memory resolver. LifeConfig/route/budget remain binding.
        command.append("--live-provider-authorized")
    if '--platform-bindings-authorized' in operation:command.append('--platform-bindings-authorized')
    os.execv(sys.executable, [sys.executable, "-I", "-B", str(Path(__file__).with_name("loopback_relay.py")), *command])


if __name__ == "__main__":
    raise SystemExit(main())
