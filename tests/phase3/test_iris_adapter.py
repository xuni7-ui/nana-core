import json,os,signal,subprocess,sys
from pathlib import Path
import pytest
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError
from nana_core.migration.iris import IrisAdapter,IrisRecord,map_record
from nana_core.migration.iris_fixtures import fixtures
from nana_core.storage import Store,digest


def test_real_schema_types_exact_source_times_and_idempotency(tmp_path):
    records=fixtures()
    with Store(tmp_path/'core.db',ManualClock()) as store:
        identity=store.identity
        first=IrisAdapter(store).import_batch(records);second=IrisAdapter(store).import_batch(records)
        assert len(first['results'])==14 and all(r['status']=='IMPORTED' for r in first['results'])
        assert all(r['status']=='DUPLICATE' for r in second['results'])
        assert len(store.all('memory_items'))==14 and store.identity==identity
        assert not any(store.all(t) for t in ('actions','grants','strategies','goals','budgets'))
        for record,result in zip(records,first['results']):
            assert IrisAdapter(store).importer.supplied_source(result['event_id'])['payload']==record.raw_json
            body=json.loads(store.one('memory_items',result['event_id'])['body_json'])
            assert body['assessment']=='UNASSESSED' and not body['execution_evidence']
            assert body['iris']['origin']['legacy_key']==record.legacy_key
        summary=next(r for r in first['results'] if r['legacy_key']=='summary')
        assert json.loads(store.one('memory_items',summary['event_id'])['body_json'])['epistemic_kind']=='SUMMARY'
        assert store.event(first['results'][0]['event_id'])['occurred_at_us']==1788220800000000


@pytest.mark.parametrize('mutation,error',[
    ('missing','IRIS_REQUIRED_FIELD_MISSING'),('mirror','IRIS_TIME_MIRROR_CONFLICT'),('unknown','IRIS_UNMAPPED_KIND'),('metadata','IRIS_DUPLICATE_FIELD_CONFLICT')])
def test_rejections_preserve_full_batch_evidence_and_do_not_silently_drop(tmp_path,mutation,error):
    record=fixtures()[0];row=json.loads(record.raw_json)
    if mutation=='missing':del row['content']
    if mutation=='mirror':record=fixtures()[-2];row=json.loads(record.raw_json);row['ts_cst']='2026-09-02T00:00:00Z'
    if mutation=='metadata':record=fixtures()[4];row=json.loads(record.raw_json);row['timestamp']='2026-09-02T00:00:00Z'
    record=record.model_copy(update={'kind':'unsupported' if mutation=='unknown' else record.kind,'raw_json':json.dumps(row)})
    with Store(tmp_path/'core.db') as store:
        report=IrisAdapter(store).import_batch([record])
        assert report['results'][0]['status']=='REJECTED' and report['results'][0]['error']==error
        assert store.all('memory_items')==[]
        raw=store.artifact(store.all('events')[-1]['artifact_id'])
        assert record.raw_json in json.loads(raw)[0]['raw_json']


def test_bad_time_missing_source_and_new_fields_stay_unassessed(tmp_path):
    record=fixtures()[3];row=json.loads(record.raw_json);row['metadata']={'timestamp':'not-a-time','confidence':1.};row['future_field']='preserved'
    record=record.model_copy(update={'raw_json':json.dumps(row)})
    with Store(tmp_path/'core.db') as store:
        r=IrisAdapter(store).import_record(record);body=json.loads(store.one('memory_items',r['event_id'])['body_json'])
        assert store.event(r['event_id'])['occurred_at_us'] is None
        assert body['iris']['legacy_fields']['future_field']=='preserved'
        assert {'UNKNOWN_TIME','NO_ORIGINAL_SOURCE_LINK','future_field'}<=set(r['warnings'])
        assert body['assessment']=='UNASSESSED'
        changed=record.model_copy(update={'raw_json':record.raw_json+' '})
        with pytest.raises(CoreError,match='LEGACY_SOURCE_KEY_COLLISION'):IrisAdapter(store).import_record(changed)


def test_real_sigkill_between_original_and_projection_resumes(tmp_path):
    db=tmp_path/'core.db'
    script='''import os,signal,sys
from nana_core.storage import Store
from nana_core.migration.iris import IrisAdapter
from nana_core.migration.iris_fixtures import fixtures
with Store(sys.argv[1]) as store:
 print(store.identity["identity_id"],flush=True)
 def fault(point,key):os.kill(os.getpid(),signal.SIGKILL)
 IrisAdapter(store).import_record(fixtures()[0],fault)
'''
    proc=subprocess.run([sys.executable,'-c',script,str(db)],env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':str(Path('src').absolute())},capture_output=True,text=True,timeout=10)
    assert proc.returncode==-signal.SIGKILL
    with Store(db) as store:
        assert store.identity['identity_id']==proc.stdout.strip()
        before=store.all('events')
        r=IrisAdapter(store).import_batch(fixtures())
        assert r['results'][0]['status']=='DUPLICATE' and sum(x['status']=='IMPORTED' for x in r['results'])==13
        assert len(store.all('memory_items'))==14 and store.all('events')[:len(before)]==before
        assert json.loads(store.one('memory_items',r['results'][0]['event_id'])['body_json'])['iris']
