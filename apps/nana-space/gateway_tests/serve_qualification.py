"""TEST ONLY: fresh real Core + loopback gateway, no provider, grants or user data."""

import json, os, signal, subprocess, sys, tempfile, time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REPO = APP.parents[1]
sys.path[:0] = [str(APP), str(REPO / "src")]
from gateway.dev_instance import initialize
from gateway.server import Bridge, Server
from nana_core.life.control import request


def main():
    with tempfile.TemporaryDirectory(prefix="nana-space-live-test-") as directory:
        home = Path(directory) / "life"
        identity = initialize(home)["identity_id"]
        process = None
        server = None
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(APP / "gateway/dev_instance.py"),
                    "run",
                    "--home",
                    str(home),
                    "--subject-id",
                    identity,
                    "--seconds",
                    "1800",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(120):
                try:
                    if request(
                        home, {"operation": "view", "view": "status"}, timeout=2
                    ).get("ok"):
                        break
                except Exception:
                    pass
                if process.poll() is not None:
                    raise RuntimeError("CORE_TEST_OWNER_EXITED")
                time.sleep(0.1)
            else:
                raise RuntimeError("CORE_TEST_OWNER_TIMEOUT")
            bridge = Bridge(
                home, identity, "qualification-only-access"
            )  # explicit public test fixture
            server = Server(4174, bridge, APP / "dist")
            target = APP / ".live-target.json"
            target.parent.mkdir(exist_ok=True)
            target.write_text(
                json.dumps({"subject_id": identity, "realm": "OWNED_DEVELOPMENT_ONLY"})
            )

            def stop(*args):
                raise KeyboardInterrupt()

            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            print("Live qualification ready on loopback port 4174", flush=True)
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            if server:
                server.server_close()
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
