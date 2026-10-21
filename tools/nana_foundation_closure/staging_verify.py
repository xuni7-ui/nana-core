"""Read-only final audit of the original frozen staging, never a replacement run."""
import hashlib,json,sqlite3,subprocess
from pathlib import Path
ROOT=Path('/workspace/nana-staging/first-life-24h-01')
PIN=Path('/workspace/nana-staging/first-life-source-645899b3')
PIN_HEAD='645899b32220e66a702e75d59a279a3a9685693f'


def require(value,code):
    if not value:raise ValueError(code)


def validate_final(progress,result):
    require(progress['state']=='PASS_24H_DEV' and progress['exit_code']==0,'FINAL_EXIT_NOT_QUALIFIED')
    require(result['source_head']==PIN_HEAD,'WRONG_PIN')
    require(result['actual_residency_seconds']>=86400,'INSUFFICIENT_ACTUAL_DURATION')
    require(result['selected_source_unchanged'] and result['source_hashes_start']==result['source_hashes_end'],'SOURCE_CHANGED')
    require(result['new_provider_calls']==result['real_social_sends']==result['production_changes']==0,'SCOPE_EXPANDED')
    require(result['human_review']=='NOT_RUN','HUMAN_REVIEW_MISATTRIBUTED')
    final=result['final'];before=result['at_work_complete']
    require(final['actions']==before['actions']==result['before_stop']['actions'],'ACTION_REPLAY')
    require(len(final['actions'])==42 and len({x['idempotency_key'] for x in final['actions']})==42,'DUPLICATE_ACTION')
    require(len(final['goals'])==12 and all(x['state'] in {'COMPLETED','FAILED'} for x in final['goals']),'UNSETTLED_GOALS')
    require(final['queue_depth']==final['cognition_calls']==0 and not final['fk_violations'],'FINAL_QUEUE_OR_DB')
    require(not result['final_life']['unknown_actions'],'UNKNOWN_EFFECT')
    restart=result['actual_sigkill_restart']
    require(restart['same_identity'] and restart['no_action_replay'] and restart['no_new_grant'] and restart['new_epoch']>restart['old_epoch'],'RECOVERY_FAILED')
    require(result['actual_external_effects']==14 and result['backup_delete_propagation'],'EFFECT_OR_ERASURE_FAILED')
    restore=result['restored_subject']
    require(restore['identity_id']==final['identity_id'] and restore['grants_all_revoked'] and restore['same_history'] and not restore['provider_configuration_transferred'],'RESTORE_AUTHORITY_FAILED')
    samples=result['samples'];require(len(samples)>=2,'MISSING_RESOURCE_HISTORY')
    elapsed=[s['elapsed_seconds'] for s in samples]
    require(all(a<b for a,b in zip(elapsed,elapsed[1:])) and elapsed[0]<5 and elapsed[-1]>result['actual_residency_seconds']-120,'SAMPLE_COVERAGE')
    require(max(b-a for a,b in zip(elapsed,elapsed[1:]))<120,'RESOURCE_SAMPLE_GAP')
    require(all(s['model_calls']==0 and s['queue']<=1 and s['pending_intentions']<=4 and s['actions']<=42 for s in samples),'HOT_STATE_GROWTH')
    return {'duration_seconds':result['actual_residency_seconds'],'identity_id':final['identity_id'],'samples':len(samples),'max_sample_gap_seconds':max(b-a for a,b in zip(elapsed,elapsed[1:])),'actions':42,'owned_dev_effects':14,'final_queue':0,'unknown_effects':0,'actual_sigkill_restart':restart}


def verify(root=ROOT,pin=PIN):
    # Every input is read from the existing run; no application/Store construction.
    root=Path(root);pin=Path(pin)
    p_raw=(root/'progress.json').read_bytes();r_raw=(root/'result.json').read_bytes()
    progress=json.loads(p_raw);result=json.loads(r_raw);report=validate_final(progress,result)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=pin,text=True).strip();require(head==PIN_HEAD,'PIN_CHECKOUT_CHANGED')
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',PIN_HEAD,'src/nana_core','tools/nana_cloud_daily_life'],cwd=pin,text=True).splitlines()
    expected={n for n in names if n.endswith('.py') and (n.startswith('src/nana_core/') or n.count('/')==2)}
    require(set(result['source_hashes_start'])==expected,'SOURCE_ATTESTATION_COVERAGE')
    for name in sorted(expected):
        original=subprocess.check_output(['git','show',PIN_HEAD+':'+name],cwd=pin)
        sha=hashlib.sha256(original).hexdigest()
        require(result['source_hashes_start'][name]==sha and hashlib.sha256((pin/name).read_bytes()).hexdigest()==sha,'SOURCE_PIN_MISMATCH')
    name='tools/nana_first_life/staging.py';require((pin/name).read_bytes()==subprocess.check_output(['git','show',PIN_HEAD+':'+name],cwd=pin),'SUPERVISOR_SOURCE_CHANGED')
    report['source_pin']={'head':PIN_HEAD,'start_end_current_git_matches':True,'attested_files':len(expected),'supervisor_checked_separately':True}
    dbs={};action_sets={}
    for label,relative in [('source','journey/life/subject/self.db'),('restored','journey/fresh-host/subject/self.db'),('backup','journey/life/backups/checkpoint.db')]:
        path=root/relative
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=1) as db:
            db.row_factory=sqlite3.Row
            require(db.execute('PRAGMA quick_check').fetchone()[0]=='ok','SQLITE_INTEGRITY')
            require(not db.execute('PRAGMA foreign_key_check').fetchall(),'SQLITE_FOREIGN_KEYS')
            require(db.execute('SELECT identity_id FROM identities').fetchone()[0]==report['identity_id'],'IDENTITY_SPLIT')
            actions=[tuple(row) for row in db.execute('SELECT action_id,idempotency_key,state FROM actions ORDER BY action_id')];action_sets[label]=actions
            require(len(actions)==42 and len({a[1] for a in actions})==42 and all(a[2]=='SUCCEEDED' for a in actions),'DB_ACTION_OR_REPLAY')
            require(db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]==0,'UNEXPECTED_PROVIDER_DISPATCH')
            require(db.execute("SELECT count(*) FROM runtime_queue WHERE state NOT IN ('DONE','IGNORED','EXPIRED')").fetchone()[0]==0,'PENDING_QUEUE')
            if label in {'source','restored'}:
                lease=db.execute('SELECT epoch,state FROM runtime_lease').fetchone();require(lease['state']=='STOPPED','WRITER_NOT_STOPPED')
                require(db.execute('SELECT count(*) FROM grants WHERE revoked=0').fetchone()[0]==0,'OLD_GRANT_ACTIVE')
            key={'source':'portable.retired','restored':'portable.received','backup':'recovery_quarantine'}[label]
            meta=db.execute('SELECT value_json FROM core_meta WHERE key=?',(key,)).fetchone();require(meta is not None,'LINEAGE_METADATA_MISSING')
            body=json.loads(meta[0])
            if label=='backup':require(body is True,'BACKUP_RUNNABLE')
            else:require(body['transfer_id']==result['transfer']['manifest']['transfer_id'],'TRANSFER_LINEAGE_MISMATCH')
            dbs[label]={'quick_check':'ok','foreign_key_violations':0,'actions':len(actions),'active_grants':db.execute('SELECT count(*) FROM grants WHERE revoked=0').fetchone()[0],'quarantined_review_copy':label=='backup','pages':db.execute('PRAGMA page_count').fetchone()[0],'page_bytes':db.execute('PRAGMA page_size').fetchone()[0]}
    require(action_sets['source']==action_sets['restored'],'TRANSFER_ACTION_HISTORY_CHANGED')
    external=json.loads((root/'journey/target/application/application-state.json').read_text())
    require(len(external['effects'])==14,'EXTERNAL_EFFECT_COUNT')
    effects=external['effects'];published={a['idempotency_key']:a['action_id'] for a in result['final']['actions'] if a['capability']=='world.publish'}
    require(set(effects)==set(published) and all(effects[k]['action_id']==published[k] and effects[k]['subject_id']==report['identity_id'] for k in effects),'EXTERNAL_EFFECT_CORRELATION')
    storage=json.loads((root/'journey/life/storage-monitor.json').read_text());require(storage['status']=='OBSERVING','STORAGE_GUARD_STOPPED')
    samples=result['samples'];num=lambda v:int(v.split()[0]) if isinstance(v,str) else v
    report['resources']={'rss_max_kib':max(num(s['runtime']['VmRSS']) for s in samples),'threads_max':max(num(s['runtime']['Threads']) for s in samples),'fds_max':max(s['runtime']['fd_count'] for s in samples),'queue_max':max(s['queue'] for s in samples),'pending_intentions_max':max(s['pending_intentions'] for s in samples),'db_family_first_bytes':samples[0]['db_bytes'],'db_family_last_bytes':samples[-1]['db_bytes'],'storage_guard_status':storage['status']}
    report.update(result='PASS_S4_C06_FROZEN_DEV_24H',database=dbs,source_retired=True,restored_grants_revoked=True,backup_delete_propagation=True,exit_code=progress['exit_code'],progress_sha256=hashlib.sha256(p_raw).hexdigest(),raw_result_sha256=hashlib.sha256(r_raw).hexdigest(),raw_result_bytes=len(r_raw),raw_result_path=str(root/'result.json'),staging_modified=False,new_provider_calls=0,human_review='NOT_RUN',production=False,scope='Original frozen owned-development process qualification; not current-code24h/live/provider/human/production qualification',legacy_result_label=result['residency_status'],legacy_label_note='PASS_GE_TWO_HOURS is a generic lower bound;24h is checked independently from actual duration and final evidence.')
    return report

if __name__=='__main__':print(json.dumps(verify(),indent=2))
