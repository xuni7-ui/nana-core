import json
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,OpenAIJSONTransport,StructuredProposal,InterestProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.continuity.subject import SubjectInput
from nana_core.presence.contracts import RuntimeEvent,Cause
from .helpers import *

def test_remote_privacy_and_model_authority_are_never_relaxed(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        mid=capture(r,'private',{'data':'synthetic personal canary'},privacy='PERSONAL')
        t=OpenAIJSONTransport('https://example.invalid/v1/chat/completions','unconfigured')
        s=CognitionSession(r,t,policy())
        with pytest.raises(CoreError,match='DENIED'):s.prepare('private','INTERPRET',(mid,),budget=CognitionBudget(cost_ceiling_micro=1000))
        assert not r.store.all('cognitive_requests')
        with pytest.raises(ValidationError):StructuredProposal(interpretation='No',manager_constraints={'disable':True})
        with pytest.raises(CoreError):OpenAIJSONTransport('http://example.invalid/v1','no')
        claim=SourcedClaim(entity_id='device',predicate='private-fact',value='private synthetic value',kind='USER_CLAIM',valid_from_us=r.clock.utc_now_us())
        m=capture(r,'claim',{'world_claim':claim.model_dump(mode='json')},kind='USER_STATEMENT',privacy='PERSONAL')
        world=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC','PERSONAL'));world.ingest(m)
        assert not WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',)).snapshot()
        forged=claim.model_copy(update={'kind':'RAW_OBSERVATION'});mid=capture(r,'forged',{'world_claim':forged.model_dump(mode='json')},kind='USER_STATEMENT')
        with pytest.raises(CoreError,match='WORLD_USER_CLAIM_NOT_OBSERVATION'):world.ingest(mid)

def test_late_actual_http_reply_cannot_overwrite_new_subject_decision(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (t,state):
        mid=capture(r,'public',{'data':'bounded context'});s=CognitionSession(r,t,policy());cid=s.prepare('late','INTERPRET',(mid,))
        row=r.store.one('cognitive_requests',cid)
        from nana_core.continuity.world_loop.cognition import CognitionRequest
        request=CognitionRequest.model_validate_json(canonical(s.records.read(row['record_id'])['payload']['request']))
        with r.store.transaction('test.calling') as tx:tx.update('cognitive_requests',cid,state='CALLING')
        reply=t.exchange(request)
        event=SubjectInput(source_key='synthetic.new-decision',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',observed_at_us=r.clock.utc_now_us())
        r.subject.run(event)
        assert s.accept(cid,reply)['state']=='STALE' and state['calls']==1
        assert not r.store.db.execute("SELECT 1 FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL'").fetchone()

def test_budgeted_source_selection_and_public_recorded_domain(tmp_path):
    from nana_core.continuity.world_loop.samples import media_samples
    with fresh(tmp_path/'s'/'self.db') as r:
        service=PerceptionService(r.store,providers(),policy());now=r.clock.utc_now_us()
        mid,rid=service.ingest(media_samples()['IMAGE'],PublicMediaSource(source_id='public-recording',modality='IMAGE',origin='RECORDED',event_time_us=now,observed_time_us=now),entity_id='observer',scope='world')
        assert MemoryService(r.store).read(mid)['source_provenance']['domain']=='RECORDED_PUBLIC'
        from nana_core.continuity.context import ContextAssembler,ContextRequest
        assembler=ContextAssembler(r.store,r.authority)
        with pytest.raises(CoreError,match='INSUFFICIENT_CONTEXT_BUDGET'):
            assembler.assemble(ContextRequest(entity_id='observer',scopes=('world',),task_class='world.image',task='inspect',task_privacy_class='PUBLIC',max_input_tokens=512,output_reserve_tokens=100),policy(),required_memory_ids=(mid,))
