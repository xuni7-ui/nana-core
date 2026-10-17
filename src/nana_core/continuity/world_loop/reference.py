"""Reusable trusted construction for a finite public synthetic laboratory.

Only descriptors/resources/Grants are installed here. Goals are not inserted;
observations must pass proposer → Concern → existing C → adoption.
"""
from pathlib import Path
from ...actions import OperatorAuthority
from ...contracts import GrantSpec
from ...storage import canonical
from .. import ContinuityStore,IdentityService
from ..memory import MemoryService
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..context import ContextPolicy
from ..providers import ProviderRegistry,ProviderDescriptor
from ..autonomy.fixture_effects import OfflineEffectPort
from ..autonomy.governance import GovernanceController
from ..open_agency.service import OpenGoalPolicy
from ..open_agency.fixtures import numeric_learning,language_learning
from ...presence.runtime import NanaRuntime
from ...presence.contracts import RuntimeConfig,LivingRuntimeConfig,HOUR,SECOND
from ...presence.authority import VirtualClock
from .perception import DecodedMediaProcessor
from .extension import SelfExtensionWork
from .ports import CognitionPlannerPort

def context_policy():return ContextPolicy(policy_id='world-reference',allowed_scopes=('world',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'),remote_privacy=('PUBLIC',))
def codec_providers():
    p=ProviderRegistry();p.register(ProviderDescriptor(provider_id='local.codec',model_id='local.codec-v1',model_version='1',operations=('VISION','AUDIO_UNDERSTAND','VIDEO_UNDERSTAND'),input_modalities=('IMAGE','AUDIO','VIDEO'),output_modalities=('TEXT',),context_limit=65536,output_limit=16384,locality='LOCAL',permitted_privacy=('PUBLIC',)),DecodedMediaProcessor());return p

def open_runtime(path,clock,*,wall=False):
    with ContinuityStore(path,clock,schema_target=13) as s:
        IdentityService(s,OperatorAuthority())
        for e,k in [('observer','PERSON'),('friend','PERSON'),('device','OBJECT')]:MemoryService(s).entity(e,k)
    config=RuntimeConfig(schema_target=13,max_calls_per_day=64,living=LivingRuntimeConfig(max_model_bytes_per_day=16_000_000,background_fraction_percent=80,maintenance_interval_us=SECOND if wall else HOUR),scopes=('world',),entity_id='observer',privacy_classes=('PUBLIC','PROJECT','PERSONAL'),lease_us=2*HOUR,heartbeat_us=SECOND if wall else 15*60*SECOND,review_interval_us=2*SECOND if wall else HOUR,idle_recall_us=2*SECOND if wall else HOUR)
    return NanaRuntime(path,config,clock=clock)

def capture(r,key,body,*,privacy='PUBLIC',kind='DIRECT_OBSERVATION',predicate=None,event_time=None,entity='observer'):
    text=canonical(body) if not isinstance(body,str) else body;m=MemoryService(r.store);now=r.clock.utc_now_us()
    eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.world-reference',source_reference=key,source_kind=kind),text=text,privacy_class=privacy,event_time_us=now if event_time is None else event_time,observed_time_us=now))
    old=r.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(eid,)).fetchone()
    return old[0] if old else m.add(MemoryCandidate(entity_id=entity,scope='world',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION' if kind!='MODEL_DERIVATION' else 'BELIEF',source_evidence_id=eid,text=text,predicate_key=predicate,confidence=.8))

def configure(r,root,transport,resources,*,grant=True,planner=True):
    port=OfflineEffectPort(r.identity_id,Path(root)/'world'/'state.fixture.json');GovernanceController(r.store,r.authority).initialize(r.authority)
    r.work.configure_open_agency(OpenGoalPolicy((),dynamic_resources=resources),port)
    r.work.configure_open_learning((numeric_learning(),language_learning()))
    r.work.configure_world(transport,context_policy(),resources=resources,skill_development=SelfExtensionWork(r))
    if planner:r.work.agency.policy.planner=CognitionPlannerPort(r.work.world.cognition)
    port.code_skills=r.work.world.skills.codes
    if grant:
        k=r.work.agency.realization.kernel;now=r.clock.utc_now_us()
        k.grant(GrantSpec(capabilities=tuple(k.capabilities)+(k.verify_capability,),resources=tuple(resources),not_before_us=now,expires_at_us=now+48*HOUR),r.authority)
        k.set_budgets({'write_attempts':100,'external_requests':500,'cost_micro_units':500},r.authority)
    return port
