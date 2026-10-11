"""Non-private real-schema migration rehearsal, explicit process restart and replay."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from ..clock import ManualClock
from ..contracts import ModelRequest,Observation
from ..memory import MemoryView,shadow_compare
from ..migration.iris import IrisAdapter
from ..migration.iris_fixtures import fixtures
from ..planning import FixtureModel,ContextBuilder
from ..storage import Store,canonical,digest

DATASETS=('synthetic:iris-schema-v030',)


class MemoryDecisionFixture(FixtureModel):
    """Engineering-only ModelPort that explicitly receives selected context."""
    descriptor='memory-engineering-fixture-v1'
    def __init__(self,context):
        super().__init__();self.context=context;self.used_memory_ids=[]
    def propose(self,request):
        if request.identity_id!=self.context['identity_id']:
            raise ValueError('fixture identity mismatch')
        current=[m for m in self.context['items'] if m.get('belief') and
            m['belief']['current_assessment']=='CURRENT_USER_STATEMENT']
        self.used_memory_ids=[m['memory_id'] for m in current]
        base=super().propose(request)
        # Not NLP: reference the structured, operator-annotated current claim.
        if current:
            claim=current[0]['belief']['claim']
            return base.model_copy(update={'purpose':base.purpose+' Current source-backed user statement: '+
                str(claim['polarity'])+' '+claim['predicate']+' '+claim['value']+'.'})
        return base


def session(path,phase):
    with Store(path,ManualClock()) as store:
        if phase=='import':
            first=IrisAdapter(store).import_batch(fixtures())
            MemoryView(store).assess_claims(DATASETS)
            return {'pid':os.getpid(),'identity':store.identity,'manifest':first,'count':len(store.all('memory_items')),
                'event_hashes':[digest(e) for e in store.all('events')]}
        duplicate=IrisAdapter(store).import_batch(fixtures())
        context=MemoryView(store).retrieve('paper garden',identity_id=store.identity['identity_id'],dataset_ids=DATASETS,max_chars=8000)
        # Existing ModelPort request and FixtureModel; memory context is an explicit
        # supplied input object, not injected charter or invented observed text.
        observation=Observation(source_namespace='synthetic.iris.rehearsal',object_id='post-restart-reading',
            raw_text='Prepare a synthetic evidence-backed reading card.',source_id='source://synthetic/rehearsal',
            card_resource='notebook://synthetic/rehearsal',occurred_at='2026-10-01T00:00:00Z')
        event_id=store.ingest(observation)
        request,_=ContextBuilder(store).build(event_id)
        model=MemoryDecisionFixture(context)
        proposal=model.propose(request)
        with store.transaction('decision.memory_preview',{'context':context,'proposal':proposal.model_dump(),
            'model':model.descriptor,'used_memory_ids':model.used_memory_ids,'acceptance':'NOT_ACCEPTED_NO_ACTION'}) as tx:pass
        before=store.snapshot()
        shadow=shadow_compare(store,'paper garden',DATASETS,('m1','m2'))
        assert store.snapshot()==before
        replay=Path(path).with_name('replay.db');store.replay(replay)
        with Store(replay,ManualClock()) as restored:
            expected=json.loads(canonical(before))
            for row in expected['core_meta']:
                if row['key']=='recovery_quarantine':row['value_json']='true'
            replay_equal=restored.snapshot()==expected
        entries=MemoryView(store).entries(DATASETS)
        relation=next(e for e in entries if e['iris']['relation'])
        source_ids={e['iris']['legacy_fields'].get('id') for e in entries}
        relation_resolved=all(n in source_ids for n in (relation['iris']['relation']['subject'],relation['iris']['relation']['object']))
        return {'pid':os.getpid(),'identity':store.identity,'manifest':duplicate,'count':len(entries),'context':context,
            'shadow':shadow,'replay_equal':replay_equal,'relation_count':sum(e['iris']['relation'] is not None for e in entries),
            'relation_resolved':relation_resolved,'source_payloads_equal':all(IrisAdapter(store).importer.supplied_source(r['event_id'])['payload']==record.raw_json
                for r,record in zip(duplicate['results'],fixtures())),
            'event_hashes':[digest(e) for e in store.all('events')],
            'claims':[e['belief'] for e in entries if e['belief']],
            'actions':len(store.all('actions')),'grants':len(store.all('grants')),'strategies':len(store.all('strategies')),
            'goals':len(store.all('goals')),'budget_rows':len(store.all('budgets')),'proposal':proposal.model_dump(),
            'used_memory_ids':model.used_memory_ids,
            'source_times':[e['iris']['time'] for e in entries]}


def run(output):
    root=Path(output);root.mkdir(parents=True,exist_ok=False)
    env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':str(Path(__file__).resolve().parents[2])}
    results=[]
    for phase in ('import','restart'):
        proc=subprocess.run([sys.executable,'-m','nana_core.phase3.memory_rehearsal','--session',phase,'--output',str(root/'core.db')],
            env=env,capture_output=True,text=True,timeout=30)
        if proc.returncode:raise RuntimeError('rehearsal worker failed '+str(proc.returncode))
        results.append(json.loads(proc.stdout))
    first,last=results
    checks={'counts':first['count']==last['count']==len(fixtures()),'duplicates':all(r['status']=='DUPLICATE' for r in last['manifest']['results']),
        'source_equal':last['source_payloads_equal'],'same_identity':first['identity']==last['identity'],
        'real_process_restart':first['pid']!=last['pid'],'history_prefix':last['event_hashes'][:len(first['event_hashes'])]==first['event_hashes'],
        'relation':last['relation_count']==1 and last['relation_resolved'],'replay':last['replay_equal'],
        'no_actions_or_authority':all(last[k]==0 for k in ('actions','grants','strategies','goals','budget_rows')),
        'conflict_kept':{b['current_assessment'] for b in last['claims']}=={'SUPERSEDED','CURRENT_USER_STATEMENT'},
        'contradiction_visible':last['shadow']['core']['contradictions_visible']==2,'no_unsupported_memory':last['shadow']['core']['unsupported_memory_rate']==0}
    report={'gate':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'first':first,'restarted':last,
        'fixture_count':len(fixtures()),'imported':sum(r['status']=='IMPORTED' for r in first['manifest']['results']),
        'duplicates_on_restart':sum(r['status']=='DUPLICATE' for r in last['manifest']['results']),
        'rejected':sum(r['status']=='REJECTED' for r in first['manifest']['results']),
        'claim_conflict_groups':len({b['claim_key'] for b in last['claims']}),
        'scope':'synthetic real Iris schema; deterministic decision preview; not real retrieval/model parity',
        'actual_http_calls':0,'real_model_calls':0,'E12':'NOT_RUN','production_calls':0,'fees':0}
    (root/'reconciliation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    parser.add_argument('--session',choices=['import','restart']);args=parser.parse_args()
    result=session(args.output,args.session) if args.session else run(args.output)
    print(canonical(result))
