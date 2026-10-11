import hashlib
import json
from pathlib import Path
import sys
import subprocess
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from nana_host_shadow.bootstrap_entry import verify
from nana_host_shadow.iris_wrappers import export,records,count_metadata
from nana_host_shadow.hook_probe import probe


def test_bootstrap_rejects_python_site_initialization_before_package_access(tmp_path):
    entry=Path(__file__).resolve().parents[2]/'tools/nana_host_shadow/bootstrap_entry.py'
    # No bundle exists: the startup barrier must reject before reading it or
    # loading any private runtime/Core, rather than relying on a launch convention.
    result=subprocess.run([sys.executable,'-I','-B',str(entry),str(tmp_path/'absent'),'preflight'],capture_output=True,text=True)
    assert result.returncode==2
    assert json.loads(result.stdout)['reason']=='BLOCKED_STARTUP_ISOLATION'
    assert not (tmp_path/'absent').exists()


def sealed(root):
    root.mkdir();(root/'script.py').write_text('synthetic source')
    files={'script.py':hashlib.sha256((root/'script.py').read_bytes()).hexdigest()}
    m={'Core_source_SHA':'ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513','files':files}
    (root/'manifest.json').write_text(json.dumps(m))
    (root/'SHA256SUMS').write_text(files['script.py']+'  script.py\n'+hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()+'  manifest.json\n')
    return root


def test_every_file_integrity_and_mutable_data_separation(tmp_path):
    p=sealed(tmp_path/'bundle');assert verify(p)['files']
    (p/'data').mkdir();(p/'data/opaque').write_text('synthetic state');assert verify(p)
    (p/'script.py').write_text('tampered')
    with pytest.raises(ValueError,match='BLOCKED_PACKAGE_INTEGRITY'):verify(p)


@pytest.mark.parametrize('change',['extra','symlink','manifest','sums','uncommitted'])
def test_integrity_fails_closed_for_unreviewed_bundle(tmp_path,change):
    p=sealed(tmp_path/'bundle')
    if change=='extra':(p/'injected.pyc').write_bytes(b'cache')
    elif change=='symlink':(p/'script.py').unlink();(p/'script.py').symlink_to(tmp_path/'other')
    elif change=='manifest':(p/'manifest.json').write_text('{}')
    elif change=='sums':(p/'SHA256SUMS').write_text('wrong')
    else:
        m=json.loads((p/'manifest.json').read_text());m['support_worktree_dirty']=True;(p/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):verify(p)


def fixture():
    return {'synthetic':True,'private':False,'source_identity':'synthetic:wrapper',
        'l1_queues':[{'session_id':'synthetic-chat','segment_1':[{'role':'user','content':'Fictional private marker',
            'timestamp':'2026-10-10T00:00:00Z','token_count':4,'source':'synthetic-user','metadata':{},'persona_id':'default'}],
            'segment_2':[],'segment_3':[]}],
        'profile_kv':{'user_profile:default:synthetic-chat:synthetic-user':{'user_id':'synthetic-user','user_name':'Fictional name','version':1},
            'group_profile:default:synthetic-chat':{'group_id':'synthetic-chat','group_name':'Fictional group','version':1}}}


def test_schema_only_never_opens_supplied_private_path(tmp_path):
    unknown=tmp_path/'not-readable.json'
    r=export(unknown)
    assert r['private_records_read']==0 and r['production_reader_enabled'] is False
    assert r['l1']['native_persistent_wrapper']=='ABSENT_IN_LOCKED_UPSTREAM'
    assert 'user_name' in r['user_profile']['fields'] and r['user_profile']['KV_key'].startswith('user_profile:')


@pytest.mark.parametrize('mode',['count-only','hash-only','redacted-sample'])
def test_native_fields_and_profile_kv_wrappers_without_plaintext_output(tmp_path,mode):
    p=tmp_path/'synthetic.json';p.write_text(json.dumps(fixture()));before=p.read_bytes()
    a=export(p,mode=mode);b=export(p,mode=mode)
    assert p.read_bytes()==before and 'Fictional' not in json.dumps(a)
    assert a['private_records_read']==0 and a['synthetic_fixture'] and not a['production_reader_enabled']
    if mode=='count-only':assert a['record_counts']=={'l1':1,'user_profile':1,'group_profile':1}
    else:
        assert a['total_records']==3 and [r['stable_legacy_id'] for r in a['records']]==[r['stable_legacy_id'] for r in b['records']]
        assert all(r['assessment']['Core']=='UNASSESSED' for r in a['records'])


def test_wrapper_drift_missing_fields_privacy_and_secret_are_rejected(tmp_path):
    data=fixture();data['private']=True
    with pytest.raises(ValueError,match='PRIVACY'):records(data)
    data=fixture();data['l1_queues'][0]['segment_1'][0].pop('timestamp')
    with pytest.raises(ValueError,match='DRIFT'):records(data)
    data=fixture();data['profile_kv']['user_profile:default:synthetic-chat:synthetic-user']['user_id']='other'
    with pytest.raises(ValueError,match='CONFLICT'):records(data)
    p=tmp_path/'fixture.json';data=fixture();data['l1_queues'][0]['segment_1'][0]['metadata']={'api_key':'synthetic-placeholder'};p.write_text(json.dumps(data))
    from nana_core.contracts import CoreError
    with pytest.raises(CoreError,match='SECRET'):export(p,mode='hash-only')
    with pytest.raises(ValueError):count_metadata({'l1':True,'user_profile':0,'group_profile':0})


def test_profile_empty_group_bucket_is_preserved_not_silently_dropped():
    data={'synthetic':True,'private':False,'profile_kv':{'user_profile:default::synthetic-user':{'user_id':'synthetic-user','version':1}}}
    rows=records(data)
    assert len(rows)==1 and rows[0][1]=='user_profile:default::synthetic-user'


def test_wrapper_duplicate_json_fields_are_not_silently_overwritten(tmp_path):
    p=tmp_path/'fixture.json';p.write_text('{"synthetic":true,"private":false,"profile_kv":{},"profile_kv":{}}')
    with pytest.raises(ValueError,match='DUPLICATE_FIELD'):export(p,mode='hash-only')


def test_hook_names_are_metadata_not_dynamic_hook_proof(tmp_path):
    p=tmp_path/'event_hook.py';p.write_text('def register_observer(): pass\ndef unregister_observer(): pass\n')
    r=probe([p]);assert r['available_API_names']==['register_observer','unregister_observer']
    assert r['dynamic_registration']=='UNKNOWN' and r['restart_required']=='UNKNOWN' and not r['hook_installed']
    assert r['FIRST_REAL_MESSAGE_STREAM_SHADOW'].startswith('BLOCKED') and r['host_imports']==0
    bad=tmp_path/'secret.py';bad.write_text('synthetic')
    with pytest.raises(ValueError,match='SCOPE'):probe([bad])
