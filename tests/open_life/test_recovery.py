import json,os,signal,subprocess,sys
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.continuity.open_life.opportunities import OpportunityQueue
from nana_core.presence.authority import VirtualClock

def test_actual_sigkill_after_c_commit_before_attention_ack(tmp_path):
    child=subprocess.run([sys.executable,'-m','tests.open_life.crash_worker',str(tmp_path)],env={'PATH':os.defpath,'PYTHONPATH':str(Path.cwd())+':'+str(Path('src').resolve())},capture_output=True,timeout=15)
    assert child.returncode==-signal.SIGKILL,child.stderr.decode()[:1000]
    cut=json.loads((tmp_path/'cut.json').read_text())
    with open_runtime(tmp_path/'s.db',VirtualClock()) as r:
        q=OpportunityQueue(r);result=q.opportunity()
        assert result['state']=='C_JUDGED'
        assert r.identity_id==cut['identity_id']
        assert len(r.store.all('subject_cycles'))==cut['cycles']
        for _ in range(30):q.opportunity()
        assert len(r.store.all('subject_cycles'))==cut['cycles']
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
