"""Sourced media observations → interpretation candidates → ordinary C events."""
import json
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import canonical,digest
from ..providers import MediaProposal,MediaSession
from ..records import RecordService
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..subject.opportunities import ConcernCue

class ContentItem(DTO):
    content_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    media_type: Literal['TEXT','VIDEO','AUDIO','IMAGE']
    topic: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    learning_key: str | None = Field(default=None,pattern=r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$')
    source_reference: str = Field(min_length=1,max_length=128)
    occurred_at_us: int = Field(ge=0)
    credibility: Literal['UNVERIFIED','SOURCE_IDENTIFIED','INDEPENDENTLY_CHECKED'] = 'UNVERIFIED'
    privacy_class: Literal['PUBLIC','PROJECT','PERSONAL','SECRET']
class ContentFeed(DTO):
    kind: Literal['CONTENT_FEED'] = 'CONTENT_FEED'
    items: tuple[ContentItem,...] = Field(max_length=16)
class InterestCandidate(DTO):
    topic: str
    learning_key: str
    source_content_id: str
class InterestCandidates(DTO):
    candidates: tuple[InterestCandidate,...] = Field(max_length=16)

class FixtureContentUnderstandingPort:
    """A deterministic metadata fixture, not video semantic-quality qualification."""
    def understand_video(self,request):
        candidates=[]
        for entry in json.loads(request.content_json):
            body=json.loads(entry['content']);feed=ContentFeed.model_validate_json(canonical(body['data']))
            for item in feed.items:
                if item.learning_key and item.privacy_class!='SECRET':candidates.append(InterestCandidate(topic=item.topic,learning_key=item.learning_key,source_content_id=item.content_id))
        return MediaProposal(operation='VIDEO_UNDERSTAND',source_memory_ids=request.source_memory_ids,result_json=canonical(InterestCandidates(candidates=tuple(candidates)).model_dump(mode='json')))

class ExplorationService:
    def __init__(self,store,providers,policy,model_id,learning_keys):
        self.store,self.records=store,RecordService(store);self.session=MediaSession(store,providers,policy);self.model_id=model_id;self.keys=frozenset(learning_keys)
        self.privacy=policy.readable_privacy
    def observe(self,runtime,memory_id):
        memory=self.records.memory.read(memory_id)
        if memory['privacy_class'] not in self.privacy:raise CoreError('CONTENT_PRIVACY_DENIED')
        try:feed=ContentFeed.model_validate_json(canonical(json.loads(memory['text'])['data']))
        except (ValueError,KeyError,TypeError):return ()
        now=self.store.clock.utc_now_us()
        if any(i.privacy_class not in self.privacy or i.occurred_at_us>now for i in feed.items):raise CoreError('CONTENT_PRIVACY_OR_TIME_DENIED')
        key=digest([memory_id,self.model_id]);old=self.store.db.execute("SELECT 1 FROM continuity_records WHERE record_kind='WORLD_OBSERVATION' AND target_id=?",(key,)).fetchone()
        if old:return ()
        proposal=self.session.understand_video(self.model_id,(memory_id,),scopes=(memory['scope'],))
        candidates=InterestCandidates.model_validate_json(proposal.result_json);inputs={i.content_id:i for i in feed.items};mids=[]
        for idea in candidates.candidates:
            item=inputs.get(idea.source_content_id)
            if not item or idea.topic!=item.topic or idea.learning_key!=item.learning_key or idea.learning_key not in self.keys:raise CoreError('CONTENT_CANDIDATE_SOURCE_MISMATCH')
            cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CREATIVE_INTEREST',topic_key=idea.topic,program_id=idea.learning_key,possible_behaviors=('LEARN','WATCH'))
            source=self.records.memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.media-interpretation',source_reference=digest([memory_id,idea.model_dump(mode='json')]),source_kind='MODEL_DERIVATION'),text=cue.model_dump_json(),privacy_class=memory['privacy_class'],observed_time_us=memory['observed_time_us']))
            existing=self.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=? LIMIT 1',(source,)).fetchone()
            mid=existing[0] if existing else self.records.memory.add(MemoryCandidate(entity_id=memory['entity_id'],scope=memory['scope'],memory_type=MemoryType.PROSPECTIVE,epistemic_kind='INFERENCE',source_evidence_id=source,text=cue.model_dump_json(),derived_from=(memory_id,),predicate_key='concern.'+idea.topic,confidence=.4))
            mids.append(mid)
            from ..subject.contracts import SubjectInput
            from ...presence.contracts import RuntimeEvent,Cause
            inp=SubjectInput(source_key='synthetic.open.interest.'+digest(mid),kind='WAKE',origin='SELF_WAKE',entity_id=memory['entity_id'],scope=memory['scope'],source_memory_ids=(mid,),observed_at_us=self.records.memory.read(mid)['observed_time_us'],novelty='RELEVANT')
            runtime.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=now,priority=1))
        with self.store.transaction('open.content_interpreted',{'source_memory_id':memory_id,'candidate_count':len(mids)}) as tx:
            self.records.create(tx,kind='WORLD_OBSERVATION',scope=memory['scope'],payload={'source_memory_id':memory_id,'candidate_memory_ids':mids,'proposal_not_truth':True,'provider':self.model_id},memories=(memory_id,*mids),target_id=key)
        return tuple(mids)
