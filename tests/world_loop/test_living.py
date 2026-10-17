import json
from nana_core.contracts import GrantSpec,CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.open_agency.service import OpenGoalPolicy
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.extension import SelfExtensionWork
from nana_core.continuity.memory import MemoryService
from .helpers import *

def configure(r,tmp_path,transport,resources):
    p=OfflineEffectPort(r.identity_id,tmp_path/'world'/'state.fixture.json')
    GovernanceController(r.store,r.authority).initialize(r.authority)
    r.work.configure_open_agency(OpenGoalPolicy((),dynamic_resources=resources),p)
    r.work.configure_world(transport,policy(),resources=resources,skill_development=SelfExtensionWork(r))
    kernel=r.work.agency.realization.kernel;now=r.clock.utc_now_us()
    kernel.grant(GrantSpec(capabilities=tuple(kernel.capabilities)+(kernel.verify_capability,),resources=resources,not_before_us=now,expires_at_us=now+48*HOUR),r.authority)
    kernel.set_budgets({'write_attempts':100,'external_requests':500,'cost_micro_units':500},r.authority)
    p.code_skills=r.work.world.skills.codes
    return p

def test_dynamic_sourced_goals_and_two_self_detected_skill_kinds(tmp_path):
    resources=tuple('synthetic://'+name+suffix for name in ('numbers','words','arrange') for suffix in ('','/compute','/report'))
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (transport,metrics):
        p=configure(r,tmp_path,transport,resources)
        from nana_core.continuity.world_loop.ports import CognitionPlannerPort
        r.work.agency.policy.planner=CognitionPlannerPort(r.work.world.cognition)
        for name,method,data,expected in [('numbers','NUMERIC_SUM',[1.5,2],3.5),('words','CASEFOLD','HELLO','hello'),('arrange','SORT',[3,1,2],[1,2,3])]:
            resource='synthetic://'+name;p.seed_observation(resource,data)
            mid=capture(r,name,{'opportunities':[{'topic':name,'resource':resource,'method':method,'expected':expected,'value':'HIGH','domain':name,'motive':'CREATIVE_INTEREST'}]})
            r.work.world.observe(mid)
        for _ in range(120):r.clock.source.advance(SECOND);r.step()
        assert len(r.store.all('goals'))==3
        assert all(g['state']=='COMPLETED' for g in r.store.all('goals'))
        assert r.work.agency.policy.objectives and metrics['calls']>=1
        for task in ('TEXT_CLEAN','TOKEN_ANALYSIS'):
            mid=capture(r,task,{'opportunities':[{'topic':task.lower().replace('_','-'),'value':'HIGH','skill_task':task}]});r.work.world.observe(mid)
        for _ in range(100):r.clock.source.advance(SECOND);r.step()
        active=dict(r.work.world.skills.active());assert set(active)=={'TEXT_CLEAN','TOKEN_ANALYSIS'}
        for task,rid in active.items():
            service=r.work.world.skills.codes;body=service.require_current(rid)
            assert body['spec']['revision']==2 and body['tests']['isolation']=='BWRAP_NAMESPACES_READONLY_NO_NETWORK'
        assert len([x for x in r.store.all('continuity_records') if x['record_kind']=='CODE_SKILL'])>=8
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()

def test_source_backed_world_revision_replans_without_reusing_old_observation(tmp_path):
    from nana_core.continuity.world_loop.world import SourcedClaim
    resources=('synthetic://numbers','synthetic://numbers/compute','synthetic://numbers/report')
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (transport,metrics):
        p=configure(r,tmp_path,transport,resources);p.seed_observation(resources[0],[1.5,2])
        mid=capture(r,'start',{'opportunities':[{'topic':'numbers','resource':resources[0],'method':'NUMERIC_SUM','expected':3.5,'value':'HIGH','domain':'numbers','motive':'CURIOSITY'}]});r.work.world.observe(mid)
        for _ in range(24):
            r.clock.source.advance(SECOND);r.step()
            job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='GOAL'").fetchone()
            if job and job['cursor']==1:break
        assert job and job['cursor']==1;oldplan=job['record_id'];goal=r.store.all('goals')[0]
        r.clock.source.advance(SECOND);p.seed_observation(resources[0],[1,2.5])
        fact=capture(r,'world-change',{'world_claim':SourcedClaim(entity_id='device',predicate='input.revision',value='new observed values',kind='RAW_OBSERVATION',valid_from_us=r.clock.utc_now_us(),related_resources=(resources[0],)).model_dump(mode='json')});r.work.world.observe(fact)
        for _ in range(50):r.clock.source.advance(SECOND);r.step()
        goal=r.store.one('goals',goal['goal_id']);assert goal['state']=='COMPLETED'
        current=json.loads(goal['body_json'])['plan_record_id'];assert current!=oldplan
        outputs=r.work.agency._outputs(goal['goal_id']);observations=[o for o in outputs if o.get('plan_record_id')==current and o['operator_id']=='inspect']
        assert observations and json.loads(MemoryService(r.store).read(observations[0]['memory_id'])['text'])['data']==[1,2.5]


def test_transient_revisit_independent_interest_expiry_and_source_erasure(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession,StructuredProposal,InterestProposal
    from nana_core.continuity.world_loop.attention import ConcernService
    from nana_core.presence.authority import VirtualClock
    clock=VirtualClock();path=tmp_path/'s'/'self.db'
    def propose(request):
        return StructuredProposal(interpretation='A sourced unresolved question, no goal or authority',source_refs=request.source_context_refs,interests=(InterestProposal(topic='question',motivation_source='UNRESOLVED_QUESTION',source_memory_ids=(request.source_context_refs[0],),interpretation='Worth watching',possible_behaviors=('WATCH',)),))
    with fresh(path,clock) as r,provider_harness(proposer=propose) as (transport,metrics):
        session=CognitionSession(r,transport,policy());concerns=ConcernService(r,resources=('synthetic://watch',))
        first=capture(r,'question-one',{'data':'First independent observation'})
        outcome=session.execute(session.prepare('question-one','INTERPRET',(first,)))
        cid=concerns.offer(outcome['record_id'])[0]
        assert concerns.offer(outcome['record_id'])==()  # replay is not independent support
        assert r.store.one('open_concerns',cid)['state']=='TRANSIENT'
        assert concerns.opportunity() is None
        assert r.store.one('open_concerns',cid)['next_review_us']>clock.utc_now_us()
        second=capture(r,'question-two',{'data':'Second independent observation'})
        outcome=session.execute(session.prepare('question-two','INTERPRET',(second,)))
        assert concerns.offer(outcome['record_id'])==(cid,)
        assert r.store.one('open_concerns',cid)['state']=='INTEREST'
        assert concerns.opportunity().input.origin=='SELF_WAKE'
        assert not r.store.all('goals') and not r.store.all('subject_goal_candidates')
        MemoryService(r.store,r.authority).forget(first,r.authority)
        assert concerns.view()==()  # no stale independent projection after erasure
    # A fresh surviving concern can expire across a true Store close/reopen.
    # Use a different topic in a fresh sourced response, never edit history or
    # revive the old topic whose support was deleted.
    def transport_proposer(req):
        return StructuredProposal(interpretation='New question',source_refs=req.source_context_refs,interests=(InterestProposal(topic='expires',motivation_source='UNRESOLVED_QUESTION',source_memory_ids=(req.source_context_refs[0],),interpretation='Transient question'),))
    with fresh(path,clock) as r,provider_harness(proposer=transport_proposer) as (transport,metrics):
        source=capture(r,'expires',{'data':'Transient public input'})
        session=CognitionSession(r,transport,policy());out=session.execute(session.prepare('expires','INTERPRET',(source,)))
        cid=ConcernService(r,resources=('synthetic://watch',)).offer(out['record_id'])[0]
    clock.advance(3*24*HOUR+SECOND)
    with fresh(path,clock) as r:
        assert ConcernService(r,resources=('synthetic://watch',)).opportunity() is None
        assert r.store.one('open_concerns',cid)['state']=='EXPIRED'
        assert not r.store.all('goals')


def test_deleted_concern_history_does_not_exhaust_hot_attention_capacity(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession,StructuredProposal,InterestProposal
    from nana_core.continuity.world_loop.attention import ConcernService
    topic=['first']
    def propose(req):
        return StructuredProposal(interpretation='Independent concern',source_refs=req.source_context_refs,interests=(InterestProposal(topic=topic[0],motivation_source='CURIOSITY',source_memory_ids=(req.source_context_refs[0],),interpretation='Public concern',expected_value='HIGH'),))
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness(proposer=propose) as (transport,metrics):
        session=CognitionSession(r,transport,policy());concerns=ConcernService(r,resources=('synthetic://watch',),max_hot=1)
        source=capture(r,'old-interest',{'data':'Public old interest'})
        old=concerns.offer(session.execute(session.prepare('old-interest','INTERPRET',(source,)))['record_id'])[0]
        MemoryService(r.store,r.authority).forget(source,r.authority)
        topic[0]='new';source=capture(r,'new-interest',{'data':'Public new interest'})
        accepted=concerns.offer(session.execute(session.prepare('new-interest','INTERPRET',(source,)))['record_id'])
        assert len(accepted)==1 and accepted[0]!=old
        assert len(concerns.view())==1 and concerns.view()[0]['topic']=='new'
        assert r.store.one('open_concerns',old)  # erased source cannot return; opaque history remains
