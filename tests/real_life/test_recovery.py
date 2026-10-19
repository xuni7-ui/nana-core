import os,signal,subprocess,sys
from pathlib import Path
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.project_work.service import ProjectWork,open_project_runtime,material_for
from nana_core.continuity.project_work.port import ProjectMaterialPort
from tools.nana_real_life.qualification import SOURCES

REPO=Path(__file__).resolve().parents[2]


def test_actual_sigkill_after_artifact_before_receipt_recovers_without_reexecute(tmp_path):
    marker=tmp_path/'after-effect'
    code='''import os,signal,sys
from pathlib import Path
from nana_core.continuity.project_work.port import ProjectMaterialPort
from tools.nana_real_life.qualification import run
original=ProjectMaterialPort.execute
def crash(self,inv):
    result=original(self,inv)
    if inv.capability=='world.publish':
        Path(sys.argv[3]).write_text('effect complete, receipt not committed')
        os.kill(os.getpid(),signal.SIGKILL)
    return result
ProjectMaterialPort.execute=crash
run(Path(sys.argv[1]),Path(sys.argv[2]))
'''
    env={**os.environ,'PYTHONPATH':str(REPO/'src')}
    proc=subprocess.Popen([sys.executable,'-c',code,str(tmp_path/'run'),str(REPO),str(marker)],cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=proc.communicate(timeout=30)
    assert proc.returncode==-signal.SIGKILL,stderr.decode()
    assert marker.exists()
    db=tmp_path/'run/subject/self.db';clock=VirtualClock()
    with open_project_runtime(db,clock) as r:
        materials=tuple(material_for(REPO,p) for p in SOURCES)
        work=ProjectWork(r,REPO,materials,tmp_path/'run/reports',grant=False)
        before=len(r.store.all('actions'));grants=len(r.store.all('grants'));identity=r.identity_id
        goal=work.goal_for(materials[0].material_id)
        publish=next(a for a in r.store.all('actions') if a['capability']=='world.publish')
        assert publish['state'] in {'UNKNOWN','DISPATCHING'}
        files={p.name:p.read_bytes() for p in work.port.output.iterdir()}
        work.run_until(lambda:r.store.one('goals',goal['goal_id'])['state']=='COMPLETED')
        assert len(r.store.all('actions'))==before and len(r.store.all('grants'))==grants
        assert r.identity_id==identity and r.store.one('actions',publish['action_id'])['state']=='SUCCEEDED'
        assert files=={p.name:p.read_bytes() for p in work.port.output.iterdir()}


def test_partial_artifact_stays_unknown_and_does_not_retry(tmp_path,monkeypatch):
    from .test_project_work import setup
    original=ProjectMaterialPort.execute;calls=[]
    def partial(self,inv):
        if inv.capability!='world.publish':return original(self,inv)
        calls.append(inv.idempotency_key)
        result=self._result(inv)
        raw=self._documents(result)['json']
        (self.output/(result['artifact_stem']+'.json')).write_bytes(raw)
        raise TimeoutError('simulated interruption after one artifact component')
    monkeypatch.setattr(ProjectMaterialPort,'execute',partial)
    with open_project_runtime(tmp_path/'subject/self.db',VirtualClock()) as r:
        work,materials=setup(r,tmp_path);work.request(materials[0].material_id)
        work.run_until(lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()))
        exp=r.store.db.execute("SELECT experience_id FROM experiences WHERE outcome='FAILURE'").fetchone()[0]
        work.reflect_failure(exp)
        work.run_until(lambda:bool(calls))
        for _ in range(3):r.clock.source.advance(1_000_000);r.step()
        assert len(calls)==1
        action=next(a for a in r.store.all('actions') if a['capability']=='world.publish')
        assert action['state']=='UNKNOWN' and not list(work.port.output.glob('*.md'))
