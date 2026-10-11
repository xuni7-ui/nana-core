"""Real subprocesses, fixed package; a development machine is NOT the Nana host."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from nana_host_shadow.build import build
from nana_host_shadow.safety import APPROVED_SHA, verify_bundle, digest
from nana_host_shadow.metadata import schema_only
from nana_host_shadow.observer import ProbeObserver, LocalProbe, new_probe


@pytest.fixture
def bundle(tmp_path):
    p = tmp_path / 'bundle'
    build(Path(__file__).resolve().parents[2], p)
    return p


def invoke(bundle, command, *args, check=True):
    p = subprocess.run([sys.executable, '-I', str(bundle / 'nana-shadow'), command, *map(str, args)],
                       text=True, capture_output=True, timeout=15)
    if check:
        assert p.returncode == 0, p.stdout + p.stderr
    return p, json.loads(p.stdout)


def wait_state(path, phase='RUNNING', process=None):
    end = time.monotonic() + 8
    while time.monotonic() < end:
        if process is not None and process.poll() is not None:
            raise AssertionError(process.communicate())
        if path.exists():
            state = json.loads(path.read_text())
            if state['phase'] == phase:
                return state
        time.sleep(.01)
    raise AssertionError('state not reached')


def test_fixed_source_integrity_and_no_global_install(bundle, tmp_path):
    m = verify_bundle(bundle)
    assert m['source_commit'] == APPROVED_SHA and not m['core_modified'] and len(m['core_files']) == 55
    _, pf = invoke(bundle, 'preflight')
    assert pf['adapter_local_probe_ready'] and not pf['astrbot_hook_ready'] and pf['files_written'] == 0
    assert any(c['check'] == 'dynamic_observer' and c['status'] == 'UNKNOWN' for c in pf['checks'])
    cache=bundle/'src/nana_core/__pycache__';cache.mkdir();(cache/'actions.cpython-312.pyc').write_bytes(b'fake-cache')
    with pytest.raises(ValueError,match='UNREVIEWED_CORE_FILE'):verify_bundle(bundle)
    (cache/'actions.cpython-312.pyc').unlink();cache.rmdir()
    (bundle / 'src/nana_core/actions.py').write_text('raise RuntimeError("tamper")')
    p, blocked = invoke(bundle, 'start', '--workdir', tmp_path/'shadow', '--window-seconds', 0, check=False)
    assert p.returncode == 2 and blocked['status'] == 'BLOCKED' and not (tmp_path/'shadow').exists()


def test_first_probe_restart_dedup_evidence_candidate_barrier(bundle, tmp_path):
    w = tmp_path / 'shadow'
    _, first = invoke(bundle, 'start', '--workdir', w, '--window-seconds', 0)
    _, second = invoke(bundle, 'start', '--workdir', w, '--window-seconds', 0)
    assert first['process_id'] != second['process_id']
    assert first['identity'] == second['identity'] and first['probe_event_id'] == second['probe_event_id']
    assert not first['identity_restored'] and second['identity_restored']
    assert len(first['memory_context_ids']) == 1 and first['memory_context_ids'] == second['memory_context_ids']
    assert first['evidence_hash'] == second['evidence_hash'] and first['goal_candidate_id'] == second['goal_candidate_id']
    assert second['goal_candidate_state'] == 'ACCEPTED' and second['counts']['jobs'] == 1
    assert second['shadow_plan_count'] == second['shadow_decision_count'] == 1
    assert second['FIRST_REAL_CLOUD_SHADOW'] == 'NOT_RUN' and second['scope'] == 'ENGINEERING_SHADOW'
    assert second['reconciliation']['status'] == 'PASS' and all(second['reconciliation']['matches'].values())
    assert len(second['barrier']) == 5 and all(r['status'] == 'SHADOW_BLOCKED' for r in second['barrier'])
    assert all(second['counts'][t] == 0 for t in ('actions', 'attempts', 'grants', 'budgets', 'strategies', 'goals', 'plans'))
    assert second['observer_removed'] and second['store_closed'] and second['shadow_runtime_stopped']
    assert second['observer_lifecycle'] == ['install', 'probe_received', 'probe_received', 'uninstall']
    assert not second['execution_owner_changed'] and not second['memory_authority_changed']
    db = sqlite3.connect(w/'shadow.db')
    assert db.execute("SELECT count(*) FROM events WHERE kind='observation.received'").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM events WHERE kind='cloud.probe_actions_blocked'").fetchone()[0] == 1
    assert not db.execute("SELECT key FROM core_meta WHERE key IN ('migration.execution_owner','cloud.memory_protocol')").fetchall()
    db.close()
    _, collected = invoke(bundle, 'collect', '--workdir', w)
    assert len(collected['reports']) == 2 and not collected['database_exported']
    assert not any(collected[k] for k in ('runtime_active', 'private_content_included'))


def test_stop_and_rollback_bound_to_one_workspace(bundle, tmp_path):
    w = tmp_path/'shadow'
    p = subprocess.Popen([sys.executable, '-I', str(bundle/'nana-shadow'), 'start', '--workdir', str(w), '--window-seconds', '30'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_state(w/'session.json', process=p)
        rejected, _ = invoke(bundle, 'start', '--workdir', w, '--window-seconds', 0, check=False)
        assert rejected.returncode == 2
        _, blocked = invoke(bundle, 'collect', '--workdir', w, check=False)
        assert blocked['status'] == 'BLOCKED'
        _, r = invoke(bundle, 'rollback', '--workdir', w)
        out, err = p.communicate(timeout=8)
        assert p.returncode == 0, err + out
        assert r['status'] == 'PASS' and not r['runtime_active'] and r['evidence_deleted'] == 0
        report = json.loads(out)
        assert report['observer_removed'] and report['store_closed']
        _, stopped = invoke(bundle, 'stop', '--workdir', w)
        assert stopped['status'] == 'INACTIVE' and stopped['signals_sent'] == 0
        _, r2 = invoke(bundle, 'rollback', '--workdir', w)
        assert r2 == r and not (w/'stop_request.json').exists()
    finally:
        if p.poll() is None:
            p.kill(); p.wait()


def test_probe_only_lifecycle_drops_real_event_and_wrong_flags():
    received=[]; observer=ProbeObserver(received.append); token=observer.install(); p=new_probe()
    with pytest.raises(ValueError, match='PROBE_ONLY'):observer.emit({'content':'not read'}, token)
    for patch in ({'private':True}, {'synthetic':False}, {'external_delivery':True}, {'source':'astrbot'}, {'event_id':'other'}):
        with pytest.raises(ValueError, match='PROBE_SCOPE'):observer.emit(LocalProbe(**{**vars(p), **patch}), token)
    with pytest.raises(ValueError, match='PROBE_ONLY'):observer.emit(p, 'wrong')
    observer.emit(p, token); observer.uninstall(); observer.uninstall()
    with pytest.raises(ValueError, match='PROBE_ONLY'):observer.emit(p, token)
    assert received == [p] and observer.lifecycle == ['install','probe_received','uninstall']


def test_no_existing_directory_or_symlink_can_be_repurposed(bundle, tmp_path):
    production = tmp_path/'production'; production.mkdir(); (production/'untouched').write_text('synthetic')
    _, r = invoke(bundle, 'start', '--workdir', production, '--window-seconds', 0, check=False)
    assert r['status'] == 'BLOCKED' and set(x.name for x in production.iterdir()) == {'untouched'}
    link = tmp_path/'link'; link.symlink_to(production, target_is_directory=True)
    _, r = invoke(bundle, 'start', '--workdir', link, '--window-seconds', 0, check=False)
    assert r['status'] == 'BLOCKED' and (production/'untouched').read_text() == 'synthetic'
    _, r = invoke(bundle, 'start', '--workdir', tmp_path/'shadow', '--window-seconds', 601, check=False)
    assert r['status'] == 'BLOCKED' and not (tmp_path/'shadow').exists()


def test_schema_only_preserves_database_and_hides_body_defaults(tmp_path):
    p = tmp_path/'iris.db'; db=sqlite3.connect(p)
    db.executescript("CREATE TABLE memories(id TEXT PRIMARY KEY,content TEXT DEFAULT 'fictional-private-default'); CREATE INDEX content_idx ON memories(content); CREATE TABLE nodes(id TEXT, label TEXT); CREATE TABLE edges(source_id TEXT,target_id TEXT); INSERT INTO memories VALUES('m','fictional-private-body');")
    db.close(); before=digest(p.read_bytes()); r=schema_only(p)
    assert before==digest(p.read_bytes()) and r['private_records_read']==r['writes']==r['application_row_queries']==0
    assert {t['table'] for t in r['tables']}=={'memories','nodes','edges'}
    assert 'fictional-private' not in json.dumps(r) and r['status']=='UNASSESSED'
    assert set(x.name for x in tmp_path.iterdir())=={'iris.db'}
    Path(str(p)+'-wal').write_bytes(b'')
    with pytest.raises(ValueError,match='FROZEN'):schema_only(p)


def test_sigkill_recovery_never_reports_clean_rollback(bundle, tmp_path):
    w=tmp_path/'shadow'
    p=subprocess.Popen([sys.executable,'-I',str(bundle/'nana-shadow'),'start','--workdir',str(w),'--window-seconds','30'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        wait_state(w/'session.json',process=p)
        # Wait for committed candidate/draft/barrier, not merely a mocked crash
        # boundary or a PID file written before the actual probe has run.
        end=time.monotonic()+8
        probe_eid=None
        while time.monotonic()<end:
            if (w/'shadow.db').exists():
                db=sqlite3.connect((w/'shadow.db').as_uri()+'?mode=ro',uri=True)
                try:
                    audit=db.execute("SELECT event_id FROM events WHERE kind='cloud.probe_actions_blocked'").fetchone()
                    row=db.execute("SELECT event_id FROM events WHERE kind='observation.received'").fetchone()
                    if audit and row:probe_eid=row[0];break
                except sqlite3.OperationalError:pass
                finally:db.close()
            time.sleep(.01)
        assert probe_eid is not None
        assert (w/'identity_metadata.json').exists()
        identity=json.loads((w/'identity_metadata.json').read_text())
        os.kill(p.pid,signal.SIGKILL);p.communicate(timeout=5);assert p.returncode==-signal.SIGKILL
        _, rollback=invoke(bundle,'rollback','--workdir',w)
        assert rollback['status']=='UNKNOWN_UNCLEAN_TERMINATION' and not rollback['runtime_active']
        _, resumed=invoke(bundle,'start','--workdir',w,'--window-seconds',0)
        assert resumed['prior_termination']=='UNKNOWN' and resumed['identity']==identity
        assert resumed['probe_event_id']==probe_eid and resumed['counts']['jobs']==1
        assert all(resumed['counts'][t]==0 for t in ('actions','attempts','grants','budgets'))
        assert resumed['observer_removed'] and resumed['store_closed']
    finally:
        if p.poll() is None:p.kill();p.wait()


def test_callback_failure_always_removes_observer_closes_store(tmp_path):
    from nana_host_shadow.runtime import probe_session
    from nana_core.storage import Store
    captured=[]
    class FailureObserver(ProbeObserver):
        def install(self):
            captured.append(self)
            return super().install()
        def emit(self, probe, token):
            super().emit(probe, token)
            raise RuntimeError('synthetic callback failure')
    w=tmp_path/'shadow';w.mkdir()
    with pytest.raises(RuntimeError,match='synthetic callback failure'):
        probe_session(w,host_instance='synthetic-host',window_seconds=0,stop_requested=lambda:False,observer_factory=FailureObserver)
    assert len(captured)==1 and not captured[0].active and captured[0].lifecycle[-1]=='uninstall'
    with Store(w/'shadow.db') as s:
        assert not any(s.all(t) for t in ('actions','grants','budgets','attempts'))
        assert len([e for e in s.all('events') if e['kind']=='observation.received'])==1


def test_corrupt_session_metadata_releases_launcher_lock(bundle, tmp_path):
    from nana_host_shadow.launcher import workspace, active
    w=workspace(tmp_path/'shadow',create=True)
    (w/'session.json').write_text('{broken')
    # A fresh process is required: this test runner already imported development
    # Core. The launcher correctly refuses to reuse that module as the fixed
    # package. Do not weaken that source-verification gate to fault-inject JSON.
    p,r=invoke(bundle,'start','--workdir',w,'--window-seconds',0,check=False)
    assert p.returncode==2 and r['error_category']=='JSONDecodeError'
    assert not active(w) and not (w/'shadow.db').exists()


def test_schema_authorizer_rejects_application_row_select(tmp_path, monkeypatch):
    # Fault-inject a query into the existing connection, not a separate weaker
    # implementation. The authorizer must refuse it before a body is fetched.
    p=tmp_path/'iris.db';db=sqlite3.connect(p)
    db.execute('CREATE TABLE memories(id TEXT,content TEXT)');db.execute("INSERT INTO memories VALUES('m','synthetic-body')");db.commit();db.close()
    real_connect=sqlite3.connect
    denied=[]
    class InspectedConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.startswith('SELECT name FROM sqlite_schema'):
                with pytest.raises(sqlite3.DatabaseError):super().execute('SELECT content FROM memories').fetchall()
                denied.append(True)
            return super().execute(sql,parameters)
    def connect(*args,**kwargs):return real_connect(*args,**kwargs,factory=InspectedConnection)
    monkeypatch.setattr(sqlite3,'connect',connect)
    before=digest(p.read_bytes());r=schema_only(p)
    assert denied==[True] and before==digest(p.read_bytes()) and r['private_records_read']==0
