from pathlib import Path
from nana_core.actions import OperatorAuthority
from nana_core.storage import canonical
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.providers import ProviderRegistry,ProviderDescriptor
from nana_core.continuity.world_loop.perception import DecodedMediaProcessor
from nana_core.presence import NanaRuntime
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig,LivingRuntimeConfig,HOUR,SECOND

def fresh(path,clock=None):
    clock=clock or VirtualClock()
    with ContinuityStore(path,clock,schema_target=13) as s:
        IdentityService(s,OperatorAuthority());MemoryService(s).entity('observer','PERSON');MemoryService(s).entity('device','OBJECT')
    return NanaRuntime(path,RuntimeConfig(schema_target=13,max_calls_per_day=64,living=LivingRuntimeConfig(max_model_bytes_per_day=16_000_000,background_fraction_percent=80,maintenance_interval_us=SECOND),scopes=('world',),entity_id='observer',privacy_classes=('PUBLIC','PROJECT','PERSONAL'),idle_recall_us=HOUR,review_interval_us=HOUR),clock=clock)
def capture(r,key,body,*,privacy='PUBLIC',kind='DIRECT_OBSERVATION',event=None):
    memory=MemoryService(r.store);text=canonical(body)
    eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.world-test',source_reference=key,source_kind=kind),text=text,privacy_class=privacy,event_time_us=r.clock.utc_now_us() if event is None else event,observed_time_us=r.clock.utc_now_us()))
    return memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION' if kind!='MODEL_DERIVATION' else 'BELIEF',source_evidence_id=eid,text=text,confidence=.8))
def policy():return ContextPolicy(policy_id='world-development',allowed_scopes=('world',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'),remote_privacy=('PUBLIC',))
def providers():
    p=ProviderRegistry();p.register(ProviderDescriptor(provider_id='local.codec',model_id='local.codec-v1',model_version='1',operations=('VISION','AUDIO_UNDERSTAND','VIDEO_UNDERSTAND'),input_modalities=('IMAGE','AUDIO','VIDEO'),output_modalities=('TEXT',),context_limit=65536,output_limit=16384,locality='LOCAL',permitted_privacy=('PUBLIC',)),DecodedMediaProcessor());return p
