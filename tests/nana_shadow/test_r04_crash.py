"""Actual OS SIGKILL(-9), not mocks. Store's FULL WAL commit is the boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from test_r04_receipt import setup,arm,RAW,NOW,FixtureTrustStore,OneShotCoreSink,OneShotSanitizer,ManualClock,parse_utc

@pytest.mark.parametrize('point,consumed,evidence',[
    ('before_consume',False,False),('before_consume_commit',False,False),
    ('after_consume_commit',True,False),('before_evidence',True,False),('after_evidence',True,True)])
def test_real_sigkill_atomic_receipt_and_no_replay(tmp_path,point,consumed,evidence):
    path=tmp_path/'shadow';sink,l,r=setup(path);arm(l,r);identity=l.store.identity;sink.close()
    marker=tmp_path/'checkpoint'
    code='''import os,sys,time,json
from pathlib import Path
from tools.nana_astrbot_shadow.one_shot_ingress import OneShotCoreSink,OneShotSanitizer
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
from nana_core.clock import ManualClock,parse_utc
path,rid,point,marker,raw=sys.argv[1:]
def checkpoint(p):
    if p==point:
        Path(marker).write_text(p)
        while True:time.sleep(.02)
s=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=rid)
sink=OneShotCoreSink(path,s,rid,trust=FixtureTrustStore(),checkpoint=checkpoint)
sink.ledger().store.clock=ManualClock(parse_utc(json.loads(raw)['timestamp']))
sink.accept(json.loads(raw))
'''
    env=dict(os.environ);env['PYTHONPATH']=str(Path('.').resolve())+os.pathsep+str(Path('src').resolve())
    p=subprocess.Popen([sys.executable,'-c',code,str(path),r.receipt_id,point,str(marker),json.dumps(RAW)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        end=time.monotonic()+10
        while not marker.exists() and p.poll() is None and time.monotonic()<end:time.sleep(.01)
        assert marker.exists()
        p.kill();assert p.wait(timeout=5)==-9
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=5)
        p.communicate(timeout=5)
    s=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id)
    sink=OneShotCoreSink(path,s,r.receipt_id,trust=FixtureTrustStore());l=sink.ledger()
    l.store.clock=ManualClock(parse_utc(NOW.isoformat()))
    assert l.store.identity==identity
    status=l.status(r.receipt_id)
    assert status['uses']==int(consumed)
    observed=[e for e in l.store.all('events') if e['kind']=='observation.received']
    assert len(observed)==int(evidence)
    if consumed:
        assert status['completion']=='UNKNOWN'
        with pytest.raises(ValueError,match='ALREADY_CONSUMED'):sink.accept(dict(RAW))
        with pytest.raises(ValueError):l.arm(r.receipt_id)
    else:
        assert status['state']=='ARMED'
        sink.accept(dict(RAW));assert l.status(r.receipt_id)['uses']==1
    assert len([e for e in l.store.all('events') if e['kind']=='observation.received'])==int(evidence or not consumed)
    assert all(len(l.store.all(t))==0 for t in ('actions','attempts','grants','budgets','strategies'))
    sink.close()


def test_receipt_partial_projection_corruption_rejects(tmp_path):
    sink,l,r=setup(tmp_path/'shadow');arm(l,r);sink.accept(dict(RAW))
    row=l.store.one('core_meta','r04.receipt:'+r.receipt_id)
    value=json.loads(row['value_json']);value.update(state='ARMED',uses=0)
    l.store.db.execute('UPDATE core_meta SET value_json=? WHERE key=?',(json.dumps(value),row['key']))
    with pytest.raises(ValueError,match='PROJECTION_CORRUPT'):sink.accept(dict(RAW))
    sink.close()
