"""Actual Core + TLS v2/Web qualification only. Explicit fresh DEV identity.

This is a separate development harness, not the production startup command.
A self-signed loopback certificate is acceptable ONLY for browser tests that
explicitly mark ignoreHTTPSErrors. Never install its trust into an APK or host.
"""

import argparse
from contextlib import ExitStack
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
    parser.add_argument("--web-root",type=Path,help="Explicit compiled Web assets for the same source qualification")
    parser.add_argument("--allow-provider-runtime-budget",action="store_true",help="Explicit fresh DEV metadata/budget setting qualification; no model key or inference")
    parser.add_argument("--allow-private-context", action="store_true", help="Synthetic owned DEV only: explicit PERSONAL surface retention and host scope")
    parser.add_argument("--synthetic-sequence",action="store_true",help="Explicit fresh DEV original-owner + zero-cost loopback sequence probe; no real/private provider")
    a = parser.parse_args()
    if a.synthetic_sequence and (a.allow_provider_configuration or a.allow_provider_runtime_budget or a.allow_private_context):
        raise ValueError("SYNTHETIC_SEQUENCE_REQUIRES_ISOLATED_PROJECT_FIXTURE")
    if a.allow_provider_runtime_budget and not a.allow_provider_configuration:
        raise ValueError("RUNTIME_BUDGET_TEST_REQUIRES_PROVIDER_CONFIGURATION_OPT_IN")
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
    if a.allow_private_context:
        from nana_core.life.config import load_config, update_config
        config = load_config(home)
        bindings = tuple(b.model_copy(update={
            "permitted_privacy": ("PUBLIC", "PROJECT", "PERSONAL"),
            "allow_personal_retention": True,
            "personal_retention_consent_ref": "TEST_ONLY_NOT_SECRET_BROWSER_CONSENT",
        }) if b.binding_id == binding.surface_binding_id else b for b in config.surface_bindings)
        update_config(home, config.model_copy(update={"revision": config.revision + 1, "surface_bindings": bindings}), expected_revision=config.revision)
        binding = binding.model_copy(update={"privacy": ("PUBLIC", "PROJECT", "PERSONAL")})
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    release = Release(release_id="owned-dev", source_commit=source, root=str(ROOT), python=sys.executable)
    with ExitStack() as cleanup:
        supervisor = Supervisor(home, work / "host", binding, [release], active_release="owned-dev")
        cleanup.callback(supervisor.close)
        release_fixture=threading.Event()
        if a.synthetic_sequence:
            # Qualification-only dependencies: absent from portable runtime closure.
            # The existing real Supervisor observes this one in-process DEV owner;
            # owner_managed remainsFalse and no second process/Subject is started.
            import shutil,sqlite3
            from tests.independent_life.test_dialogue import relay
            from tests.first_life_android_v2.test_continuous_inputs import running_owner,setup
            from nana_core.life.config import load_config,update_config
            setup(home)
            config=load_config(home)
            update_config(home,config.model_copy(update={'revision':config.revision+1,
                'provider_calls_per_day':32,'provider_calls_per_hour':32,'per_provider_calls_per_day':32,
                'provider_total_calls_limit':32}),expected_revision=config.revision)
            router,calls=cleanup.enter_context(relay(home,'CHAT',stream_fixture={
                'release':release_fixture,'release_timeout':15,'reset_release':True},
                renderer=lambda request:'SYNTHETIC '+('combined response to '+str(len(request['role_input']['dialogue']['communication_purpose']['respond_to_memory_ids']))
                    if len(request['role_input']['dialogue']['communication_purpose']['respond_to_memory_ids'])>1 else 'individual original response')+' · '+('source-bound fixture wording. '*45)))
            shutil.copy2(home/'test-providers.json',home/'providers.json')
            def record_fixture():
                from nana_core.presence.cli import status
                with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
                    counts={name:db.execute('SELECT count(*) FROM '+name).fetchone()[0]
                        for name in ('identities','cognitive_requests','actions','grants')}
                    counts['surface_events']=db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'local.surface.%'").fetchone()[0]
                (work/'sequence-report.json').write_text(json.dumps({'subject_id':identity,'lineage_binding':lineage,
                    'runtime_active':status(home/'subject/self.db')['runtime_active'],'counts':counts,
                    'roles':[c['cognitive_role'] for c in calls],
                    'purpose_input_counts':[len(c['role_input']['dialogue']['communication_purpose']['respond_to_memory_ids']) for c in calls if c['cognitive_role']=='SOCIAL'],
                    'real_provider_calls':0,'sqlite_version':sqlite3.sqlite_version,'python':sys.version.split()[0]},indent=2)+'\n')
            cleanup.callback(record_fixture)
            cleanup.enter_context(running_owner(home,router))
            cleanup.callback(release_fixture.set)
            watcher_stop=threading.Event()
            def release_when_requested():
                while not watcher_stop.wait(.02):
                    marker=work/'release.fixture'
                    if marker.exists():marker.unlink();release_fixture.set()
            watcher=threading.Thread(target=release_when_requested,daemon=True);watcher.start()
            def stop_watcher():watcher_stop.set();watcher.join(1)
            cleanup.callback(stop_watcher)
        else:
            supervisor.start()
            cleanup.callback(supervisor.stop)
        auth = AuthService(work / "auth.json", password=PW, roles=tuple(Role))
        service = GatewayService(supervisor, auth, work / "host", allow_provider_configuration=a.allow_provider_configuration,
                                 allow_provider_runtime_budget=a.allow_provider_runtime_budget)
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
            web_root=a.web_root or ROOT / "apps/nana-space/dist",
            tls_context=tls,
        )
        (work / "target.json").write_text(
            json.dumps(
                {
                    "subject_id": identity,
                    "lineage_binding": lineage,
                    "origin": f"https://127.0.0.1:{a.port}",
                    "realm": "OWNED_DEVELOPMENT_ONLY",
                    "private_context_qualification": a.allow_private_context,
                    "runtime_budget_qualification":a.allow_provider_runtime_budget,
                    "synthetic_sequence_qualification":a.synthetic_sequence,
                    "synthetic_release_marker":str(work/"release.fixture") if a.synthetic_sequence else None,
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



if __name__ == "__main__":
    main()
