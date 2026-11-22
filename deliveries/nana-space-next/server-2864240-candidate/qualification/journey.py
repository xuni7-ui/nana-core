"""One owned-dev Subject across all offline integration and process stages.

Synthetic semantic provider is explicit loopback, never real-provider evidence.
The existing daily-life process runner remains the sole residency orchestrator.
"""
import argparse,json
from pathlib import Path
from nana_core.storage import canonical
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.autonomy.private_intent import candidates,eligible_content
from nana_core.continuity.autonomy.contracts import RealizationTarget
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint,ManagerConstraintGate
from nana_core.life.inspector import inspect
from nana_core.contracts import CoreError
from tools.nana_cloud_daily_life.qualification import run as residency


def setup(app,root):
    r=app.runtime;s=r.store;identity=r.identity_id
    def event(key,**fields):
        return SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.integration.'+key,privacy_class='PROJECT',entity_id=r.config.entity_id,scope=r.config.scopes[0],observed_at_us=r.clock.utc_now_us(),**fields)
    def settle(c):
        if c.intention_id:
            row=s.one('subject_intentions',c.intention_id)
            if row['state']=='PENDING':r.subject.transition_intention(c.intention_id,expected_revision=row['revision'],state='DROPPED')
    # Owned source bytes observed on disk, not a pre-inserted goal or fake life event.
    path=root/'observed-project.json';path.write_text(canonical({'state':'a public development note merits review','opportunities':[{'topic':'note-review','motive':'CURIOSITY','value':'HIGH','possible_behaviors':['EXPLORE','WATCH']}]}))
    mid=capture(r,'integration.owned-note',json.loads(path.read_text()))
    with provider_harness() as (transport,metrics):
        session=CognitionSession(r,transport,app.policy)
        request=session.prepare('first-life-semantic-once','INTERPRET',(mid,),budget=CognitionBudget(timeout_ms=2000,cost_ceiling_micro=0))
        reply=session.execute(request);assert reply['state']=='PROPOSED'
        parsed=session.proposal(reply['record_id'])
        claim=SourcedClaim(entity_id=r.config.entity_id,predicate='integration.note',kind='MODEL_BELIEF',value=parsed.proposal.interpretation,confidence=parsed.proposal.confidence,valid_from_us=r.clock.utc_now_us())
        derived=capture(r,'integration.semantic',{'world_claim':claim.model_dump(mode='json'),'request_id':request,'request_digest':parsed.request_digest},kind='MODEL_DERIVATION',parents=(mid,))
        world=WorldModel(s,scopes=r.config.scopes,privacy_classes=('PROJECT',));bid=world.ingest(derived)
        service=ConcernService(r,resources=('synthetic://integration/note',));ids=service.offer(reply['record_id']);offered=service.opportunity();assert offered
        c=r.subject.run(offered.input);assert c.intention.kind=='EXPLORE';settle(c)
        before=world.view(r.config.entity_id,'integration.note').state
        # An independent direct conflicting owned-source observation exposes uncertainty.
        contrary=SourcedClaim(entity_id=r.config.entity_id,predicate='integration.note',kind='RAW_OBSERVATION',value='The owned note changed',valid_from_us=r.clock.utc_now_us())
        path.write_text(canonical({'state':contrary.value}))
        counter=capture(r,'integration.changed-note',{'world_claim':contrary.model_dump(mode='json')});world.ingest(counter)
        conflict=world.view(r.config.entity_id,'integration.note').state;assert conflict=='CONFLICT'
        corrected=contrary.model_copy(update={'corrects':bid})
        correction=capture(r,'integration.corrected-note',{'world_claim':corrected.model_dump(mode='json')});world.ingest(correction)
        after_correction=world.view(r.config.entity_id,'integration.note').state;assert after_correction=='SUPPORTED_BELIEF'
        app.forget(mid);app.forget(counter);app.forget(correction)
        withdrawn=world.view(r.config.entity_id,'integration.note').state;assert withdrawn=='UNKNOWN' and service.opportunity() is None
        after=r.subject.run(event('withdrawn',kind='WAKE',origin='SELF_WAKE'));assert after.intention.kind=='NO_ACTION'
        assert session.execute(request)['replayed'] and metrics['calls']==1
        semantic={'execution':'SYNTHETIC_LOOPBACK_NOT_LIVE','identity_id':identity,'request_id':request,'source_to_world_to_concern_to_c':True,'before':before,'conflict':conflict,'corrected':after_correction,'withdrawn':withdrawn,'after_choice':after.intention.kind,'fixture_calls':1,'real_provider_calls':0,'no_duplicate_dispatch':True}
    # Non-command creative opportunity, chosen by the original C before any content
    # is stored as a private idea. No model roleplay or surprise-create command.
    cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='creative-note',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE','REST'),resource_class='ORDINARY')
    private_source=capture(r,'integration.creative-source',cue.model_dump(mode='json'),predicate='concern.creative-note')
    private_cycle=r.subject.run(event('creative',kind='WAKE',origin='SELF_WAKE',source_memory_ids=(private_source,)))
    private=candidates(s,'project-work',('PUBLIC','PROJECT'));assert len(private)==1
    rid,value=private[0]
    withhold=False
    try:eligible_content(s,value.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
    except CoreError as exc:withhold=exc.code=='PRIVATE_INTENT_WITHHELD'
    assert withhold
    before_events=s.db.execute('SELECT count(*) FROM events').fetchone()[0];before_changes=s.db.total_changes
    inspector=inspect(app.home,scope='project-work',entity_id='project-user')
    assert value.content_summary not in inspector.model_dump_json() and inspector.private_activity=='PRESENT_CONTENT_WITHHELD'
    assert s.db.total_changes==before_changes and s.db.execute('SELECT count(*) FROM events').fetchone()[0]==before_events
    # Separate external governance veto; original judgment is retained verbatim.
    target=RealizationTarget(capability='world.observe',operation='READ',resource='synthetic://integration/blocked',resource_class='ORDINARY')
    other=cue.model_copy(update={'topic_key':'governed-note','possible_behaviors':('EXPLORE',)})
    govmid=capture(r,'integration.governed',other.model_dump(mode='json'),predicate='concern.governed-note')
    govcycle=r.subject.run(event('governed',kind='WAKE',origin='SELF_WAKE',source_memory_ids=(govmid,),realization_target=target))
    controller=GovernanceController(s,r.authority);controller.initialize(r.authority)
    controller.install(ManagerConstraint(constraint_id='first-life-dev-wall',revision=1,issuer=r.authority.principal,source_reference='owned-development-governance',identity_id=identity,scope='project-work',targets=(target,),effective_from_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+7200_000_000,reason_code='DO_NOT_READ_RESOURCE'),r.authority)
    blocked=ManagerConstraintGate(s).gate(govcycle.intention_id,expected_revision=1)
    assert blocked.result=='BLOCK' and blocked.actual_effect=='NONE' and blocked.action_id is None
    original=r.subject.result(s.one('subject_cycles',govcycle.cycle_id));assert original.judgment==govcycle.judgment and original.evaluation.normative=='ENDORSED'
    controller.revoke('first-life-dev-wall',expected_revision=1,authority=r.authority)
    # Ordinary topic refusal stops expression, not all future independent cognition.
    response=app.chat('这个先别聊了',topic='creative-note',privacy='PROJECT',message_id='integration-refusal')
    assert response['mode']=='RESPECT_BOUNDARY'
    assert value.content_summary not in response['text']
    from nana_core.continuity.subject.context_fit import depth_boundary
    assert depth_boundary(s,'project-user','project-work','creative-note',r.config.privacy_classes)[0]
    assert not depth_boundary(s,'project-user','project-work','creative-note',r.config.privacy_classes,purpose='COGNITION')[0]
    assert len(s.all('identities'))==1 and len(s.all('actions'))==0
    return {'identity_id':identity,'semantic':semantic,'private_intent':{'cycle_id':private_cycle.cycle_id,'intent_id':value.intent_id,'record_id':rid,'policy':value.disclosure_policy,'withheld':withhold,'inspector_read_only':True,'no_action_or_grant_created':True},'manager':{'original_normative':'ENDORSED','result':blocked.result,'no_action':True,'revocation_no_old_replay':True},'conversation_refusal_not_cognitive_boundary':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--seconds',type=float,default=1800);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[2]
    result=residency(a.root,repo,a.seconds,integration_setup=setup)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'state':'OFFLINE_PROCESS_JOURNEY_COMPLETE','seconds':result['actual_residency_seconds'],'identity_id':result['final']['identity_id'],'output':str(a.output),'human_review':'NOT_RUN'}))
if __name__=='__main__':main()
