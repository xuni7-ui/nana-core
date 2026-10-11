import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from tools.nana_astrbot_shadow.core_sink import MetadataCoreSink
from tools.nana_astrbot_shadow.sanitize import MetadataSanitizer
from test_astrbot_sanitizer import event, PROBE

PROBE2='nana-probe-development-v2'
def new_sink(path):
    path.mkdir(exist_ok=True,mode=0o700)
    s=MetadataSanitizer(scope='dev-observer-v1',hash_key=b'D'*32,probe_ids=frozenset({PROBE,PROBE2}))
    return s,MetadataCoreSink(path,s)

def test_persistent_alias_dedup_original_time_and_no_production_state(tmp_path):
    s,sink=new_sink(tmp_path/'shadow')
    first=sink.accept(s.sanitize(event()).metadata)
    changed=event();changed['timestamp']='2026-10-12T00:00:00+00:00'
    second=sink.accept(s.sanitize(changed).metadata)
    other=event();other['probe_id']=PROBE2
    third=sink.accept(s.sanitize(other).metadata)
    assert first['dedup_result']=='NEW' and second['dedup_result']==third['dedup_result']=='DUPLICATE'
    assert first['observation_id']==second['observation_id']==third['observation_id']
    assert first['event_timestamp']==second['event_timestamp']=='2026-10-11T02:00:00+00:00'
    assert len([e for e in sink._store.all('events') if e['kind']=='observation.received'])==1
    assert not any(first['zero_execution_counts'].values())
    identity=first['identity_id']; sink.close()
    s,reopened=new_sink(tmp_path/'shadow'); r=reopened.accept(s.sanitize(changed).metadata)
    assert r['identity_id']==identity and r['observation_id']==first['observation_id'] and r['dedup_result']=='DUPLICATE'
    reopened.close()

def test_same_probe_other_event_is_collision_not_new_memory(tmp_path):
    s,sink=new_sink(tmp_path/'shadow');sink.accept(s.sanitize(event()).metadata)
    e=event();e['event_id']='synthetic-other'
    with pytest.raises(ValueError,match='PROBE_ID_COLLISION'):sink.accept(s.sanitize(e).metadata)
    assert len([e for e in sink._store.all('events') if e['kind']=='observation.received'])==1
    sink.close()

def test_process_restart_recovers_identity_and_dedup(tmp_path):
    code='''import json,sys
from pathlib import Path
from tools.nana_astrbot_shadow.sanitize import MetadataSanitizer
from tools.nana_astrbot_shadow.core_sink import MetadataCoreSink
p=Path(sys.argv[1]);p.mkdir(exist_ok=True,mode=0o700)
s=MetadataSanitizer(scope="dev-observer-v1",hash_key=b"D"*32,probe_ids=frozenset({"nana-probe-development-v1"}))
e={"event_id":"synthetic-event","event_source":"operator_probe","synthetic":True,"probe_id":"nana-probe-development-v1","timestamp":"2026-10-11T02:00:00+00:00"}
sink=MetadataCoreSink(p,s);r=sink.accept(s.sanitize(e).metadata);sink.close();print(json.dumps(r))'''
    env=dict(os.environ);env['PYTHONPATH']=str(Path('src').resolve())+os.pathsep+str(Path('.').resolve())
    argv=[sys.executable,'-c',code,str(tmp_path/'shadow')]
    a=json.loads(subprocess.run(argv,env=env,text=True,capture_output=True,check=True).stdout)
    b=json.loads(subprocess.run(argv,env=env,text=True,capture_output=True,check=True).stdout)
    assert a['dedup_result']=='NEW' and b['dedup_result']=='DUPLICATE'
    assert a['identity_id']==b['identity_id'] and a['observation_id']==b['observation_id']
