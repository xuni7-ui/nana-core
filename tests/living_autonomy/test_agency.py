from nana_core.actions import ActionKernel
from nana_core.contracts import GrantSpec
from nana_core.continuity.agency import OfflineGoalPolicy
from nana_core.continuity.agency_contracts import OfflineProgram
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.contracts import SECOND,Cause
from .helpers import fresh,event


def setup(r,path,*,allow=True):
    port=OfflineEffectPort(r.store.identity['identity_id'],path)
    port.seed_source('synthetic://source/document',text='Fictional verified source',locator='section:2')
    p=OfflineProgram(program_id='fixture.reading',scope='lab',motivation_source='PROJECT_COMPLETION',source_resource='synthetic://source/document',output_resource='synthetic://card/one')
    GovernanceController(r.store,r.authority).initialize(r.authority)
    r.work.configure_agency(OfflineGoalPolicy((p,)),port)
    if allow:
        kernel=r.work.agency.realization.kernel;now=r.clock.utc_now_us()
        kernel.grant(GrantSpec(capabilities=('reading.source.read','reading.source.locate','reading.card.create','reading.action.verify'),resources=(p.source_resource,p.output_resource),not_before_us=now,expires_at_us=now+100*SECOND),r.authority)
        kernel.set_budgets({'write_attempts':8,'external_requests':40,'cost_micro_units':40},r.authority)
    cue=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='PROJECT_COMPLETION',topic_key='reading-project',program_id=p.program_id)
    m=MemoryService(r.store)
    e=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.living-project',source_reference='one',source_kind='DIRECT_OBSERVATION'),text=cue.model_dump_json(),observed_time_us=r.clock.utc_now_us(),privacy_class='PERSONAL'))
    mid=m.add(MemoryCandidate(entity_id='synthetic-person',scope='lab',memory_type=MemoryType.PROJECT,epistemic_kind='OBSERVATION',source_evidence_id=e,text=cue.model_dump_json(),predicate_key='concern.reading-project'))
    return p,mid


def start(r,mid):
    r.submit(event(r,'self-project',background=True,source_memory_ids=(mid,)))
    return r.step()

def test_no_input_goal_adoption_steps_verified_outcome_and_restart(tmp_path):
    path=tmp_path/'subject'/'self.db';world=tmp_path/'world'/'project.fixture.json'
    with fresh(path) as r:
        p,mid=setup(r,world);result=start(r,mid)
        assert result['cycle'].intention.self_generated
        assert r.store.all('goals')[0]['state']=='ACTIVE'
        r.step() # first verified read
        assert len(r.store.all('actions'))==1
        identity=r.store.identity['identity_id'];clock=r.clock.source
    from nana_core.presence import NanaRuntime
    from nana_core.presence.contracts import RuntimeConfig,LivingRuntimeConfig
    clock.advance(SECOND)
    with NanaRuntime(path,RuntimeConfig(schema_target=11,living=LivingRuntimeConfig(),scopes=('lab',),entity_id='synthetic-person'),clock=clock) as r:
        r.work.configure_agency(OfflineGoalPolicy((p,)),OfflineEffectPort(identity,world))
        r.step()
        assert r.store.identity['identity_id']==identity
        assert r.store.all('goals')[0]['state']=='FAILED' # actual card verified, missing locator -> quality failure
        assert len(r.store.all('actions'))==2
        assert r.store.all('experiences')[0]['outcome']=='FAILURE'
        r.step();assert len(r.store.all('actions'))==2


def test_manager_and_missing_grant_remain_distinct(tmp_path):
    with fresh(tmp_path/'a'/'self.db') as r:
        p,mid=setup(r,tmp_path/'wa'/'world.fixture.json',allow=False)
        start(r,mid);r.step()
        assert r.store.all('actions')[0]['state']=='BLOCKED'
        assert not r.store.all('attempts')
    with fresh(tmp_path/'b'/'self.db') as r:
        p,mid=setup(r,tmp_path/'wb'/'world.fixture.json')
        from nana_core.continuity.autonomy.contracts import RealizationTarget
        target=RealizationTarget(capability='reading.source.read',operation='READ',resource=p.source_resource,resource_class='ORDINARY')
        gov=GovernanceController(r.store,r.authority)
        gov.install(ManagerConstraint(constraint_id='no-source',revision=1,issuer=r.authority.principal,source_reference='synthetic.review',identity_id=r.store.identity['identity_id'],scope='lab',targets=(target,),effective_from_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+100*SECOND,reason_code='NO_SOURCE'),r.authority)
        start(r,mid);result=r.step()
        assert result['cycle'].evaluation.normative=='ENDORSED'
        assert not r.store.all('actions')
        assert r.store.all('goals')[0]['state']=='BLOCKED'


def test_new_action_payloads_and_journal_cannot_resurrect_erased_source(tmp_path):
    from nana_core.continuity.memory import MemoryService
    with fresh(tmp_path/'subject'/'self.db') as r:
        _,mid=setup(r,tmp_path/'world'/'world.fixture.json')
        start(r,mid);r.step()
        assert len(r.store.all('actions'))==1
        # Synthetic world text is actually observed, never copied into immutable rows.
        assert 'Fictional verified source' not in str(r.store.all('events'))
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        assert all(not a['payload'] or b'Fictional verified source' not in a['payload'] for a in r.store.all('artifacts'))
        r.clock.source.advance(SECOND);r.step()
        assert r.store.all('goals')[0]['state']=='ABANDONED'
        assert not r.work.agency.next_reference()
