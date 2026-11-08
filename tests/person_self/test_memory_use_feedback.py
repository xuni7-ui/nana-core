"""Explicit source-bound use preferences, not real human/delivery evidence."""
import json
import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
from nana_core.continuity.lived_language import LanguageService,LanguageSample,MemoryUseFeedback
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from tests.independent_life.test_dialogue import relay


def package(app):
    request=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='world.social',
        task='SYNTHETIC ORCHID recall',task_privacy_class='PROJECT',query_terms=('ORCHID',),max_input_tokens=16384)
    policy=ContextPolicy(policy_id='synthetic.memory-use',allowed_scopes=('project-work',),readable_privacy=('PROJECT',))
    assembler=ContextAssembler(app.runtime.store,app.runtime.authority)
    result=assembler.assemble(request,policy,pinned_only=True,conversation_topic='daily')
    assembler.validate(result,request,policy)
    return result


@pytest.mark.parametrize('mode',['EXPLICIT_RECALL','NATURAL_REFERENCE','IMPLICIT_REFERENCE','DO_NOT_MENTION'])
def test_bound_preference_reaches_later_context_restart_and_withdrawal(app,mode):
    home=app.home;clock=app.clock;app.close()
    def render(request):
        blocks=json.loads(request['context_json'])['blocks']
        guidance=next((json.loads(b['data_json'])['memory_use_guidance'] for b in blocks if b['kind']=='MEMORY_USE_GUIDANCE'),None)
        return 'SYNTHETIC '+(guidance[0]['requested_mode'] if guidance else 'BASELINE')
    with relay(home,'CHAT',recall_query_terms=('ORCHID',),renderer=render) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause()
            mid=save(current,text='SYNTHETIC ORCHID meeting is Friday.',privacy='PROJECT',request_id='use-note')['memory_id']
            before=MemoryService(current.runtime.store).read(mid)
            assert not any(b.kind=='MEMORY_USE_GUIDANCE' for b in package(current).blocks)
            turn=current.chat('SYNTHETIC ORCHID question',privacy='PROJECT',retain_shared_life=True,message_id='use-turn')
            sample=LanguageSample(sample_id='memory-use-report',review_target=turn['exchange_record_id'],mode='CASUAL',
                context='SYNTHETIC ORCHID question',candidate_response=turn['text'],human_judgment='PARTIAL',
                provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us(),
                memory_use=MemoryUseFeedback(memory_id=mid,mode=mode))
            service=LanguageService(current.runtime.store,current.runtime.authority)
            unrelated=save(current,text='SYNTHETIC unrelated saved note',privacy='PROJECT',request_id='other-use-note')['memory_id']
            bad=sample.model_copy(update={'sample_id':'wrong-memory-use','memory_use':MemoryUseFeedback(memory_id=unrelated,mode=mode)})
            with pytest.raises(CoreError,match='MEMORY_USE_REVIEW_SOURCE_MISMATCH'):
                service.record(bad,scope='project-work',entity_id='project-user',privacy='PROJECT',
                    authority=current.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            rid=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                authority=current.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            saved=service.records.read(rid)['payload']
            assert 'memory_use' not in saved['sample'] and saved['memory_use_feedback']['mode']==mode
            assert service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                authority=current.runtime.authority,exchange_record_id=turn['exchange_record_id'])==rid
            if mode=='NATURAL_REFERENCE':
                for n in range(40):
                    noise=sample.model_copy(update={'sample_id':'noise-'+str(n),'review_target':'synthetic-noise-'+str(n),
                        'memory_use':None,'provenance':'PROJECT_SYNTHETIC','human_judgment':'UNREVIEWED','body_storage':'SOURCE_REPORT'})
                    service.record(noise,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=current.runtime.authority)
            identity=current.runtime.identity_id
        clock.advance(3*86400_000_000)
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause()
            assert current.runtime.identity_id==identity
            blocks=[b for b in package(current).blocks if b.kind=='MEMORY_USE_GUIDANCE']
            assert len(blocks)==1 and rid in blocks[0].source_record_ids
            guidance=json.loads(blocks[0].data_json)['memory_use_guidance'][0]
            assert guidance['memory_id']==mid and guidance['requested_mode']==mode
            assert guidance['fact_assessment_unchanged'] and guidance['advisory_to_subject']
            reply=current.chat('SYNTHETIC different ORCHID follow-up',privacy='PROJECT',message_id='use-later-turn')
            assert reply['text']=='SYNTHETIC '+mode and len(requests)==4
            after=MemoryService(current.runtime.store).read(mid)
            assert (after['assessment'],after['confidence'],after['text'])==(before['assessment'],before['confidence'],before['text'])
            source=current.runtime.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.conversation.feedback' AND e.source_reference='memory-use-report'").fetchone()[0]
            current.forget(source)
            assert not any(b.kind=='MEMORY_USE_GUIDANCE' for b in package(current).blocks)
            assert MemoryService(current.runtime.store).read(mid)['text']==before['text']


def test_unbound_or_unrelated_memory_use_report_rejected(app):
    service=LanguageService(app.runtime.store,app.runtime.authority)
    sample=LanguageSample(sample_id='unbound',review_target='no-exchange',mode='CASUAL',context='SYNTHETIC',
        candidate_response='SYNTHETIC',human_judgment='PARTIAL',provenance='USER_PROVIDED_REVIEW',
        observed_at_us=app.clock.utc_now_us(),memory_use=MemoryUseFeedback(memory_id='no-memory',mode='DO_NOT_MENTION'))
    with pytest.raises(CoreError,match='MEMORY_USE_REVIEW_BINDING_REQUIRED'):
        service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority)
    assert not app.runtime.store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_reference='unbound'").fetchone()


def test_legacy_language_sample_serialization_stays_unchanged(app):
    sample=LanguageSample(sample_id='legacy',review_target='turn',mode='CASUAL',context='SYNTHETIC',
        candidate_response='SYNTHETIC',human_judgment='UNREVIEWED',provenance='PROJECT_SYNTHETIC',observed_at_us=app.clock.utc_now_us())
    assert 'memory_use' not in sample.model_dump(mode='json')
