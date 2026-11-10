"""Actual isolated installed-bundle BFF→original Core qualification.

Fresh short DEV home, no production/private source/provider/network payment.
Run using the installed bundle's Python -I, passing that exact bundle explicitly.
The source repository is not on PYTHONPATH and no demo/qualification module is
needed from inside the Runtime archive.
"""

import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def run(bundle, work, *, check_memory_notes=False):
    bundle = Path(bundle).resolve()
    work = Path(work).absolute()
    if work.exists():
        raise ValueError("FRESH_OWNED_PROBE_REQUIRED")
    work.mkdir(mode=0o700)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(bundle / "src"))
    from nana_core.life.application import LifeApplication
    from nana_core.life.config import LifeConfig, write_config
    from nana_core.life.surfaces import SurfaceBinding
    from nana_core.continuity.project_work.service import material_for
    from nana_core.life.live_api.supervisor import existing_identity

    home = work / "life"
    paths = (
        "src/nana_core/continuity/recurrence.py",
        "src/nana_core/continuity/identity.py",
        "src/nana_core/continuity/autonomy/requests.py",
        "src/nana_core/continuity/subject/social.py",
    )
    materials = [material_for(bundle, p) for p in paths]
    cfg = LifeConfig(
        project_root=str(bundle),
        materials=(materials[0],),
        practice=materials[1],
        heldout=materials[2],
        transfer=materials[3],
        max_autonomous_materials=0,
        provider_calls_per_day=0,
        provider_total_calls_limit=0,
        provider_total_reserved_cost_micro=0,
        surface_bindings=(
            SurfaceBinding(
                binding_id="nana.space", platform="nana.space", surface="chat.direct", adapter="nana-space.gateway"
            ),
        ),
    )
    write_config(home, cfg)
    with LifeApplication(home, bootstrap_grant=False):
        pass
    identity, lineage, _ = existing_identity(home)
    (home / "nana-space-development.json").write_text(
        json.dumps({"realm": "OWNED_DEVELOPMENT_ONLY", "identity_id": identity})
    )
    (home / "nana-space-development.json").chmod(0o600)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    source = json.loads((bundle / "runtime.json").read_text())["source_commit"]
    host = work / "host.json"
    host.write_text(
        json.dumps(
            {
                "home": str(home),
                "host_state": str(work / "host"),
                "binding": {"subject_id": identity, "lineage_binding": lineage},
                "releases": [
                    {"release_id": "installed", "source_commit": source, "root": str(bundle), "python": sys.executable}
                ],
                "active_release": "installed",
                "public_origin": "https://space.test",
                "web_root": str(work / "no-web-build"),
                "port": port,
                "roles": ["READER", "CONVERSATION", "MANAGER", "HOST_ADMIN"],
            }
        )
    )
    host.chmod(0o600)
    read, write = os.pipe()
    os.write(write, b"TEST_ONLY_NOT_SECRET_installed_password")
    os.close(write)
    log = (work / "bff.log").open("wb")
    process = subprocess.Popen(
        [sys.executable, "-I", str(bundle / "host_gateway.py"), "--config", str(host), "--password-fd", str(read)],
        pass_fds=(read,),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        cwd=work,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC"},
    )
    os.close(read)
    cookie = ""
    csrf = ""

    def call(route, method="GET", body=None, authenticated=True):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        headers = {"Host": "space.test", "Origin": "https://space.test"}
        if authenticated:
            headers.update({"Cookie": cookie, "X-Nana-CSRF": csrf})
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, "/api/nana-space/v2/" + route, None if body is None else json.dumps(body), headers)
        response = conn.getresponse()
        data = json.loads(response.read())
        received = response.getheader("Set-Cookie")
        conn.close()
        return response.status, data, received

    def hostop(operation):
        status, b, _ = call("bootstrap")
        assert status == 200
        status, c, _ = call("host/confirmations", "POST", {"operation": operation, "expected_revision": b["revision"]})
        assert status == 200
        key = operation.lower() + "." + str(time.time_ns())
        status, row, _ = call(
            "host/operations",
            "POST",
            {
                "operation": operation,
                "confirmation_id": c["data"]["confirmation_id"],
                "client_request_id": key,
                "idempotency_key": key,
                "expected_revision": b["revision"],
                "run_generation": b["run_generation"],
                "owner_epoch": b["owner_epoch"],
            },
        )
        assert status == 200 and row["data"]["state"] == "VERIFIED", row
        return row["data"]["result"]

    result = {
        "execution": "ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD",
        "source_commit": source,
        "python": sys.version.split()[0],
        "subject_id": identity,
        "lineage_binding": lineage,
        "real_provider_calls": 0,
        "production_changed": False,
        "private_data_used": False,
        "real_social_sends": 0,
    }
    try:
        deadline = time.monotonic() + 10
        while True:
            if process.poll() is not None:
                raise RuntimeError("INSTALLED_BFF_START_EXITED")
            try:
                if call("bootstrap", authenticated=False)[0] == 401:
                    break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("INSTALLED_BFF_START_TIMEOUT")
            time.sleep(0.1)
        status, login, received = call(
            "session", "POST", {"subject_id": identity, "password": "TEST_ONLY_NOT_SECRET_installed_password"}, False
        )
        assert status == 200 and "HttpOnly; Secure; SameSite=Strict" in received
        cookie = received.split(";")[0]
        csrf = login["data"]["csrf"]
        first = hostop("START")
        assert first["process_ready"]
        for page in [
            "home",
            "chat",
            "memories",
            "goals",
            "journal",
            "world",
            "growth",
            "devices",
            "runtime",
            "settings",
        ]:
            status, row, _ = call("views/" + page)
            assert status == 200 and row["subject_id"] == identity
        status, b, _ = call("bootstrap")
        key = "installed.project.1"
        status, row, _ = call(
            "messages",
            "POST",
            {
                "text": "PROJECT 请按现有来源说明当前状态",
                "retain_shared_life": True,
                "privacy_class": "PROJECT",
                "client_request_id": key,
                "idempotency_key": key,
                "expected_revision": b["revision"],
                "owner_epoch": b["owner_epoch"],
                "run_generation": b["run_generation"],
            },
        )
        assert (
            status == 200 and row["data"]["state"] == "VERIFIED" and row["data"]["result"]["external_delivery"] is False
        )
        result["chat"] = "ORIGINAL_CORE_VERIFIED_OFFLINE_NOT_NATURALNESS_QUALIFICATION"
        turn=row['data']['result']
        _,current,_=call('bootstrap')
        if not current['capabilities'].get('conversation_feedback'):raise RuntimeError('FEEDBACK_CAPABILITY_MISSING')
        feedback={'client_request_id':'installed.feedback','idempotency_key':'installed.feedback',
            'expected_revision':current['revision'],'owner_epoch':current['owner_epoch'],'run_generation':current['run_generation'],
            'consent':True,'exchange_record_id':turn['exchange_record_id'],
            'sample':{'sample_id':'installed-review','review_target':turn['exchange_record_id'],'mode':'CASUAL',
                'context':'SYNTHETIC retained installed dialogue','candidate_response':turn['text'],
                'human_judgment':'PARTIAL','provenance':'USER_PROVIDED_REVIEW','observed_at_us':time.time_ns()//1000}}
        code,ack,_=call('conversation/feedback','POST',feedback)
        if code!=200 or ack['data']['state']!='VERIFIED':raise RuntimeError('INSTALLED_FEEDBACK_FAILED')
        code,repeated,_=call('conversation/feedback','POST',feedback)
        if code!=200 or repeated['data']['result']!=ack['data']['result']:raise RuntimeError('INSTALLED_FEEDBACK_REPLAY_FAILED')
        if ack['data']['result'].get('delivery_proven') is not False:raise RuntimeError('FALSE_DELIVERY_PROOF')
        result['feedback']='PASS_ORIGINAL_OWNER_AND_STORE_NOT_REAL_USER_REVIEW'
        result['sqlite']=__import__('sqlite3').sqlite_version

        def note_write(key, text, target=None):
            _, current, _ = call('bootstrap')
            request={"client_request_id":key,"idempotency_key":key,
                "expected_revision":current['revision'],"owner_epoch":current['owner_epoch'],
                "run_generation":current['run_generation'],"text":text,
                "privacy_class":"PROJECT","consent":True}
            if target:request['target_id']=target
            code, receipt, _=call('memories/notes','POST',request)
            if code!=200 or receipt['data']['state']!='VERIFIED':raise RuntimeError('INSTALLED_NOTE_WRITE_UNVERIFIED')
            return receipt['data']['result']['memory_id']
        if check_memory_notes:
            initial_note=note_write('installed.note.1','SYNTHETIC installed-note project Wednesday')
            current_note=note_write('installed.note.2','SYNTHETIC installed-note project Friday',initial_note)
        result["backup"] = hostop("BACKUP")["state"]
        second = hostop("RESTART")
        assert second["subject_id"] == identity and second["owner_epoch"] > first["owner_epoch"]
        if check_memory_notes:
            code, notes, _=call('memories/search','POST',{'query':'SYNTHETIC installed-note'})
            if code!=200 or [m['memory_id'] for m in notes['data']['memories']]!=[current_note]:raise RuntimeError('INSTALLED_NOTE_RESTART_RECALL_FAILED')
            _, current, _=call('bootstrap')
            code, removed, _=call('commands','POST',{'operation':'WITHDRAW','target_id':current_note,
                'client_request_id':'installed.note.withdraw','idempotency_key':'installed.note.withdraw',
                'expected_revision':current['revision'],'owner_epoch':current['owner_epoch'],'run_generation':current['run_generation']})
            if code!=200 or removed['data']['state']!='VERIFIED':raise RuntimeError('INSTALLED_NOTE_WITHDRAWAL_FAILED')
            code, notes, _=call('memories/search','POST',{'query':'SYNTHETIC installed-note'})
            if code!=200 or notes['data']['memories']:raise RuntimeError('INSTALLED_NOTE_WITHDRAWAL_REVIVED_OLD_VERSION')
            result['notes_correction_restart_withdrawal']='PASS_ORIGINAL_STORE_NOT_NATURAL_MODEL_RECALL'
        stopped = hostop("STOP")
        assert not stopped["runtime_active"] and stopped["stop_latch"]
        assert call("bootstrap")[0] == 200
        result.update(
            ten_pages="PASS",
            independent_host_stop="PASS",
            same_subject_restart="PASS",
            no_repository_pythonpath="PASS",
            isolation_entry="PASS",
            new_subject_mode="EXPLICIT_DEVELOPMENT_ONLY",
        )
        return result
    finally:
        # Only this owned fixture and process; never a cloud or prior staging.
        try:
            hostop("STOP")
        except Exception:
            pass
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument('--check-memory-notes',action='store_true')
    a = p.parse_args()
    value = run(a.bundle, a.work,check_memory_notes=a.check_memory_notes)
    a.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value))


if __name__ == "__main__":
    main()
