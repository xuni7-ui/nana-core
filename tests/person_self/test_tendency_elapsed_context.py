"""Core time informs original private tendency use; no automatic decay or expiry."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import HOUR
from nana_core.storage import canonical
from nana_core.continuity.autonomy import private_intent
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import form,current,render


@pytest.mark.parametrize('enduring',[False,True])
def test_core_elapsed_time_changes_situational_use_without_erasing_enduring_interest(tmp_path,monkeypatch,enduring):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    private='SYNTHETIC_LONG_LIVED_INTEREST_CANARY' if enduring else 'SYNTHETIC_BRIEF_FEELING_CANARY'
    def meaning(request):
        own=[json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks']
            if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
        seen.append(own)
        # Fixture preferences, not Core constants: a continuing interest may
        # still matter, whereas a brief reaction can stop shaping this chat.
        relevant=[v for v in own if enduring or v.get('elapsed_since_update_us',0)<HOUR]
        return {'communication_proposal':{'approach':'LISTEN' if relevant else 'CHAT','detail':'BRIEF','follow_up':'NONE',
            'basis_private_record_ids':[v['record_id'] for v in relevant]}}
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();form(app,text=private);rid,item=current(app)[0];identity=app.runtime.identity_id;root=item.source_memory_ids[0]
            before=dict(app.runtime.store.one('continuity_records',rid));events=len(app.runtime.store.all('events'))
            projection=private_intent.internal_projection(app.runtime.store,(rid,),scope='project-work',privacy_classes=('PROJECT',))
            assert len(app.runtime.store.all('events'))==events
            wall=clock.now_us;clock.now_us-=HOUR  # explicit wall rollback, not a negative lived interval
            try:
                assert private_intent.internal_projection(app.runtime.store,(rid,),scope='project-work',privacy_classes=('PROJECT',))[0]['elapsed_since_update_us']==0
            finally:clock.now_us=wall
            fresh=app.chat('SYNTHETIC ordinary followup',topic='own-concern',privacy='PROJECT',message_id='fresh')
            assert fresh['text']=='SYNTHETIC: stay with the topic without pressing for details.'
        clock.advance(49*HOUR)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity
            later=app.chat('SYNTHETIC ordinary followup',topic='own-concern',privacy='PROJECT',message_id='later')
            print(json.dumps({'enduring':enduring,'later':later['text'],'age':seen[-1][0].get('elapsed_since_update_us'),
                'projection_bytes':len(canonical(seen[-1][0]).encode()),'calls':len(requests)}))
            assert later['text']==('SYNTHETIC: stay with the topic without pressing for details.' if enduring else 'SYNTHETIC: ordinary brief chat.')
            assert seen[-1][0]['elapsed_since_update_us']==49*HOUR and projection[0]['elapsed_since_update_us']==0
            assert dict(app.runtime.store.one('continuity_records',rid))==before
            assert current(app)[0][1].activity_state=='ACTIVE'
            base=private_intent.internal_projection
            def without_elapsed(*args,**kwargs):
                return tuple({k:v for k,v in row.items() if k!='elapsed_since_update_us'} for row in base(*args,**kwargs))
            with monkeypatch.context() as off:
                off.setattr(private_intent,'internal_projection',without_elapsed)
                ablated=app.chat('SYNTHETIC ordinary followup',topic='own-concern',privacy='PROJECT',message_id='ablated')
            assert ablated['text']=='SYNTHETIC: stay with the topic without pressing for details.'
            app.forget(root)
            withdrawn=app.chat('SYNTHETIC ordinary followup',topic='own-concern',privacy='PROJECT',message_id='withdrawn')
            assert withdrawn['text']=='SYNTHETIC: ordinary brief chat.'
            assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions')
            assert len(requests)==8 and all(q['budget']==requests[0]['budget'] for q in requests)
            assert all(private not in q['context_json'] for q in requests if q['cognitive_role']=='SOCIAL')
            assert all(private not in value['text'] for value in (fresh,later,ablated,withdrawn))
