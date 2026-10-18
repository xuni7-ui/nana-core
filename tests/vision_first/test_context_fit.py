import pytest
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal,depth_boundary
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.world_loop.reference import open_runtime,capture,context_policy
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND

def interaction(r,key,kind,topic='ordinary',**kwargs):
    return SubjectInput(source_key='synthetic.context.'+key,kind='INTERACTION',origin='USER',entity_id='observer',scope='world',observed_at_us=r.clock.utc_now_us(),text='Public synthetic '+kind+' utterance',privacy_class='PUBLIC',interaction_signal=InteractionSignal(kind=kind,topic_key=topic),**kwargs)

def wake(r,key,mid):
    return SubjectInput(source_key='synthetic.context.wake.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),privacy_class='PUBLIC')

def test_vent_help_share_unclear_and_busy_are_semantic_proposals_not_tasks(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        class Count(AnalyticalFixturePort):
            calls=0
            def propose(self,*args):self.calls+=1;return super().propose(*args)
        model=Count()
        vent=r.subject.cognize(interaction(r,'vent','VENT',significance='RELEVANT'),model=model,authority=r.authority,policy=context_policy())
        assert vent.context_fit.mode=='VENT' and vent.social_proposal.act=='CHECK_IN' and vent.social_proposal.utterance is None and model.calls==0
        assert vent.goal_candidate_id is None and not r.store.all('jobs')
        help=r.subject.run(interaction(r,'help','HELP',topic='help'))
        assert help.judgment.stance=='THINK_MORE' and help.goal_candidate_id and not r.store.all('goals')
        uncertain=r.subject.run(interaction(r,'unclear','UNCLEAR',topic='unclear'))
        assert uncertain.judgment.stance=='ASK' and uncertain.intention.kind=='WAIT'
        busy=r.subject.run(interaction(r,'busy','SHARE',topic='busy',observed_availability='BUSY'))
        assert busy.social_proposal.act=='STAY_SILENT' and not r.store.all('actions')
        assert not r.store.all('grants')

def test_exact_topic_refusal_blocks_later_private_learning_but_not_own_interest(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        closed=r.subject.run(interaction(r,'decline','DECLINE_DEPTH','private-topic'))
        assert not closed.context_fit.allow_deepening
        # Capture actual typed cue as prospective source, not JSON-encoded prose.
        from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
        def cue(topic):
            c=ConcernCue(cue_kind='OPEN_LOOP',topic_key=topic,motivation_source='CREATIVE_INTEREST',possible_behaviors=('LEARN',))
            m=MemoryService(r.store);eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.context-cue',source_reference=topic,source_kind='MODEL_DERIVATION'),text=c.model_dump_json(),privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()))
            root=capture(r,'root-'+topic,{'issue':topic})
            return m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='INFERENCE',source_evidence_id=eid,text=c.model_dump_json(),derived_from=(root,),predicate_key='concern.'+topic))
        private=cue('private-topic');own=cue('independent-art')
        blocked=r.subject.run(wake(r,'closed',private));assert blocked.context_fit.mode=='RESPECT_BOUNDARY' and not blocked.goal_candidate_id
        independent=r.subject.run(wake(r,'own',own));assert independent.intention.behavior=='LEARN'
        pending=r.store.one('subject_intentions',independent.intention_id)
        r.subject.run(interaction(r,'casual','VENT','other-topic'))
        assert r.store.one('subject_intentions',independent.intention_id)==pending
        r.subject.run(interaction(r,'focus','FOCUS','now'))
        assert r.store.one('subject_intentions',independent.intention_id)==pending
        r.subject.run(interaction(r,'reopen','REOPEN','private-topic'))
        assert not depth_boundary(r.store,'observer','world','private-topic',('PUBLIC',))[0]
        reopened=r.subject.run(wake(r,'open',private));assert reopened.intention.behavior=='LEARN'
        # Explicit delete removes boundary's derived support; it never revives text.
        source=r.store.one('subject_events',closed.event_id)['memory_id']
        MemoryService(r.store,r.authority).forget(source,r.authority)
        with pytest.raises(Exception):r.subject.result(r.store.one('subject_cycles',closed.cycle_id))

def test_boundary_survives_restart_and_other_entity_or_topic_not_blocked(tmp_path):
    clock=VirtualClock();db=tmp_path/'self.db'
    with open_runtime(db,clock) as r:
        r.subject.run(interaction(r,'boundary','DECLINE_DEPTH','personal'));identity=r.identity_id
    with open_runtime(db,clock) as r:
        assert identity==r.identity_id and depth_boundary(r.store,'observer','world','personal',('PUBLIC',))[0]
        assert not depth_boundary(r.store,'friend','world','personal',('PUBLIC',))[0]
        assert not depth_boundary(r.store,'observer','world','unrelated',('PUBLIC',))[0]

def test_help_can_disagree_and_playfulness_is_sourced(tmp_path):
    from nana_core.continuity.projects import ProjectService,ProjectContent
    from nana_core.continuity.autonomy.contracts import RelationshipDetails
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        method=capture(r,'project-method',{'allowed_methods':['verify-first']})
        ProjectService(r.store,r.authority).save(project_id='joint',entity_id='observer',scope='world',content=ProjectContent(goal='A controlled project',current_state='Verify before accepting'),source_memory_ids=(method,),expected_revision=0,authority=r.authority)
        event=interaction(r,'inefficient-help','HELP','project',constraint_memory_ids=(method,),proposed_method='guess-first')
        assert r.subject.run(event).judgment.stance=='ALTERNATIVE'
        # Existing relational history, not a friendliness quota, licenses play.
        for i in range(2):
            e=SubjectInput(source_key='synthetic.context.joke.'+str(i),kind='RELATIONSHIP',origin='USER',entity_id='observer',scope='world',text='Public synthetic shared joke',observed_at_us=r.clock.utc_now_us(),privacy_class='PUBLIC',relationship_kind='SHARED_JOKE' if i else 'SHARED_HISTORY',significance='RELEVANT')
            r.subject.run(e)
        playful=r.subject.run(interaction(r,'sharing','SHARE','play'))
        assert playful.social_proposal.act in {'TEASE','SHARE_THOUGHT'} and playful.social_proposal.utterance is None

def test_transient_context_is_available_now_but_not_durable_after_restart(tmp_path):
    from nana_core.presence.contracts import RuntimeEvent,Cause
    clock=VirtualClock();db=tmp_path/'self.db'
    with open_runtime(db,clock) as r:
        e=interaction(r,'transient','VENT','short-lived')
        qid=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=e,causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=clock.utc_now_us(),priority=3))
        row=r.store.one('runtime_queue',qid)
        assert row['record_id'] is None and 'short-lived' not in row['metadata_json']
        assert r.queue.input(row).interaction_signal.kind=='VENT'
    with open_runtime(db,clock) as r:
        assert r.queue.input(r.store.one('runtime_queue',qid)).interaction_signal is None
        assert not r.queue._transient_interactions


def test_deleted_boundary_no_longer_projects_and_inference_cannot_install_one(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        event=interaction(r,'explicit','DECLINE_DEPTH','erasable')
        result=r.subject.run(event);mid=r.store.one('subject_events',result.event_id)['memory_id']
        assert depth_boundary(r.store,'observer','world','erasable',('PUBLIC',))[0]
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        assert not depth_boundary(r.store,'observer','world','erasable',('PUBLIC',))[0]
        inferred=interaction(r,'guess','DECLINE_DEPTH','uncertain')
        inferred=inferred.model_copy(update={'interaction_signal':inferred.interaction_signal.model_copy(update={'basis':'INTERPRETED'})})
        assert r.subject.run(inferred).context_fit.mode=='UNCLEAR'
        assert not depth_boundary(r.store,'observer','world','uncertain',('PUBLIC',))[0]
