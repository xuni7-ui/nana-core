import hashlib,json,sqlite3
import pytest
from nana_core.integration.exporter import bundle,read_sqlite_snapshot,read_json_snapshot
from nana_core.integration.preflight import probe
from nana_core.contracts import CoreError
from nana_core.clock import ManualClock

def test_snapshot_readonly_and_modes(tmp_path):
    p=tmp_path/'metadata.db'
    with sqlite3.connect(p) as db:
        db.execute('CREATE TABLE memories(memory_id TEXT,content TEXT,metadata TEXT,timestamp TEXT)')
        db.execute('INSERT INTO memories VALUES(?,?,?,?)',('synthetic-m1','Fictional private marker','{}','2026-10-01T00:00:00Z'))
    before=p.read_bytes();names=set(tmp_path.iterdir())
    rows=read_sqlite_snapshot(p,'memories',frozen=True)
    h=bundle(rows,'synthetic:host',clock=ManualClock());assert 'Fictional private marker' not in json.dumps(h) and h['mode']=='hash-only'
    assert h['records'][0]['payload'] is None and h['records'][0]['underlying_occurrence_time_us'] is None
    include=bundle(rows,'synthetic:host',mode='include');assert include['records'][0]['payload']['content']=='Fictional private marker'
    red=bundle(rows,'synthetic:host',mode='redact');assert red['records'][0]['payload']['content']=='[REDACTED]'
    assert p.read_bytes()==before and set(tmp_path.iterdir())==names
    with pytest.raises(CoreError,match='FROZEN'):read_sqlite_snapshot(p,'memories')
    with pytest.raises(CoreError,match='QUERY'):read_sqlite_snapshot(p,'memories;DROP TABLE memories',frozen=True)
    with pytest.raises(CoreError,match='SECRET'):bundle([('l2_row','x',{'content':'safe','metadata':{'api_key':'synthetic-placeholder'}})],'s')

def test_bounded_json_and_metadata_preflight(tmp_path):
    p=tmp_path/'rows.json';p.write_text(json.dumps([{'legacy_key':'a','payload':{'role':'user','content':'Synthetic'}}]))
    rows=read_json_snapshot(p,'l1',frozen=True);assert bundle(rows,'synthetic:s')['total_records']==1
    with pytest.raises(CoreError,match='DUPLICATE'):bundle(rows+rows,'synthetic:s')
    secret=tmp_path/'secret';secret.write_text('do not read this synthetic marker');before=secret.read_bytes()
    r=probe({'opaque':str(secret),'missing':str(tmp_path/'absent')})
    assert r['status']=='BLOCKED' and r['files_written']==0 and 'do not read' not in json.dumps(r)
    assert secret.read_bytes()==before and not r['private_content_read']
    assert any(c['status']=='UNKNOWN' for c in r['checks'])
