"""New query-shape qualification through original C/G, never an old-scope upgrade."""
import json
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.retrieval_growth import case_for
from nana_core.continuity.subject.experience_need import project_need
from nana_core.continuity.open_agency.learning import LearningProblem
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.presence.authority import VirtualClock
from .conftest import initialize
from .test_retrieval_growth import advance, selected
from .test_retrieval_growth_expanded import initialize_expanded, fillers
from .test_dialogue import relay
from .test_note_recall import supplied_notes, render_from_supplied_sources

SCOPE='project-work'
TRAIN=('SYNTHETIC ＭＩＳＴ  ＧＡＲＤＥＮ','SYNTHETIC ＯＲＢＩＴ  ＭＵＳＩＣ','SYNTHETIC ＣＥＤＡＲ  ＰＩＣＮＩＣ')
FROZEN=Path(__file__).resolve().parents[2]/'tools/nana_next_experience/qualification/note_query_diversity_v1.json'


@pytest.mark.parametrize('boundary', ['resume', 'paused', 'dropped', 'expired', 'withdrawn'])
def test_retained_c_learning_choice_recovers_after_host_lacked_spec(tmp_path, boundary):
    home=tmp_path/'home';clock=VirtualClock();initialize(home,active=0)
    with LifeApplication(home,clock=clock) as app:
        mids=[save(app,text=text,privacy='PROJECT',request_id='missing-spec-'+str(i))['memory_id']
              for i,text in enumerate(TRAIN)]
        r=app.runtime;identity=r.identity_id;growth=r.work.note_retrieval_growth
        growth.slice(SCOPE);advance(app);assert selected(app)[1]=='UNICODE_WORDS'
        growth.slice(SCOPE)
        key=next(k for k,s in growth.service().specs.items() if 'NFKC_CASEFOLD' in s.hypotheses)
        growth.service().specs.pop(key)  # older host can commit C without knowing this G profile
        advance(app,12)
        choices=[]
        for intention in r.subject.pending(SCOPE):
            row=r.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=? ORDER BY revision DESC LIMIT 1',
                                  (intention['subject_event_id'],)).fetchone()
            cycle=r.subject.result(row)
            if cycle.proposed_program_id==key and cycle.intention.behavior=='LEARN':choices.append((intention,cycle))
        assert len(choices)==1
        intention,cycle=choices[0]
        assert not r.store.db.execute("SELECT 1 FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id WHERE j.work_kind='LEARNING' AND c.target_id=?",(key,)).fetchone()
        if boundary=='paused':app.pause()
        if boundary=='dropped':r.subject.transition_intention(intention['intention_id'],expected_revision=intention['revision'],state='DROPPED')
        if boundary=='expired':clock.advance(intention['expires_at_us']-r.clock.utc_now_us()+1)
        if boundary=='withdrawn':app.forget(mids[0])
        before_cycles=len(r.store.all('subject_cycles'))
    with LifeApplication(home,clock=clock) as app:
        r=app.runtime;growth=r.work.note_retrieval_growth
        assert r.identity_id==identity
        growth.slice(SCOPE)
        jobs=r.store.db.execute("SELECT j.* FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id WHERE j.work_kind='LEARNING' AND c.target_id=?",(key,)).fetchall()
        assert len(jobs)==(1 if boundary=='resume' else 0)
        assert len(r.store.all('subject_cycles'))==before_cycles  # no second judgment
        if boundary=='resume':
            assert r.store.one('subject_intentions',intention['intention_id'])['state']=='COMPLETED'
            growth.slice(SCOPE)
            assert len(r.store.all('subject_cycles'))==before_cycles
            advance(app);assert selected(app)[1]=='NFKC_CASEFOLD'
            assert len(r.store.db.execute("SELECT j.job_id FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id WHERE j.work_kind='LEARNING' AND c.target_id=?",(key,)).fetchall())==1
        assert not r.store.all('cognitive_requests') and not r.store.all('actions')


@pytest.mark.parametrize('capacity',[16,32])
def test_original_g_text_qualification_restores_and_reuses_on_unseen_sources_and_model(tmp_path,capacity):
    home=tmp_path/'home';clock=VirtualClock()
    if capacity==32:initialize_expanded(home)
    else:initialize(home,active=0)
    with LifeApplication(home,clock=clock) as app:
        train=[save(app,text=text,privacy='PROJECT',request_id='text-training-'+str(i))['memory_id'] for i,text in enumerate(TRAIN)]
        fillers(app,capacity-11)  # training+fillers+8 genuinely later sources == original capacity
        growth=app.runtime.work.note_retrieval_growth
        assert growth.slice(SCOPE)['note_retrieval']=='OFFERED_TO_C'
        advance(app);assert selected(app)[1]=='UNICODE_WORDS'  # old qualification still first
        old_word_lesson=selected(app)
        old_rule=RecordService(app.runtime.store).read(selected(app)[0])['payload']['rule']
        old_trial=RecordService(app.runtime.store).read(old_rule['trial_record_id'])['payload']
        assert old_trial['results']['EVALUATE']['evaluator']==('CORE_NOTE_RETRIEVAL_V2' if capacity==32 else 'CORE_NOTE_RETRIEVAL_V1')
        offered=growth.slice(SCOPE)
        assert offered and offered['note_retrieval']=='OFFERED_TO_C', 'Text-shaped capability gap needs its own C-reviewed study'
        identity=app.runtime.identity_id
        assert not app.runtime.store.all('cognitive_requests')
    # Restore pending text-profile spec before original C has adopted it.
    with LifeApplication(home,clock=clock) as app:
        assert app.runtime.identity_id==identity;advance(app)
        lesson=selected(app)
        assert lesson and lesson[1]=='NFKC_CASEFOLD'
        records=RecordService(app.runtime.store);rule=records.read(lesson[0])['payload']['rule']
        trial=records.read(rule['trial_record_id'])['payload']
        for stage in ('EVALUATE','TRANSFER'):
            result=trial['results'][stage]
            assert result['evaluator']=='CORE_NOTE_RETRIEVAL_TEXT_V1_'+str(capacity)
            assert result['qualification_scope']['query_shape']=='TEXT_2_64'
            assert result['qualification_scope']['max_notes']==capacity and result['all_passed']
        specs=[spec for spec in app.runtime.work.note_retrieval_growth.service().specs.values()
            if spec.domain=='retrieval.notes' and any(c.data.get('kind','').startswith('CORE_NOTE_RETRIEVAL_TEXT_') for c in spec.practice)]
        assert len(specs)==1
        problem=LearningProblem.from_spec(specs[0]).model_dump()
        assert set(problem)=={'learning_key','domain','baseline_method','hypotheses','practice'}
        assert not ({json.dumps(c.data,sort_keys=True) for c in specs[0].evaluation+specs[0].transfer}
                    & {json.dumps(c['data'],sort_keys=True) for c in problem['practice']})
        # A new literal-only source must not manufacture learned-method reuse.
        assessments=len(app.runtime.store.all('strategy_assessments'))
        literal=save(app,text='ordinary plain source for literal-only control',privacy='PROJECT',request_id='literal-control')['memory_id']
        app.runtime.work.note_retrieval_growth.slice(SCOPE)
        assert len(app.runtime.store.all('strategy_assessments'))==assessments
        assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state=='OPEN'
        app.forget(literal)
        assert selected(app)[1]=='NFKC_CASEFOLD'
        spec=json.loads(FROZEN.read_text())
        later={n['label']:save(app,text=n['text'],privacy='PROJECT',request_id='unseen-text-'+n['label'])['memory_id'] for n in spec['notes']}
        evaluator=app.runtime.work.note_retrieval_growth.evaluator
        from nana_core.continuity.retrieval_growth import qualified_query_profile
        profile=qualified_query_profile(app.runtime.store,lesson)
        with pytest.raises(CoreError,match='NOTE_STRATEGY_SCOPE_BOUND'):
            evaluator.snapshot(SCOPE,max_notes=32 if capacity==16 else 16,profile=profile)
        for case in spec['cases']:
            snapshot=evaluator.snapshot(SCOPE,max_notes=capacity,profile=profile)
            actual=sorted(n['memory_id'] for n in evaluator.lookup(lesson[1],(case['query'],),snapshot))
            assert actual==sorted(later[label] for label in case['expected']),case
        before={mid:MemoryService(app.runtime.store).read(mid) for mid in later.values()}
        before_jobs=len(app.runtime.store.all('jobs'))
        for _ in range(4):app.runtime.work.note_retrieval_growth.slice(SCOPE)
        assert len(app.runtime.store.all('jobs'))==before_jobs
        assert len(app.runtime.store.all('strategy_assessments'))==assessments+1
        assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state=='SETTLED'
        # An actual failure of a different earlier lesson must not reopen the
        # now independently settled text gap merely because the domain matches.
        legacy_snapshot=evaluator.snapshot(SCOPE,max_notes=capacity)
        aid=app.runtime.work.note_retrieval_growth.assess(old_word_lesson,legacy_snapshot,('MI',),'other-word-counterexample')
        assert app.runtime.store.one('strategy_assessments',aid)['verdict']=='COUNTEREXAMPLE'
        assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state=='SETTLED'
    with relay(home,'CHAT',renderer=render_from_supplied_sources,remote_model_id='text-profile-unseen-resource',
               recall_query_terms=('C++',)) as (router,calls):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity and selected(app)[1]=='NFKC_CASEFOLD'
            app.chat('SYNTHETIC later symbolic lookup',privacy='PROJECT',message_id='text-later')
            assert [n['memory_id'] for n in supplied_notes(calls[-1])]==[later['cpp']]
            for mid,value in before.items():
                now=MemoryService(app.runtime.store).read(mid)
                assert tuple(now[k] for k in ('text','assessment','confidence'))==tuple(value[k] for k in ('text','assessment','confidence'))
            app.forget(train[0]);assert selected(app) is None
            assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state!='SETTLED'
            app.chat('SYNTHETIC source-withdrawn skill lookup',privacy='PROJECT',message_id='text-withdrawn')
            assert supplied_notes(calls[-1])==[] and len(calls)==4
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_old_wordlike_trial_cannot_certify_new_method_or_query_shape(tmp_path):
    home=tmp_path/'home';initialize(home,active=0)
    with LifeApplication(home,clock=VirtualClock()) as app:
        for i,text in enumerate(TRAIN):save(app,text=text,privacy='PROJECT',request_id='old-profile-'+str(i))
        evaluator=app.runtime.work.note_retrieval_growth.evaluator
        snapshot=evaluator.snapshot(SCOPE)
        with pytest.raises(CoreError,match='NOTE_STRATEGY_INPUT_BOUND'):
            evaluator.evaluate('NFKC_CASEFOLD',(case_for(snapshot,('MIST',),'legacy-method'),))
        with pytest.raises(CoreError,match='NOTE_STRATEGY_INPUT_BOUND'):
            evaluator.evaluate('JOIN',(case_for(snapshot,('mist  garden',),'legacy-shape'),))
        assert not app.runtime.store.all('lessons') and not app.runtime.store.all('cognitive_requests')


def test_new_text_gap_is_not_settled_by_earlier_wordlike_reuse_at_the_same_clock(tmp_path):
    from .test_retrieval_growth import notes as legacy_notes
    home=tmp_path/'home';initialize_expanded(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        legacy_notes(app);fillers(app,15)
        growth=app.runtime.work.note_retrieval_growth
        growth.slice(SCOPE);advance(app);assert selected(app)[1]=='UNICODE_WORDS'
        legacy_notes(app,('ＡＬＰＨＡＢＥＴ','ＢＥＴＡＭＡＸ','ＧＡＭＭＡＲＡＹ'),prefix='same-clock-prefix')
        growth.slice(SCOPE);advance(app);assert selected(app)[1]=='JOIN'
        old_word_method=selected(app)
        for i,text in enumerate(TRAIN):save(app,text=text,privacy='PROJECT',request_id='same-clock-text-'+str(i))
        # One maintenance slice can verify the old word method and then observe
        # a distinct text-shape failure. Equal timestamps do not connect causes.
        offered=growth.slice(SCOPE)
        assert offered and offered['note_retrieval']=='OFFERED_TO_C'
        need=project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',))
        assert need.state=='OPEN',need.model_dump()
        # Merely changing >= to > would still falsely settle the new gap when
        # a successful old-method episode happens later. Check that case too.
        app.runtime.clock.source.advance(1_000_000)
        snapshot=growth.evaluator.snapshot(SCOPE,max_notes=32)
        growth.assess(old_word_method,snapshot,('MIST',),'old-word-reuse-after-new-text-gap')
        assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state=='OPEN'
        advance(app)
        assert selected(app)[1]=='NFKC_CASEFOLD'
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions')


def test_existing_method_can_settle_a_new_gap_when_independent_proof_descends_from_that_gap(tmp_path):
    from nana_core.storage import canonical
    from nana_core.continuity.world_loop.learning import EpisodeLearning
    from nana_core.continuity.retrieval_growth import qualified_query_profile
    home=tmp_path/'home';initialize(home,active=0)
    with LifeApplication(home,clock=VirtualClock()) as app:
        for i,text in enumerate(TRAIN):save(app,text=text,privacy='PROJECT',request_id='transfer-training-'+str(i))
        growth=app.runtime.work.note_retrieval_growth
        growth.slice(SCOPE);advance(app);growth.slice(SCOPE);advance(app)
        learned=selected(app);assert learned[1]=='NFKC_CASEFOLD'
        lesson=app.runtime.store.db.execute('SELECT lesson_id FROM lessons WHERE record_id=?',(learned[0],)).fetchone()[0]
        save(app,text='SYNTHETIC Ｃ＋＋ later application',privacy='PROJECT',request_id='transfer-current-gap')
        snapshot=growth.evaluator.snapshot(SCOPE,profile=qualified_query_profile(app.runtime.store,learned))
        _,result,_=growth.experience(snapshot,('C++',),'IDENTITY','new-gap-with-known-method')
        assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state=='OPEN'
        lesson_count=len(app.runtime.store.all('lessons'))
        case=case_for(snapshot,('C++',),'actual-application-to-new-gap')
        proof=growth.capture('explicit-known-method-reuse',canonical({'strategy_episode':{
            'episode_key':'known-method-fixes-this-new-gap','lesson_id':lesson,'case':case.model_dump(mode='json')}}),
            SCOPE,(result,))
        aid=EpisodeLearning(app.runtime.store,app.runtime.authority,scopes=(SCOPE,),privacy_classes=('PROJECT',),
            evaluator=growth.evaluator).assess(lesson,proof,authority=app.runtime.authority)
        assert app.runtime.store.one('strategy_assessments',aid)['verdict']=='SUCCESS'
        assert project_need(app.runtime.store,'retrieval.notes',scope=SCOPE,privacy_classes=('PROJECT',)).state=='SETTLED'
        assert len(app.runtime.store.all('lessons'))==lesson_count  # transfer, without another study
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions')
