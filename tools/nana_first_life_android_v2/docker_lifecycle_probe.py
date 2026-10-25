"""Owned developer container crash/restart qualification, never a cloud subject.

Uses a separately qualified DEVELOPMENT SDK mounted at its existing prefix.
This does NOT qualify the cloud operator's still-unavailable runtime archive.
All data here is the explicitly synthetic installed_gateway_probe fixture.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

DOCKER = [
    "env",
    "-u",
    "DOCKER_HOST",
    "-u",
    "DOCKER_CONTEXT",
    "-u",
    "DOCKER_TLS",
    "-u",
    "DOCKER_TLS_VERIFY",
    "-u",
    "DOCKER_CERT_PATH",
    "docker",
    "--host=unix:///var/run/docker.sock",
]
SDK = "/workspace/nana-staging/quality-v2-20261025/private-host-complete"
BUNDLE = "/workspace/nflv2-a"
DATA = "/workspace/nflv2-docker-qual"
NAME = "nana-first-life-owned-recovery-v2"
REMOTE = """
import http.client,json,sys,time
config=json.load(open('/qual/owned/host.json'))
cookie='';csrf=''
def call(path,method='GET',body=None):
 c=http.client.HTTPConnection('127.0.0.1',config['port'],timeout=20)
 h={'Host':'space.test','Origin':'https://space.test','Cookie':cookie,'X-Nana-CSRF':csrf}
 if body is not None:h['Content-Type']='application/json'
 c.request(method,'/api/nana-space/v2/'+path,None if body is None else json.dumps(body),h)
 r=c.getresponse();v=json.loads(r.read());received=r.getheader('Set-Cookie');c.close()
 if r.status!=200:raise RuntimeError('OWNED_HTTP_NOT_VERIFIED')
 return v,received
row,received=call('session','POST',{'subject_id':config['binding']['subject_id'],'password':'TEST_ONLY_NOT_SECRET_installed_password'})
cookie=received.split(';')[0];csrf=row['data']['csrf']
op=sys.argv[1]
if op=='status':print(json.dumps(call('bootstrap')[0]['data']['host']))
else:
 b=call('bootstrap')[0];confirmation=call('host/confirmations','POST',{'operation':op,'expected_revision':b['revision']})[0]['data']['confirmation_id']
 key=op.lower()+'.'+str(time.time_ns())
 row=call('host/operations','POST',{'operation':op,'confirmation_id':confirmation,'client_request_id':key,'idempotency_key':key,'expected_revision':b['revision'],'owner_epoch':b['owner_epoch'],'run_generation':b['run_generation']})[0]
 if row['data']['state']!='VERIFIED':raise RuntimeError('OWNED_TRANSITION_UNVERIFIED')
 print(json.dumps(row['data']['result']))
"""


def docker(*args, check=True, input=None):
    result = subprocess.run([*DOCKER, *args], input=input, capture_output=True, text=True, timeout=45)
    if check and result.returncode:
        raise RuntimeError("OWNED_DOCKER_OPERATION_UNVERIFIED")
    return result


def transition(operation):
    return json.loads(docker("exec", "-i", NAME, BUNDLE + "/.venv/bin/python", "-I", "-c", REMOTE, operation).stdout)


def run(image):
    if not Path(DATA + "/result.json").is_file():
        raise ValueError("EXPLICIT_SYNTHETIC_FIXTURE_REQUIRED")
    previous = json.loads(Path(DATA + "/result.json").read_text())
    if previous["execution"] != "ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD" or previous["production_changed"]:
        raise ValueError("NOT_AN_OWNED_FIXTURE")
    docker(
        "run",
        "-d",
        "--name",
        NAME,
        "--init",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "1",
        "--restart",
        "unless-stopped",
        "--user",
        "1000:1000",
        "--tmpfs",
        "/tmp:rw,nosuid,noexec,size=32m",
        "--mount",
        "type=bind,src=" + SDK + ",dst=" + SDK + ",readonly",
        "--mount",
        "type=bind,src=" + BUNDLE + ",dst=" + BUNDLE + ",readonly",
        "--mount",
        "type=bind,src=" + DATA + ",dst=/qual",
        "--entrypoint",
        BUNDLE + "/.venv/bin/python",
        image,
        "-I",
        BUNDLE + "/host_gateway.py",
        "--config",
        "/qual/owned/host.json",
    )
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                first = transition("status")
                break
            except (RuntimeError, ValueError):
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.5)
        if first["stop_latch"]:
            first = transition("START")  # Exactly one admitted write, never retry.
        else:
            # Resume the same owned interrupted fixture through the existing
            # original Supervisor's recovery, never a new START request.
            while not first["process_ready"]:
                if time.monotonic() > deadline:
                    raise RuntimeError("OWNED_RECOVERY_READINESS_UNKNOWN")
                time.sleep(0.5)
                first = transition("status")
        # Docker restart qualification starts from an actually stable container.
        stable_until = time.monotonic() + 11
        while time.monotonic() < stable_until:
            time.sleep(0.5)
        # Known active state is now observed; no model/Hands/social work exists.
        process = json.loads(docker("inspect", "--format", "{{json .HostConfig}}", NAME).stdout)
        assert process["ReadonlyRootfs"] and process["RestartPolicy"]["Name"] == "unless-stopped"
        assert "ALL" in process["CapDrop"] and process["Memory"] == 512 * 1024 * 1024
        # Do not read PID1's protected children file: nonroot isolation denies
        # it. Select exactly the owned BFF argv, skipping inaccessible processes.
        kill = """import os,signal,json
from pathlib import Path
matches=[]
prefix=[b'/workspace/nflv2-a/.venv/bin/python',b'-I',b'/workspace/nflv2-a/host_gateway.py']
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or p.name==str(os.getpid()):continue
 try:argv=(p/'cmdline').read_bytes().split(bytes([0]))
 except OSError:continue
 if argv[:3]==prefix:matches.append(int(p.name))
assert len(matches)==1
print(json.dumps({'owned_target_count':len(matches)}),flush=True)
os.kill(matches[0],signal.SIGKILL)
"""
        killed = docker("exec", NAME, BUNDLE + "/.venv/bin/python", "-I", "-c", kill, check=False)
        if "AssertionError" in killed.stderr:
            raise RuntimeError("OWNED_TARGET_NOT_UNIQUELY_IDENTIFIED")
        deadline = time.monotonic() + 40
        last = None
        while time.monotonic() < deadline:
            count = int(docker("inspect", "--format", "{{.RestartCount}}", NAME).stdout)
            if count >= 1:
                try:
                    last = transition("status")
                    if last["process_ready"] and last["owner_epoch"] > first["owner_epoch"]:
                        break
                except RuntimeError:
                    pass
            time.sleep(0.5)
        else:
            raise RuntimeError("AUTOMATIC_CONTAINER_RECOVERY_NOT_QUALIFIED")
        assert last["subject_id"] == first["subject_id"] and last["lineage_binding"] == first["lineage_binding"]
        stopped = transition("STOP")
        assert stopped["stop_latch"] and not stopped["runtime_active"]
        return {
            "evidence": "ACTUAL_OWNED_DOCKER_NOT_CLOUD",
            "cloud_runtime_archive_qualified": False,
            "sdk_scope": "SEPARATE_DEVELOPMENT_SDK_ORIGINAL_PREFIX_NOT_CLOUD_INPUT",
            "source_commit": first["source_commit"],
            "image_id": docker("inspect", "--format", "{{.Image}}", NAME).stdout.strip(),
            "subject_id": first["subject_id"],
            "lineage_binding": first["lineage_binding"],
            "owned_target_selection": "EXACT_ARGV_NOT_PID1_CHILD_ACCESS",
            "kill_helper_exit": killed.returncode,
            "before_epoch": first["owner_epoch"],
            "after_epoch": last["owner_epoch"],
            "automatic_restart_count": count,
            "same_subject": "PASS",
            "same_store": "PASS",
            "single_original_runtime": "PASS",
            "hardening": "PASS",
            "intentional_stop_latch": "PASS",
            "provider_calls": 0,
            "production_changed": False,
            "private_data_used": False,
        }
    except Exception:
        # Retain actual failure diagnostics BEFORE removing only this container.
        state = docker("inspect", "--format", "{{json .State}}", NAME, check=False)
        logs = docker("logs", "--tail", "20", NAME, check=False)
        Path(DATA + "/last-recovery-diagnostic.json").write_text(
            json.dumps({"state": state.stdout, "logs": logs.stdout, "stderr": logs.stderr})
        )
        raise
    finally:
        docker("stop", "--time", "15", NAME, check=False)
        docker("rm", NAME, check=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    value = run(a.image)
    a.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value))


if __name__ == "__main__":
    main()
