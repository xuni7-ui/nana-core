"""Offline audit probe of existing topic scope; never repairs policy or calls a model."""
import json,tempfile
from pathlib import Path
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.world_loop.reference import open_runtime,capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.autonomy.governance import manager_views


def probe():
 with tempfile.TemporaryDirectory(prefix='nana-foundation-scope-') as directory:
  with open_runtime(Path(directory)/'self.db',VirtualClock()) as r:
   def cue(topic):
    m=MemoryService(r.store);body=ConcernCue(cue_kind='OPEN_LOOP',topic_key=topic,motivation_source='CREATIVE_INTEREST',possible_behaviors=('LEARN',)).model_dump_json()
    root=capture(r,'source-'+topic,{'issue':topic})
    eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.scope-audit',source_reference=topic,source_kind='MODEL_DERIVATION'),text=body,privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()))
    return m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='INFERENCE',source_evidence_id=eid,text=body,derived_from=(root,),predicate_key='concern.'+topic))
   def wake(key,mid):return r.subject.run(SubjectInput(source_key='synthetic.scope-audit.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(mid,),privacy_class='PUBLIC',observed_at_us=r.clock.utc_now_us()))
   mid=cue('public-topic');before=wake('before',mid)
   text='这个公开项目我暂时不想聊，别分析了。'
   signal=LiteralSpanInterpreter().interpret(text)
   r.subject.run(SubjectInput(source_key='synthetic.scope-audit.decline',kind='INTERACTION',origin='USER',entity_id='observer',scope='world',text=text,privacy_class='PUBLIC',observed_at_us=r.clock.utc_now_us(),interaction_signal=InteractionSignal(kind=signal.kind,topic_key='public-topic')))
   after=wake('after',mid);other=wake('other',cue('independent-topic'))
   out={'scope':'OFFLINE_SYNTHETIC_CURRENT_CORE_NOT_HUMAN_REVIEW','literal_kind':signal.kind,'source_privacy':'PUBLIC','before':{'behavior':before.intention.behavior,'goal_candidate':bool(before.goal_candidate_id)},'after':{'mode':after.context_fit.mode,'behavior':after.intention.behavior,'goal_candidate':bool(after.goal_candidate_id),'allow_internal_new_work':after.context_fit.allow_new_work},'other_topic_behavior':other.intention.behavior,'source_still_visible':bool(MemoryService(r.store).read(mid)),'manager_outcome_count':len(manager_views(r.store,scope='world',privacy_classes=('PUBLIC',))),'provider_call_count':len(r.store.all('cognitive_requests')),'action_count':len(r.store.all('actions')),'finding':'Conversation-depth refusal has no distinct type from same-topic internal learning pause; unrelated topics remain independent. This observation does not authorize removing privacy/refusal safeguards.'}
   assert out['before']['behavior']=='LEARN' and out['after']['mode']=='RESPECT_BOUNDARY' and not out['after']['goal_candidate']
   assert other.intention.behavior=='LEARN' and out['manager_outcome_count']==out['provider_call_count']==out['action_count']==0
   return out

if __name__=='__main__':print(json.dumps(probe(),ensure_ascii=False,indent=2))
