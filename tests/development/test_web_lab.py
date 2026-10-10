import json
from nana_core.development.web_lab import run
from .proof import record


def test_research_restart_crash_and_multitool_experience_ablation(tmp_path):
    report=run(tmp_path/'lab')
    assert report['engineering_gate']=='PASS',report['checks']
    assert all(report['checks'].values())
    assert report['actual_loopback_http_requests']==5
    assert report['actual_public_http_requests']==report['real_model_calls']==report['external_fees']==0
    assert report['E12']==report['semantic_gate']=='NOT_RUN'
    by_phase={p['phase']:p for p in report['phases']}
    learned,ablated=by_phase['next'],by_phase['without_experience']
    assert [s['capability'] for s in learned['plan']['steps']]==[
        'reading.source.read','reading.source.locate','reading.card.create']
    assert [s['capability'] for s in ablated['plan']['steps']]==['reading.source.read','reading.card.create']
    card=next(a for a in learned['actions'] if a['capability']=='reading.card.create')
    locator=next(a for a in learned['actions'] if a['capability']=='reading.source.locate')
    assert json.loads(card['result_json'])['locator']==json.loads(locator['result_json'])['locator']
    assert learned['cited_result']['evidence_artifact_id']
    assert learned['cited_result']['fetched_at_us']!=learned['cited_result']['original_occurred_at_us']
    record('controlled_web_multitool',report)
