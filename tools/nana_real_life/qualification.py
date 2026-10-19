"""Real repository sources→artifacts→original learning→later C choices.

Only recipient context/fixture ModelPorts are synthetic. No live message/provider.
"""
import argparse,json,time
from pathlib import Path
from nana_core.storage import canonical,digest
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.project_work.service import ProjectWork,open_project_runtime,material_for,learning_spec,capture
from nana_core.continuity.project_work.port import read_material
from nana_core.continuity.project_work.analysis import inventory
from nana_core.continuity.project_work.oracle import expected_inventory
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.open_agency.delivery import RecipientState
from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.subject.growth_life import project,opportunities
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.cognition import AnalyticalFixturePort,CautiousFixturePort
from nana_core.continuity.context import ContextPolicy

SOURCES=('src/nana_core/continuity/recurrence.py','src/nana_core/continuity/extensions.py')
TRAINING=('src/nana_core/continuity/identity.py','src/nana_core/continuity/autonomy/requests.py','src/nana_core/continuity/subject/social.py')

def recipient(r,key,state):
    value=RecipientState(resource='synthetic://recipient/project-user',entity_id='project-user',availability=state,observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+60*SECOND)
    m=MemoryService(r.store)
    eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.project-context',source_reference=key,source_kind='SYSTEM_VERIFICATION'),text=value.model_dump_json(),privacy_class='PROJECT',observed_time_us=r.clock.utc_now_us()))
    return m.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=value.model_dump_json(),predicate_key='recipient.context'))

def future_cycle(r,key,view):
    return r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.future.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',source_memory_ids=view.source_memory_ids,observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',growth_assessment_id=view.assessment_id))

def run(root,repo,*,withdraw=False):
    clock=VirtualClock();started=time.monotonic();cpu=time.process_time();db=root/'subject/self.db'
    materials=tuple(material_for(repo,p) for p in SOURCES)
    spec=learning_spec(*(read_material(repo,material_for(repo,p)) for p in TRAINING))
    with open_project_runtime(db,clock) as r:
        work=ProjectWork(r,repo,materials,root/'reports',spec,grant=True);identity=r.identity_id
        root_source=work.request(materials[0].material_id)
        work.run_until(lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()))
        failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE'").fetchone()
        work.reflect_failure(failure['experience_id'])
        work.run_until(lambda:bool(r.work.open_learning.strategy('python-api','project-work')))
        work.run_until(lambda:len(list(work.port.output.glob('*.md')))==1)
        learning_job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        learning=RecordService(r.store).read(learning_job['record_id'])['payload'];lesson_id=learning['lesson_id']
        navigation=work.lookup(materials[0].material_id,'RecurrenceSpec.next_after')
        assert 'def next_after' in navigation['excerpt'] and navigation['line']==43
        # New practical input, not present in proposer/practice/heldout/transfer.
        later=read_material(repo,materials[1]);assert all(digest(later)!=digest(c.data) for group in (spec.practice,spec.evaluation,spec.transfer) for c in group)
        before=time.monotonic();later_root=work.request(materials[1].material_id)
        work.run_until(lambda:len(list(work.port.output.glob('*.md')))==2);later_latency=time.monotonic()-before
        reports=[json.loads(p.read_text()) for p in work.port.output.glob('*.json')]
        assert {x['source_path'] for x in reports}==set(SOURCES)
        for m in materials:assert next(x for x in reports if x['source_path']==m.relative_path)['data']==expected_inventory(read_material(repo,m))
        later_action=next(a for a in r.store.all('actions') if a['resource']=='project://'+materials[1].material_id+'/inventory')
        assert later_action['state']=='SUCCEEDED'
        result=json.loads(r.work.agency.realization.kernel.payload(later_action,'result_json'));assert result['method']=='PYTHON_AST_API'
        memory=r.store.db.execute("SELECT memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_namespace='recorded.project.local-action' AND e.source_reference=?",(later_action['action_id'],)).fetchone()[0]
        case=LearningCase(case_id='later-real-source',context='portable-surface-onboarding',data=later,expected=expected_inventory(later))
        episode={'episode_key':'later-real-source','lesson_id':lesson_id,'case':case.model_dump(mode='json'),'action_id':later_action['action_id'],'actual_result_digest':digest(result['data'])}
        reuse=capture(r,'later-reuse',{'strategy_episode':episode},kind='SYSTEM_VERIFICATION',parents=(memory,))
        assessment=EpisodeLearning(r.store,r.authority,scopes=('project-work',),privacy_classes=('PROJECT',)).assess(lesson_id,reuse,authority=r.authority)
        view=project(r.store,assessment,scope='project-work',privacy_classes=('PROJECT',));assert view
        # Actual local sources cause future choices; availability here is explicitly synthetic.
        recipient(r,'available','AVAILABLE');share=future_cycle(r,'share',view)
        assert share.social_proposal and share.social_proposal.act=='REPORT_DISCOVERY'
        if share.intention_id:r.subject.transition_intention(share.intention_id,expected_revision=1,state='DROPPED')
        clock.advance(SECOND);recipient(r,'busy','BUSY');busy=future_cycle(r,'busy',view)
        assert busy.intention.kind=='NO_ACTION' and not busy.social_proposal
        refuse=r.subject.run(SubjectInput(source_key='synthetic.project-refusal',kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',text='Anonymous manual no-interest control',interaction_signal=InteractionSignal(kind='DECLINE_DEPTH',topic_key=view.topic)))
        clock.advance(SECOND);recipient(r,'available-again','AVAILABLE');refused=future_cycle(r,'refused',view)
        assert refused.context_fit.mode=='RESPECT_BOUNDARY' and refused.intention.kind=='NO_ACTION'
        policy=ContextPolicy(policy_id='project-local',allowed_scopes=('project-work',),readable_privacy=('PROJECT',),remote_privacy=())
        before_counts=(len(r.store.all('actions')),len(r.store.all('grants')))
        for key,model in (('a',AnalyticalFixturePort()),('b',CautiousFixturePort())):
            r.subject.cognize(SubjectInput(source_key='synthetic.project-model.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',source_memory_ids=(reuse,),observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',task_class='python-api'),model=model,authority=r.authority,policy=policy)
        assert before_counts==(len(r.store.all('actions')),len(r.store.all('grants')))
        # Separate actual interventions; deletion is never tested after an
        # already suspended strategy (that would confound the causal result).
        assert project(r.store,assessment,scope='project-work',privacy_classes=('PROJECT',))
        if withdraw:
            MemoryService(r.store,r.authority).forget(root_source,r.authority)
            assert not project(r.store,assessment,scope='project-work',privacy_classes=('PROJECT',))
            assert not r.work.open_learning.strategy('python-api','project-work')
            try:capture(r,'input:'+materials[0].material_id,{'origin':'DEVELOPMENT_PROJECT','source':read_material(repo,materials[0])})
            except Exception as e:assert getattr(e,'code',None)=='SOURCE_DELETED'
            else:raise AssertionError('source resurrected')
        else:
            ExperienceService(r.store,r.authority).suspend(lesson_id,r.authority)
            assert not project(r.store,assessment,scope='project-work',privacy_classes=('PROJECT',))
            assert not r.work.open_learning.strategy('python-api','project-work')
        count=len(r.store.all('actions'))
        erasure=withdraw;suspended=not withdraw
        quality={'baseline':learning['results']['BASELINE'],'practice':learning['results']['PRACTICE'],'heldout':learning['results']['EVALUATE'],'transfer':learning['results']['TRANSFER'],
                 'later_baseline_count':len(inventory('PYTHON_TOP_DEFS',later)),'later_actual_count':len(result['data']),'later_oracle_count':len(expected_inventory(later))}
        summary={'identity_id':identity,'navigation':navigation,'input_sources':[m.model_dump() for m in materials],'training_sources':list(TRAINING),'quality':quality,'failure_experience_id':failure['experience_id'],
            'learning_work_id':learning_job['job_id'],'lesson_id':lesson_id,'later_action_id':later_action['action_id'],'later_source_memory_id':later_root,'reuse_memory_id':reuse,'assessment_id':assessment,
            'source_memory_id':root_source,'artifacts':list(work.artifacts()),'future_share':share.social_proposal.act,'busy':busy.intention.kind,'no_interest':refused.intention.kind,
            'source_withdrawal':erasure,'strategy_retirement':suspended,'model_fixture_swap':True,'local_kernel_actions':count,'later_elapsed_seconds':later_latency,
            'experience_before_learning':failure['outcome'],'actual_external_actions':0,'provider_calls':0,'synthetic_context':'recipient availability and anonymous refusal only; not real user reactions'}
    with open_project_runtime(db,clock) as r:
        assert r.identity_id==identity and len(r.store.all('actions'))==count
        assert not opportunities(r.store,scope='project-work',privacy_classes=('PROJECT',))
        assert r.store.db.execute('PRAGMA foreign_key_check').fetchall()==[]
        summary.update(restart_identity_stable=True,no_resurrection_after_restart=withdraw,no_new_actions_or_grants_on_restart=True)
    summary.update(elapsed_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,capability_claim='Source-supported selection among prewritten bounded methods, not autonomous algorithm invention')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.root.exists():p.error('fresh dedicated dev root required')
    result=run(a.root/'retirement',a.repo);ablation=run(a.root/'withdrawal',a.repo,withdraw=True)
    result['withdrawal_arm']=ablation
    assert result['quality']==ablation['quality']
    result['counterfactual']='same sources/spec and checked pre-intervention results; separate store IDs; only actual withdrawal vs strategy retirement differs'
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'artifacts':result['artifacts'],'result':str(a.output)}))
if __name__=='__main__':main()
