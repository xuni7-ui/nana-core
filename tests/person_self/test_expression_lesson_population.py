"""An originally proposed G candidate can qualify later than another evidence family."""
import json
import pytest
from nana_core.continuity.lived_language import LanguageService,learnable,expression_policy
from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.records import RecordService
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_learning import sample,record,activate


@pytest.mark.parametrize('newer_lessons',[0,16])
def test_later_qualified_original_candidate_reaches_normal_dialogue_without_population_crowding(tmp_path,newer_lessons):
    home=tmp_path/'home';initialize(home);seen=[]
    def render(request):
        blocks=json.loads(request['context_json'])['blocks']
        policies=[json.loads(b['data_json'])['policy'] for b in blocks if b['kind']=='LIVED_LANGUAGE']
        seen.append(policies)
        selected=bool(policies and policies[0].get('evidence_level')=='USER_PROVIDED_REVIEW')
        return 'SYNTHETIC qualified human method available' if selected else 'SYNTHETIC baseline without human method'
    with relay(home,'CHAT',renderer=render,context_limit=65536) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();r=app.runtime;language=LanguageService(r.store,r.authority);g=ExperienceService(r.store,r.authority)
        proposal=sample(app,'early-partial',provenance='USER_PROVIDED_REVIEW').model_copy(update={'human_judgment':'PARTIAL'})
        source_record=language.record(proposal,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=r.authority)
        eid=language.experience(source_record,r.authority);lid=g.derive_lesson(eid)
        assert r.store.one('lessons',lid)['state']=='CANDIDATE'
        assert not learnable(r.store,'project-work',('PROJECT',))['eligible']
        other=[]
        for n in range(newer_lessons+1):
            _,synthetic_eid=record(app,100+n)
            if n:other.append(activate(app,synthetic_eid))
        # These later, independent reports are not the proposal's own sample.
        record(app,'later-human-a',provenance='USER_PROVIDED_REVIEW')
        record(app,'later-human-b',provenance='USER_PROVIDED_REVIEW')
        assert all(g.test_lesson(lid).values());g.activate(lid,r.authority)
        qualification=learnable(r.store,'project-work',('PROJECT',))
        assert qualification['eligible'] and qualification['evidence_level']=='USER_PROVIDED_REVIEW'
        assert RecordService(r.store).current_support(r.store.one('lessons',lid)['record_id'])
        positions={row['lesson_id']:row['pos'] for row in r.store.db.execute('SELECT rowid AS pos,lesson_id FROM lessons')}
        assert all(positions[other_lid]>positions[lid] for other_lid in other)
        identity=r.identity_id;clock=app.clock;app.close()
        with LifeApplication(home,clock=clock,router=router) as restored:
            restored.pause();r=restored.runtime;assert r.identity_id==identity
            writes=r.store.db.total_changes
            selected=expression_policy(r.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
            assert r.store.db.total_changes==writes
            answer=restored.chat('SYNTHETIC a new casual topic after delayed qualification',privacy='PROJECT',message_id='after-late-qualification')
            print(json.dumps({'measurement':'delayed-expression-population','newer_other_family_lessons':newer_lessons,
                'original_lesson_active':r.store.one('lessons',lid)['state']=='ACTIVE',
                'selected_original_lesson':selected.get('lesson_id')==lid,'answer':answer['text'],
                'roles':[request['cognitive_role'] for request in requests],'http_calls':len(requests),
                'request_json_bytes':[len(json.dumps(request,separators=(',',':'),ensure_ascii=False).encode()) for request in requests],
                'real_model_calls':0}))
            assert selected.get('lesson_id')==lid
            assert answer['text']=='SYNTHETIC qualified human method available'
            assert len(requests)==2 and [request['cognitive_role'] for request in requests]==['INTERPRET','SOCIAL']
            source_memory=next(mid for mid in RecordService(r.store).support(source_record)
                if r.store.one('continuity_evidence',r.store.one('memories',mid)['source_evidence_id'])['source_namespace']=='recorded.conversation.feedback')
            restored.forget(source_memory)
            assert learnable(r.store,'project-work',('PROJECT',))['eligible']
            assert expression_policy(r.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule'] is None
            answer=restored.chat('SYNTHETIC another topic after source withdrawal',privacy='PROJECT',message_id='after-method-withdrawal')
            assert answer['text']=='SYNTHETIC baseline without human method' and len(requests)==4
            assert not r.store.all('actions') and not r.store.all('grants')
