"""Manual same-Store old→new communication comparison; synthetic loopback only."""
from __future__ import annotations
import argparse,json,os,resource,socket,subprocess,sys,time
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]

def phase(home,stage):
    original_connect=socket.socket.connect
    def local_only(sock,address):
        if not isinstance(address,tuple) or address[0] not in {'127.0.0.1','::1'}:
            raise RuntimeError('qualification permits synthetic loopback only')
        return original_connect(sock,address)
    socket.socket.connect=local_only
    import nana_core
    from tests.person_self.test_inner_communication import initialize,seed,meaning,render,PRIVATE
    from tests.independent_life.test_dialogue import relay
    from nana_core.life.application import LifeApplication
    from nana_core.presence.authority import VirtualClock
    marker=home/'synthetic-binding.json';life=home/'life'
    if stage=='baseline':
        if life.exists() or marker.exists():raise RuntimeError('fresh synthetic home required')
        initialize(life)
    else:
        binding=json.loads(marker.read_text())
        if binding['domain']!='SYNTHETIC_ONLY':raise RuntimeError('synthetic binding required')
        relative=Path(binding['store_relative'])
        if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('invalid synthetic store path')
        existing=home/relative
        if existing.resolve()!=existing or not existing.is_file():raise RuntimeError('original synthetic Store required; never initialize a replacement')
    with relay(life,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(life,clock=VirtualClock(),router=router) as app:
        app.pause();r=app.runtime
        db=Path(r.store.db.execute('PRAGMA database_list').fetchone()[2])
        if stage=='baseline':
            root,rid=seed(app)
            marker.write_text(json.dumps({'domain':'SYNTHETIC_ONLY','identity_id':r.identity_id,'root':root,'private_record_id':rid,'store_relative':str(db.relative_to(home))}))
        binding=json.loads(marker.read_text());assert binding['identity_id']==r.identity_id
        def storage():
            return {'family_allocated_bytes':sum(p.stat().st_blocks*512 for p in (db,Path(str(db)+'-wal'),Path(str(db)+'-shm')) if p.exists()),
                'page_count':r.store.db.execute('PRAGMA page_count').fetchone()[0],
                'freelist_count':r.store.db.execute('PRAGMA freelist_count').fetchone()[0],
                'db_total_changes':r.store.db.total_changes}
        before=storage();cpu=time.process_time_ns();wall=time.monotonic_ns()
        result=app.chat('SYNTHETIC same comparison input',topic='own-curiosity',privacy='PROJECT',message_id='source-'+stage)
        elapsed={'cpu_us':(time.process_time_ns()-cpu)//1000,'wall_us':(time.monotonic_ns()-wall)//1000,
            'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        after=storage();ids=[q['request_id'] for q in requests]
        rows=[r.store.one('cognitive_requests',key) for key in ids]
        cycle=r.subject.result(r.store.one('subject_cycles',result['cycle_id']))
        choice=getattr(cycle,'communication_choice',None)
        assert len(requests)==2 and all(q['budget']==requests[0]['budget'] for q in requests)
        def refs_resolve(node,definitions):
            if isinstance(node,dict):
                if '$ref' in node:assert node['$ref'].rsplit('/',1)[-1] in definitions
                for value in node.values():refs_resolve(value,definitions)
            elif isinstance(node,list):
                for value in node:refs_resolve(value,definitions)
        for request in requests:refs_resolve(request['expected_schema'],request['expected_schema'].get('$defs',{}))
        assert all(PRIVATE not in q['context_json'] for q in requests if q['cognitive_role']=='SOCIAL')
        assert not r.store.all('actions') and not r.store.all('grants')
        return {'stage':stage,'module':str(Path(nana_core.__file__).resolve()),'identity_id':r.identity_id,
            'private_record_id':binding['private_record_id'],'reply':result['text'],
            'choice':choice.model_dump(mode='json') if choice else None,'fixture_http_calls':len(requests),
            'real_model_calls':0,'budget':requests[0]['budget'],
            'request_roles':[q['cognitive_role'] for q in requests],
            'private_context_by_role':[PRIVATE in q['context_json'] for q in requests],
            'measured_wire_input_bytes':[x['input_bytes'] for x in rows],
            'measured_wire_output_bytes':[x['output_bytes'] for x in rows],
            'fixture_http_latency_us':[x['latency_us'] for x in rows],
            'fixture_usage_tokens_per_call':{'input':10,'output':10,'not_real_token_measurement':True},
            'real_provider_tokens':None,'real_provider_cost':None,'timing':elapsed,
            'storage_before':before,'storage_after':after,
            'scope':'CONTROLLED_SINGLE_SAMPLE_NOT_P50_P95_OR_PRODUCTION_PERFORMANCE'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--baseline-source',type=Path);parser.add_argument('--candidate-source',type=Path)
    parser.add_argument('--phase',choices=('baseline','candidate'));args=parser.parse_args();home=args.home.absolute()
    if home.resolve()!=home or not any(home.is_relative_to(Path(p)) for p in ('/tmp','/dev/shm')):
        raise RuntimeError('only an unsymlinked fresh /tmp or /dev/shm qualification directory is supported')
    if args.phase:
        if not home.is_dir():raise RuntimeError('parent must create the fresh directory')
        print(json.dumps(phase(home,args.phase)));return
    if args.baseline_source is None or args.candidate_source is None:parser.error('both source paths required')
    home.mkdir(exist_ok=False,parents=True);results=[]
    for stage,source in [('baseline',args.baseline_source),('candidate',args.candidate_source)]:
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join((str(source.resolve()),str(REPO)))}
        raw=subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'--home',str(home),'--phase',stage],env=env,cwd=REPO,text=True)
        results.append(json.loads(raw))
    old,new=results
    assert old['identity_id']==new['identity_id'] and old['private_record_id']==new['private_record_id']
    assert old['budget']==new['budget'] and old['choice'] is None and new['choice']['approach']=='EXPLORE'
    assert old['reply']=='SYNTHETIC: hello.' and 'two possible connections' in new['reply']
    report={'same_subject':True,'same_store':True,'same_initial_private_state':True,'same_budget':True,
        'single_writer_at_a_time':True,'old_writer_stopped_before_new':True,'stages':results,
        'installation_qualification':False,'real_model_or_production':False,'reverse_source_rollback':'NOT_TESTED'}
    (home/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='stages'}))

if __name__=='__main__':main()
