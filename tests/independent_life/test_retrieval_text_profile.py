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
