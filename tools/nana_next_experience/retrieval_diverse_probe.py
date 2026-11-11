"""Same32-note originalStore/G comparison; research or explicit G-qualified mode.

No production promotion or paid models.

Expected labels are frozen separately before algorithms. Experimental methods
cannot manufacture a G qualification or alter stored facts. Raw source data and
all qualification/history remain in the one original synthetic Core Store.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import time
import unicodedata
from nana_core.contracts import CoreError
from nana_core.storage import digest
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.open_agency.world import transform
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_retrieval_growth import notes, advance, selected
from tests.independent_life.test_retrieval_growth_expanded import initialize_expanded, fillers

BASELINE='8ae12dae8cd328465e6fc7808ac96e8f4494a9d1'
SPEC=Path(__file__).with_name('qualification')/'note_query_diversity_v1.json'
ARMS=('qualified_v2','research_casefold','research_words','research_join','research_nfkc')


def experimental_match(method,terms,snapshot,memory,deadline):
    """Pure bounded candidate lookup; never a lesson/eligibility assertion."""
    folded=[unicodedata.normalize('NFKC',term).casefold() for term in terms]
    result=[]
    for row in reversed(snapshot['notes']):
        if time.perf_counter()>deadline:raise CoreError('NOTE_RECALL_TIME_BOUND')
        if method=='research_casefold':
            actual=transform('CASEFOLD',row['text']);wanted=[t.casefold() for t in terms]
            matched=any(t in actual for t in wanted)
        elif method in {'research_words','research_join'}:
            words=[t.casefold() for t in transform('UNICODE_WORDS',row['text'])]
            actual=words if method=='research_words' else transform('JOIN',words)
            matched=any(t in actual for t in folded)
        elif method=='research_nfkc':
            actual=unicodedata.normalize('NFKC',row['text']).casefold()
            matched=any(t in actual for t in folded)
        else:raise ValueError('FINITE_RESEARCH_METHOD_REQUIRED')
        if matched:
            # Re-read original lifecycle/source/authority before exposing a hit.
            result.append(memory.read(row['memory_id']))
            if len(result)==4:break
    return result


def lookup(app,evaluator,method,term):
    deadline=time.perf_counter()+.1;memory=MemoryService(app.runtime.store)
    def remaining():
        value=int((deadline-time.perf_counter())*1000)
        if value<=0:raise CoreError('NOTE_RECALL_TIME_BOUND')
        return min(value,100)
    actual=memory.literal_notes(entity_ids=('project-user',),scopes=('project-work',),
        privacy_classes=('PROJECT',),terms=(term,),timeout_ms=remaining())
    gap=None
    if not actual:
        if method=='qualified_v2' and not evaluator.word_queries((term,)):
            return [],'UNSUPPORTED_QUERY_SHAPE'
        if method=='qualified_text':
            from nana_core.continuity.retrieval_growth import qualified_query_profile,QUALIFICATION_SCOPES,query_allowed
            learned=selected(app)
            if not learned:raise CoreError('NOTE_STRATEGY_SCOPE_BOUND')
            profile=qualified_query_profile(app.runtime.store,learned)
            if not query_allowed(profile,(term,)):return [],'UNSUPPORTED_QUERY_SHAPE'
            current=app.runtime.work.note_retrieval_growth.evaluator
            snapshot=current.snapshot('project-work',timeout_ms=remaining(),
                max_notes=QUALIFICATION_SCOPES[profile]['max_notes'],profile=profile)
            actual=current._normalized_lookup(learned[1],(term,),snapshot)
            remaining()
            return sorted(row['memory_id'] for row in actual),None
        snapshot=evaluator.reader.snapshot('project-work',timeout_ms=remaining(),max_notes=32)
        if method=='qualified_v2':actual=evaluator.reader._normalized_lookup('JOIN',(term,),snapshot)
        else:actual=experimental_match(method,(term,),snapshot,memory,deadline)
    remaining()
    return sorted(row['memory_id'] for row in actual),gap


def run(home,output,*,baseline=BASELINE,qualified=False):
    from types import SimpleNamespace
    if home.exists() or output.exists():raise ValueError('FRESH_SYNTHETIC_HOME_AND_OUTPUT_REQUIRED')
    spec=json.loads(SPEC.read_text());frozen_digest=digest(spec)
    assert (spec['source_bound'],spec['timeout_ms'],spec['result_limit'],spec['provider_calls'])==(32,100,4,0)
    assert all(type(c['query']) is str and 2<=len(c['query'])<=64 for c in spec['cases'])
    source=subprocess.check_output(['git','show',baseline+':src/nana_core/continuity/retrieval_growth.py'])
    baseline_path=output.with_name(output.stem+'.baseline.py')
    if baseline_path.exists():raise ValueError('FRESH_BASELINE_SNAPSHOT_REQUIRED')
    baseline_path.write_bytes(source)
    module_spec=importlib.util.spec_from_file_location('nana_core.continuity._diverse_baseline',baseline_path)
    old=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(old)
    initialize_expanded(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        train=notes(app);fillers(app,15 if qualified else 18)
        growth=app.runtime.work.note_retrieval_growth;growth.slice('project-work');advance(app)
        assert selected(app)[1]=='UNICODE_WORDS'
        notes(app,('ＡＬＰＨＡＢＥＴ','ＢＥＴＡＭＡＸ','ＧＡＭＭＡＲＡＹ'),prefix='research-counter')
        growth.slice('project-work');advance(app);assert selected(app)[1]=='JOIN'
        g_qualification='NOT_RUN'
        if qualified:
            from tests.independent_life.test_retrieval_text_profile import TRAIN
            from nana_core.continuity.retrieval_growth import qualified_query_profile
            from nana_core.continuity.subject.experience_need import project_need
            from nana_core.continuity.records import RecordService
            for index,text in enumerate(TRAIN):
                save(app,text=text,privacy='PROJECT',request_id='independent-text-training-'+str(index))
            offered=growth.slice('project-work')
            assert offered and offered['note_retrieval']=='OFFERED_TO_C'
            assert project_need(app.runtime.store,'retrieval.notes',scope='project-work',privacy_classes=('PROJECT',)).state=='OPEN'
            advance(app)
            learned=selected(app);assert learned and learned[1]=='NFKC_CASEFOLD'
            profile=qualified_query_profile(app.runtime.store,learned)
            rule=RecordService(app.runtime.store).read(learned[0])['payload']['rule']
            trial=RecordService(app.runtime.store).read(rule['trial_record_id'])['payload']
            assert all(trial['results'][stage]['all_passed'] for stage in ('EVALUATE','TRANSFER'))
            g_qualification={'state':'CONTROLLED_ORIGINAL_G_PASSED','method':learned[1],
                'profile':profile,'trial_record_id':rule['trial_record_id'],
                'evaluation':trial['results']['EVALUATE'],'transfer':trial['results']['TRANSFER']}
        source_ids={row['label']:save(app,text=row['text'],privacy='PROJECT',request_id='diverse.'+row['label'])['memory_id'] for row in spec['notes']}
        reader=old.NoteRetrievalEvaluator(app.runtime.store,'project-user',('project-work',),('PROJECT',))
        assert len(reader.snapshot('project-work',max_notes=32)['notes'])==32
        evaluator=SimpleNamespace(reader=reader,word_queries=old.word_queries)
        arms=ARMS+('qualified_text',) if qualified else ARMS
        before={mid:MemoryService(app.runtime.store).read(mid) for mid in source_ids.values()}
        results={arm:[] for arm in arms};samples={arm:[] for arm in arms}
        for index,case in enumerate(spec['cases']):
            expected=sorted(source_ids[label] for label in case['expected'])
            order=arms[index%len(arms):]+arms[:index%len(arms)]
            for arm in order:
                started=time.perf_counter_ns()
                try:actual,gap=lookup(app,evaluator,arm,case['query'])
                except CoreError as exc:
                    if exc.code not in {'NOTE_RECALL_TIME_BOUND','NOTE_STRATEGY_SCOPE_BOUND'}:raise
                    actual,gap=[],exc.code
                samples[arm].append((time.perf_counter_ns()-started)/1_000_000)
                results[arm].append({'query':case['query'],'expected':expected,'actual':actual,
                    'gap':gap,'correct':gap is None and actual==expected})
        for mid,value in before.items():
            current=MemoryService(app.runtime.store).read(mid)
            assert tuple(current[k] for k in ('assessment','confidence','text'))==tuple(value[k] for k in ('assessment','confidence','text'))
        app.forget(source_ids['cpp'])
        assert lookup(app,evaluator,'research_nfkc','C++')==([],None)
        assert lookup(app,evaluator,'research_nfkc','v1.3')[0]==[source_ids['version']]
        assert selected(app)[1]==('NFKC_CASEFOLD' if qualified else 'JOIN')  # unrelated later-source removal is not a lesson failure
        app.forget(train[0]);assert selected(app) is None
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        summaries={arm:{'queries':len(rows),'correct':sum(r['correct'] for r in rows),
            'eligible_queries':sum(r['gap'] is None for r in rows),
            'false_positive_queries':sum(bool(set(r['actual'])-set(r['expected'])) for r in rows),
            'unsupported':sum(r['gap']=='UNSUPPORTED_QUERY_SHAPE' for r in rows),
            'p50_ms':statistics.median(samples[arm]),
            'p95_ms':statistics.quantiles(samples[arm],n=100,method='inclusive')[94],
            'percentile_method':'LINEAR_INCLUSIVE'} for arm,rows in results.items()}
        result={'scope':('SYNTHETIC_ORIGINAL_C_G_QUALIFIED_LOOKUP_NOT_PRODUCTION' if qualified else 'SYNTHETIC_ORIGINAL_STORE_G_RESEARCH_NOT_RUNTIME_QUALIFICATION'),
            'baseline_source':baseline,'frozen_spec':spec,'frozen_spec_digest':frozen_digest,
            'summaries':summaries,'results':results,'latency_samples_ms':samples,
            'subject_id':app.runtime.identity_id,'source_count':32,'candidate_promoted':False,
            'candidate_g_qualification':g_qualification,'candidate_token_cost':'NOT_RUN','real_model_calls':0,
            'later_withdrawal_checked':True,'legacy_g_source_withdrawal_checked':True,'facts_unchanged':True}
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        assert all(row['correct'] for row in results['qualified_text' if qualified else 'research_nfkc']), 'FROZEN_EXPECTATIONS_NOT_MET'
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--qualified',action='store_true',help='Qualify original G on disjoint earlier text sources before adding frozen later notes')
    args=p.parse_args();result=run(args.home,args.output,qualified=args.qualified)
    print(json.dumps({'frozen_spec_digest':result['frozen_spec_digest'],'summaries':result['summaries']},indent=2))
