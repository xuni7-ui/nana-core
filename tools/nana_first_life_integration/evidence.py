"""Compact evidence from the completed owned process run; no state mutation."""
import argparse,hashlib,json,sqlite3,subprocess
from collections import Counter
from pathlib import Path


def summarize(path,root):
    path=Path(path);root=Path(root);raw=path.read_bytes();r=json.loads(raw);setup=r['integration_setup'];final=r['final'];identity=final['identity_id']
    assert setup['identity_id']==setup['semantic']['identity_id']==identity==r['restored_subject']['identity_id']
    assert r['selected_source_unchanged'] and r['source_hashes_start']==r['source_hashes_end']
    repo=Path(__file__).resolve().parents[2]
    for name,sha in r['source_hashes_end'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',r['source_head']+':'+name],cwd=repo)).hexdigest()==sha,name
    assert len(final['actions'])==42 and len({a['idempotency_key'] for a in final['actions']})==42
    assert final['actions']==r['at_work_complete']['actions']==r['before_stop']['actions']
    assert all(a['state']=='SUCCEEDED' for a in final['actions'])
    assert final['queue_depth']==0 and final['cognition_calls']==1 and not final['fk_violations']
    assert not r['final_life']['unknown_actions']
    assert r['actual_sigkill_restart']['same_identity'] and r['actual_sigkill_restart']['no_action_replay'] and r['actual_sigkill_restart']['no_new_grant']
    assert r['restored_subject']['grants_all_revoked'] and r['restored_subject']['same_history']
    assert r['backup_delete_propagation'] and r['new_provider_calls']==r['real_social_sends']==r['production_changes']==0
    assert r['human_review']=='NOT_RUN' and r['actual_external_effects']==14
    external=json.loads((root/'target/application/application-state.json').read_text())
    assert len(external['effects'])==14
    for key,effect in external['effects'].items():
        assert effect['subject_id']==identity and any(a['action_id']==effect['action_id'] and a['idempotency_key']==key for a in final['actions'])
    dbpath=root/'fresh-host/subject/self.db'
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
        counts={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('identities','actions','experiences','lessons','strategy_assessments','cognitive_requests','open_concerns')}
        outcomes=dict(db.execute('SELECT outcome,count(*) FROM experiences GROUP BY outcome'))
        lesson_states=dict(db.execute('SELECT state,count(*) FROM lessons GROUP BY state'))
        assessments=dict(db.execute('SELECT verdict,count(*) FROM strategy_assessments GROUP BY verdict'))
        skill_count=db.execute("SELECT count(*) FROM continuity_records WHERE record_kind='CODE_SKILL'").fetchone()[0]
        private_rows=db.execute("SELECT lifecycle,count(*) FROM continuity_records WHERE target_id='private-intent.v1' GROUP BY lifecycle").fetchall()
        verified_actions=db.execute("SELECT count(*) FROM actions a JOIN events e ON e.event_id=json_extract(a.body_json,'$.verification_event_id') WHERE e.kind='action.verified'").fetchone()[0]
        assert counts['identities']==1 and counts['cognitive_requests']==1 and verified_actions==42
        assert outcomes.get('FAILURE',0)>0 and outcomes.get('SUCCESS',0)>0 and assessments.get('SUCCESS',0)>0 and skill_count>0
    samples=r['samples'];elapsed=[x['elapsed_seconds'] for x in samples]
    assert elapsed[0]<5 and elapsed[-1]>r['actual_residency_seconds']-120
    assert all(b>a for a,b in zip(elapsed,elapsed[1:]))
    from nana_core.life.application import runtime_config
    from nana_core.life.config import load_config
    capacity=runtime_config(load_config(root/'fresh-host')).queue_capacity
    # Concurrent user + maintenance events legitimately occupy two slots. Check
    # the actual frozen Runtime capacity and complete drain, not an invented1.
    assert all(s['queue']<=capacity and s['pending_intentions']<=6 and s['model_calls']==1 for s in samples)
    assert all(s['queue']==0 for s in samples if s['elapsed_seconds']>r['work_complete_at_seconds']+120)
    number=lambda v:int(v.split()[0]) if isinstance(v,str) else v
    return {'level':'ACTUAL_OWNED_DEV_PROCESS_WITH_SYNTHETIC_SEMANTIC_PROVIDER','source_head':r['source_head'],'source_hashes_unchanged_and_match_commit':True,'source_files_attested':len(r['source_hashes_end']),'raw_result_sha256':hashlib.sha256(raw).hexdigest(),'raw_result_bytes':len(raw),'identity_id':identity,'same_identity_through_all_stages':True,'duration_seconds':r['actual_residency_seconds'],'samples':len(samples),'resources':{'rss_max_kib':max(number(x['runtime']['VmRSS']) for x in samples),'threads_max':max(number(x['runtime']['Threads']) for x in samples),'fds_max':max(x['runtime']['fd_count'] for x in samples),'queue_max':max(x['queue'] for x in samples),'pending_intentions_max':max(x['pending_intentions'] for x in samples),'db_bytes_first':samples[0]['db_bytes'],'db_bytes_last':samples[-1]['db_bytes']},'fixture_semantic':setup['semantic'],'private_intent':setup['private_intent'],'manager':setup['manager'],'conversation_refusal_not_cognitive_boundary':setup['conversation_refusal_not_cognitive_boundary'],'actions':42,'verified_actions':verified_actions,'owned_dev_effects':14,'no_duplicate_effect':True,'actual_sigkill_restart':r['actual_sigkill_restart'],'backup_delete_propagation':True,'restored_subject':r['restored_subject'],'database_counts':counts,'experience_outcomes':outcomes,'lesson_states':lesson_states,'strategy_assessments':assessments,'code_skill_records':skill_count,'private_record_lifecycles':dict(private_rows),'real_provider_calls':0,'human_review':'NOT_RUN','live_semantic_combination_this_subject':'NOT_RUN','production':False,'social_send':False,'user_device':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args();print(json.dumps(summarize(a.result,a.root),ensure_ascii=False,indent=2))
