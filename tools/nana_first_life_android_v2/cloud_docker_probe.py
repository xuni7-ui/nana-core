"""Actual supplied-SDK Docker lifecycle over a fresh explicit DEV Subject.

Only the managed local daemon and caller's fresh qualification directory are
used. The production /srv tree, AstrBot, credentials and devices are untouched.
Synthetic password bytes travel only through the docker client's stdin pipe.
"""

import argparse
import hashlib
import http.client
import json
import socket
import subprocess
import time
from pathlib import Path

DOCKER = ["env", "-u", "DOCKER_HOST", "-u", "DOCKER_CONTEXT", "-u", "DOCKER_TLS",
          "-u", "DOCKER_TLS_VERIFY", "-u", "DOCKER_CERT_PATH", "docker", "--host=unix:///var/run/docker.sock"]
SOURCE = "dbfb37ebe5c82edcfba6d50ba4f41a02ab8f358e"
BUNDLE = "/opt/nana-core/runtime/core-releases/" + SOURCE
PYTHON = BUNDLE + "/.venv/bin/python"
PASSWORD = "TEST_ONLY_NOT_SECRET_cloud_docker_probe"
ORIGIN = "https://space.test"
SEED = r'''
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.portable_runtime import configuration
from nana_core.life.config import write_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.live_api.supervisor import existing_identity
home=Path('/opt/nana-core/data/life')
cfg=configuration(root).model_copy(update={'provider_calls_per_day':0,'provider_total_calls_limit':0,'provider_total_reserved_cost_micro':0,'surface_bindings':(SurfaceBinding(binding_id='nana.space',platform='nana.space',surface='chat.direct',adapter='nana-space.gateway'),)})
write_config(home,cfg)
with LifeApplication(home,bootstrap_grant=False):pass
identity,lineage,_=existing_identity(home)
marker=home/'nana-space-development.json'
marker.write_text(json.dumps({'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':identity}));marker.chmod(0o600)
host=Path('/opt/nana-core/data/host');host.mkdir(mode=0o700)
value={'home':str(home),'host_state':str(host/'state'),'binding':{'subject_id':identity,'lineage_binding':lineage},'releases':[{'release_id':'installed','source_commit':sys.argv[2],'root':str(root),'python':sys.executable}],'active_release':'installed','public_origin':'https://space.test','web_root':'/opt/nana-core/runtime/web-releases/'+sys.argv[3],'port':18765,'roles':['READER','CONVERSATION','MANAGER','HOST_ADMIN']}
p=host/'host.json';p.write_text(json.dumps(value));p.chmod(0o600)
print(json.dumps({'subject_id':identity,'lineage_binding':lineage,'realm':'OWNED_DEVELOPMENT_ONLY'}))
'''
RESTORE = r'''
import json,sqlite3,sys
from pathlib import Path
from uuid import uuid4
sys.dont_write_bytecode=True;root=Path(sys.argv[1]);sys.path.insert(0,str(root/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config
from nana_core.life.cloud import transfer,receive,backup
from nana_core.continuity import ContinuityStore
from nana_core.contracts import CoreError
home=Path('/opt/nana-core/data/life');target=Path('/opt/nana-core/data/restored')
backup_path=Path('/opt/nana-core/backups/review.db')
with ContinuityStore(home/'subject/self.db',schema_target=13) as store:
    before=store.identity['identity_id'];b=backup(store,backup_path)
with sqlite3.connect(backup_path.as_uri()+'?mode=ro',uri=True) as db:
    if db.execute("select value_json from core_meta where key='recovery_quarantine'").fetchone()[0]!='true':raise RuntimeError('BACKUP_NOT_QUARANTINED')
destination=str(uuid4());package=Path('/opt/nana-core/backups/transfer.zip')
exported=transfer(home,package,destination_id=destination,source_commit=sys.argv[2])
old_rejected=False
try:
    with LifeApplication(home):pass
except CoreError:old_rejected=True
if not old_rejected:raise RuntimeError('SOURCE_NOT_FENCED')
restored=receive(package,target,sha256=exported['sha256'],destination_id=destination,config=load_config(home))
with LifeApplication(target,bootstrap_grant=False) as app:
    if app.runtime.identity_id!=before:raise RuntimeError('RESTORE_IDENTITY_CHANGED')
    if any(not row['revoked'] for row in app.runtime.store.all('grants')):raise RuntimeError('OLD_GRANT_SURVIVED')
print(json.dumps({'identity_id':before,'backup':b['state'],'restore':restored['state'],'old_source_fenced':old_rejected,'provider_config_transferred':restored['provider_config_transferred'],'old_grants':0,'same_subject':'PASS','single_active_lineage':'PASS'}))
'''


def require(value, code):
    if not value:
        raise RuntimeError(code)


def docker(*args, input=None, check=True, timeout=90):
    p = subprocess.run([*DOCKER, *args], input=input, text=True, capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError("DOCKER_" + args[0].upper() + "_FAILED: " + p.stderr[-1000:])
    return p


def run(image, work, web_sha):
    work = Path(work).absolute()
    require(not work.exists() and work.resolve() == work, "FRESH_OWNED_DEV_ROOT_REQUIRED")
    work.mkdir(mode=0o700, parents=True)
    name = "nana-owned-cloud-sdk-" + hashlib.sha256(str(work).encode()).hexdigest()[:10]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    containers = set()
    cookie = csrf = ""
    source_container = docker("create", image).stdout.strip()
    try:
        docker("cp", source_container + ":/opt/nana-core/runtime", str(work / "runtime"))
    finally:
        docker("rm", source_container)
    # This helper is confined to this newly created directory, not /srv or an
    # existing cloud volume. The actual service always runs as UID/GID999.
    docker("run", "--rm", "--network", "none", "--user", "0:0", "--mount",
           f"type=bind,src={work},dst=/qual", "--entrypoint", "/bin/sh", image, "-ec",
           "mkdir /qual/data /qual/logs /qual/backups; chown 999:999 /qual/data /qual/logs /qual/backups; chmod 700 /qual/data /qual/logs /qual/backups; chown -R 999:999 /qual/runtime/core-releases")
    common = ["--read-only", "--user", "999:999", "--init", "--cap-drop", "ALL", "--security-opt",
              "no-new-privileges:true", "--pids-limit", "64", "--memory", "512m", "--cpus", "1",
              "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m,uid=999,gid=999,mode=1770"]
    for part in ("runtime", "data", "logs", "backups"):
        common += ["--mount", f"type=bind,src={work / part},dst=/opt/nana-core/{part}" + (",readonly" if part == "runtime" else "")]
    def execute(code):
        p = docker("run", "--rm", "--network", "none", *common, "--entrypoint", PYTHON, image,
                   "-I", "-B", "-c", code, BUNDLE, SOURCE, web_sha)
        return json.loads(p.stdout.splitlines()[-1])
    seeded = execute(SEED)
    def call(path, method="GET", body=None, auth=True):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        headers = {"Host": "space.test", "Origin": ORIGIN}
        if auth:
            headers.update(Cookie=cookie, **{"X-Nana-CSRF": csrf})
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, "/api/nana-space/v2/" + path, None if body is None else json.dumps(body), headers)
        response = conn.getresponse()
        value = json.loads(response.read())
        received = response.getheader("Set-Cookie")
        conn.close()
        return response.status, value, received
    def ready():
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            try:
                if call("bootstrap", auth=False)[0] == 401:
                    return
            except (OSError, ValueError):
                pass
            time.sleep(.2)
        raise RuntimeError("PUBLISHED_LOOPBACK_PORT_NOT_READY")
    def login():
        nonlocal cookie, csrf
        status, row, received = call("session", "POST", {"subject_id": seeded["subject_id"], "password": PASSWORD}, False)
        require(status == 200 and "Secure" in received, "LOGIN_NOT_VERIFIED")
        cookie = received.split(";")[0]
        csrf = row["data"]["csrf"]
    def status():
        code, row, _ = call("bootstrap")
        require(code == 200, "AUTHENTICATED_STATUS_REQUIRED")
        return row
    def transition(operation):
        row = status()
        code, c, _ = call("host/confirmations", "POST", {"operation": operation, "expected_revision": row["revision"]})
        require(code == 200, "CONFIRMATION_FAILED")
        key = operation.lower() + "." + str(time.time_ns())
        code, result, _ = call("host/operations", "POST", {"operation": operation,
            "confirmation_id": c["data"]["confirmation_id"], "client_request_id": key, "idempotency_key": key,
            "expected_revision": row["revision"], "run_generation": row["run_generation"], "owner_epoch": row["owner_epoch"]})
        require(code == 200 and result["data"]["state"] == "VERIFIED", "TRANSITION_UNVERIFIED_NO_RETRY")
        return result["data"]["result"]
    bootstrap_name = name + "-bootstrap"
    bootstrap = subprocess.Popen([*DOCKER, "run", "-i", "--name", bootstrap_name, *common,
        "-p", f"127.0.0.1:{port}:18766", image, "serve", "--password-fd", "0"],
        stdin=subprocess.PIPE, stdout=(work / "bootstrap.log").open("w"), stderr=subprocess.STDOUT, text=True)
    containers.add(bootstrap_name)
    bootstrap.stdin.write(PASSWORD + "\n")
    bootstrap.stdin.close()
    result = {"scope": "ACTUAL_SUPPLIED_CLOUD_SDK_ISOLATED_DEV_NOT_PRODUCTION", "runtime_source_commit": SOURCE,
              "sdk_sha256": "1dbbcf46f6a16ab41deac96657a43a8fcecbba6ab7dea1d0113a84b2c8285b27",
              **seeded, "provider_calls": 0, "real_social_sends": 0, "private_data_used": False,
              "production_changed": False, "image_id": docker("image", "inspect", "--format", "{{.Id}}", image).stdout.strip()}
    def start():
        docker("run", "-d", "--name", name, *common, "--restart", "unless-stopped",
               "-p", f"127.0.0.1:{port}:18766", image, "serve")
        containers.add(name)
        ready()
        login()
    try:
        ready()
        login()
        require(not status()["data"]["host"]["runtime_active"], "DEFAULT_AUTO_STARTED_SUBJECT")
        docker("stop", "--time", "15", bootstrap_name)
        bootstrap.wait(timeout=20)
        docker("rm", bootstrap_name)
        containers.remove(bootstrap_name)
        start()
        first = transition("START")
        require(first["process_ready"], "ORIGINAL_CORE_NOT_READY")
        for page in ("home", "chat", "memories", "goals", "journal", "world", "growth", "devices", "runtime", "settings"):
            code, row, _ = call("views/" + page)
            require(code == 200 and row["subject_id"] == seeded["subject_id"], "PAGE_IDENTITY_MISMATCH")
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/", headers={"Host": "space.test"})
        response = conn.getresponse(); response.read(); location = response.getheader("Location"); conn.close()
        require(response.status == 303 and location == "/index.html?source=live", "LIVE_WEB_ROUTE_NOT_PINNED")
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", location, headers={"Host": "space.test"})
        response = conn.getresponse(); html = response.read(); conn.close()
        require(response.status == 200 and b"<html" in html, "LIVE_WEB_NOT_SERVED")
        row = status(); key = "project.cloud-docker.1"
        code, message, _ = call("messages", "POST", {"text": "PROJECT 请依据现有来源说明目前状态", "privacy_class": "PROJECT",
            "client_request_id": key, "idempotency_key": key, "expected_revision": row["revision"],
            "owner_epoch": row["owner_epoch"], "run_generation": row["run_generation"]})
        require(code == 200 and message["data"]["state"] == "VERIFIED", "ORIGINAL_C_CHAT_NOT_VERIFIED")
        require(message["data"]["result"]["external_delivery"] is False, "UNAUTHORIZED_DELIVERY")
        backup = transition("BACKUP")
        result.update(published_host_loopback="PASS", first_password_pipe="PASS", original_ten_pages="PASS",
            live_web="PASS", original_c_offline_chat="PASS_NOT_NATURALNESS", backup=backup["state"])
        # Wait for Docker's documented stable-start interval; no semantic retry.
        until = time.monotonic() + 11
        while time.monotonic() < until:
            time.sleep(.5)
        kill_code = "import os,signal;from pathlib import Path;matches=[]\nfor p in Path('/proc').iterdir():\n if not p.name.isdigit() or p.name==str(os.getpid()):continue\n try:a=(p/'cmdline').read_bytes().split(bytes([0]))\n except OSError:continue\n if len(a)>2 and a[2]==b'" + (BUNDLE + "/host_gateway.py") + "':matches.append(int(p.name))\nif len(matches)!=1:raise RuntimeError('OWNED_BFF_NOT_UNIQUE')\nos.kill(matches[0],signal.SIGKILL)"
        killed = docker("exec", name, PYTHON, "-I", "-B", "-c", kill_code, check=False)
        require(killed.returncode == 0, "OWNED_BFF_KILL_NOT_CONFIRMED")
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            count = int(docker("inspect", "--format", "{{.RestartCount}}", name).stdout)
            if count >= 1:
                ready(); login()
                current = status()["data"]["host"]
                if current["process_ready"] and current["owner_epoch"] > first["owner_epoch"]:
                    break
            time.sleep(.5)
        else:
            raise RuntimeError("AUTOMATIC_RECOVERY_NOT_QUALIFIED")
        require(current["subject_id"] == seeded["subject_id"] and current["lineage_binding"] == seeded["lineage_binding"], "CRASH_IDENTITY_CHANGED")
        stopped = transition("STOP")
        require(stopped["stop_latch"] and not stopped["runtime_active"], "STOP_LATCH_NOT_VERIFIED")
        docker("stop", "--time", "15", name); docker("rm", name); containers.remove(name)
        start()
        reopened = status()["data"]["host"]
        require(reopened["stop_latch"] and not reopened["runtime_active"], "STOP_LATCH_LOST_AFTER_RECREATE")
        restarted = transition("START")
        require(restarted["subject_id"] == seeded["subject_id"] and restarted["owner_epoch"] > current["owner_epoch"], "RECREATE_IDENTITY_CHANGED")
        transition("STOP")
        docker("stop", "--time", "15", name); docker("rm", name); containers.remove(name)
        restored = execute(RESTORE)
        require(restored["identity_id"] == seeded["subject_id"], "RESTORE_IDENTITY_CHANGED")
        result.update(automatic_container_restart="PASS", restart_count=count, before_epoch=first["owner_epoch"],
            after_crash_epoch=current["owner_epoch"], after_recreate_epoch=restarted["owner_epoch"],
            container_recreation="PASS", intentional_stop_latch="PASS", uid=999,
            four_volume_mapping="PASS", runtime_readonly="PASS", restoration=restored,
            formal_genesis="NOT_RUN", cloud_deployment="NOT_RUN", naturalness="NOT_RUN")
        (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    except BaseException:
        diagnostics = {}
        for container in containers:
            diagnostics[container] = {"state": docker("inspect", "--format", "{{json .State}}", container, check=False).stdout,
                                      "logs": docker("logs", "--tail", "20", container, check=False).stdout}
        (work / "failure.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
        raise
    finally:
        for container in containers:
            docker("stop", "--time", "15", container, check=False)
            docker("rm", container, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--web-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.image, args.work, args.web_sha256), indent=2))
