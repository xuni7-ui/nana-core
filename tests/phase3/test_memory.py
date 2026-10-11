import json
from nana_core.clock import ManualClock
from nana_core.memory import MemoryView,shadow_compare
from nana_core.migration.iris import IrisAdapter
from nana_core.migration.iris_fixtures import fixtures
from nana_core.phase3.memory_rehearsal import run,DATASETS
from nana_core.storage import Store


def test_claim_updates_preserve_source_and_shadow_is_pure(tmp_path):
    with Store(tmp_path/'core.db',ManualClock()) as store:
        imported=IrisAdapter(store).import_batch(fixtures());view=MemoryView(store)
        source=store.artifact(store.event(imported['results'][0]['event_id'])['artifact_id'])
        assert view.assess_claims(DATASETS)['changed']==2
        assert view.assess_claims(DATASETS)['changed']==0
        before=store.snapshot();shadow=shadow_compare(store,'paper garden',DATASETS,('m1','m2'))
        assert store.snapshot()==before and shadow['core']['recall']==1
        assert shadow['core']['contradictions_visible']==2
        assert shadow['old']['recall']<shadow['core']['recall']
        assert store.artifact(store.event(imported['results'][0]['event_id'])['artifact_id'])==source
        beliefs=[json.loads(m['body_json']).get('belief') for m in store.all('memory_items')]
        assert {b['current_assessment'] for b in beliefs if b}=={'SUPERSEDED','CURRENT_USER_STATEMENT'}


def test_unknown_order_disputes_instead_of_overwriting(tmp_path):
    records=list(fixtures()[:2]);row=json.loads(records[1].raw_json);row['timestamp']='bad-time';records[1]=records[1].model_copy(update={'raw_json':json.dumps(row)})
    with Store(tmp_path/'core.db') as store:
        IrisAdapter(store).import_batch(records);MemoryView(store).assess_claims(DATASETS)
        assert all(json.loads(m['body_json'])['belief']['current_assessment']=='DISPUTED' for m in store.all('memory_items'))


def test_migration_rehearsal_restarts_replays_and_reconciles(tmp_path):
    report=run(tmp_path/'rehearsal')
    assert report['gate']=='PASS',report['checks']
    assert report['fixture_count']==report['imported']==report['duplicates_on_restart']==14
    assert report['real_model_calls']==report['actual_http_calls']==0
    assert len(report['restarted']['used_memory_ids'])==1
    assert 'False prefers paper-gardens' in report['restarted']['proposal']['purpose']
