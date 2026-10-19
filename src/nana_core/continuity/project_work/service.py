"""Dev application facade: structured requests through original C/D/F/G/Kernel.

No LLM credentials, ambient project walk or unreviewed adoption. Each request
installs only finite program descriptions; the original C chooses its intention.
"""
import hashlib
import json
import time
from pathlib import Path
from contextlib import contextmanager
from ...actions import OperatorAuthority
from ...contracts import CoreError, GrantSpec
from ...storage import canonical, digest
from .. import ContinuityStore, IdentityService
from ..memory import MemoryService
from ..contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from ..records import RecordService
from ..subject import SubjectInput
from ..subject.opportunities import ConcernCue
from ..open_agency.contracts import Objective, Operator
from ..open_agency.service import OpenGoalPolicy
from ..open_agency.learning import LearningCase, LearningSpec
from ..autonomy.governance import GovernanceController
from ...presence.runtime import NanaRuntime
from ...presence.contracts import RuntimeConfig, LivingRuntimeConfig, RuntimeEvent, Cause, SECOND, HOUR
from .port import ProjectMaterial, ProjectMaterialPort, read_material, read_material_bytes
from .oracle import expected_inventory


def learning_spec(practice, heldout, transfer):
    """Answers are host evaluator inputs, not proposer inputs."""
    def case(key, context, data):
        return LearningCase(case_id=key, context=context, data=data, expected=expected_inventory(data))
    return LearningSpec(learning_key='learn.python-api', domain='python-api', baseline_method='PYTHON_TOP_DEFS', hypotheses=('PYTHON_AST_API',),
        practice=(case('practice', 'project-api', practice),), evaluation=(case('heldout', 'project-api', heldout),), transfer=(case('transfer', 'onboarding', transfer),))


@contextmanager
def open_project_runtime(path, clock):
    with ContinuityStore(path, clock, schema_target=13) as store:
        IdentityService(store, OperatorAuthority())
        MemoryService(store).entity('project-user', 'PERSON')
    config = RuntimeConfig(schema_target=13, scopes=('project-work',), entity_id='project-user', privacy_classes=('PUBLIC', 'PROJECT'),
        max_calls_per_day=32, lease_us=2*HOUR, heartbeat_us=15*60*SECOND, review_interval_us=HOUR, idle_recall_us=HOUR,
        living=LivingRuntimeConfig(background_fraction_percent=80, maintenance_interval_us=HOUR))
    with NanaRuntime(path, config, clock=clock) as runtime:
        yield runtime


def capture(runtime, key, data, *, kind='DIRECT_OBSERVATION', parents=(), predicate=None):
    memory=MemoryService(runtime.store); text=canonical(data) if not isinstance(data,str) else data
    previous=runtime.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference=?",(key,)).fetchone()
    observed=previous[0] if previous else runtime.clock.utc_now_us()
    eid=memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',source_namespace='recorded.project.material', source_reference=key, source_kind=kind), text=text,
        privacy_class='PROJECT', observed_time_us=observed))
    existing=runtime.store.db.execute("SELECT memory_id FROM memories WHERE source_evidence_id=? AND lifecycle='ACTIVE'",(eid,)).fetchone()
    return existing[0] if existing else memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,
        epistemic_kind='BELIEF' if kind=='MODEL_DERIVATION' else 'STATEMENT' if kind=='USER_STATEMENT' else 'OBSERVATION',source_evidence_id=eid,text=text,derived_from=parents,predicate_key=predicate))


def post(runtime, key, mids, **kwargs):
    old=runtime.store.db.execute("SELECT queue_id FROM runtime_queue WHERE source_key=?",('development.project.'+key,)).fetchone()
    if old:return old[0]
    inp=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.project.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
        observed_at_us=runtime.clock.utc_now_us(),source_memory_ids=mids,privacy_class='PROJECT',task_class='python-api',**kwargs)
    return runtime.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,
        causes=(Cause(kind='MEMORY',reference_id=mids[0]),),due_at_us=runtime.clock.utc_now_us()))


def source_objective(material, expected, *, suffix='request',motivation_source='PROJECT_COMPLETION'):
    key=material.material_id; program='project.'+key+'-'+suffix
    return Objective(objective_id=program,scope='project-work',motivation_source=motivation_source,task_domain='python-api',desired=('report',),operators=(
        Operator(operator_id='inspect',capability='world.observe',resource='project://'+key+'/source',produces=('seen',),args={}),
        Operator(operator_id='inventory',capability='world.compute',resource='project://'+key+'/inventory',requires=('seen',),produces=('indexed',),
            args={'method':'PYTHON_TOP_DEFS','input_from':'inspect','data_privacy':'PROJECT'},strategy_selectable=True,expected_digest=digest(expected)),
        Operator(operator_id='publish',capability='world.publish',resource='project://'+key+'/report',requires=('indexed',),produces=('report',),args={'input_from':'inventory','data_privacy':'PROJECT'},expected_digest=digest(expected))))


class ProjectWork:
    """Application-owned facade. Receives explicit manifests and original Runtime."""
    def __init__(self, runtime, repo, materials, output, spec=None, *, grant=False,motivation_source='PROJECT_COMPLETION'):
        self.runtime=runtime; self.port=ProjectMaterialPort(runtime.identity_id,repo,materials,output)
        self.objects={m.material_id:source_objective(m,expected_inventory(read_material(repo,m)),motivation_source=motivation_source) for m in materials}
        # Recovery descriptions are host configuration. No grants are recreated
        # on reopening; caller must explicitly request local development authority.
        all_objects=tuple(self.objects.values())
        GovernanceController(runtime.store,runtime.authority).initialize(runtime.authority)
        runtime.work.configure_open_agency(OpenGoalPolicy(all_objects),self.port)
        self.training_sources=()
        if spec:
            self.training_sources=tuple(capture(runtime,'dataset:'+digest(c.data),{'origin':'DEVELOPMENT_PROJECT','source':c.data}) for group in (spec.practice,spec.evaluation,spec.transfer) for c in group)
            runtime.work.configure_open_learning((spec,),source_memory_ids=self.training_sources)
        if grant:
            kernel=runtime.work.agency.realization.kernel;now=runtime.clock.utc_now_us()
            kernel.grant(GrantSpec(capabilities=('world.observe','world.compute','world.publish',kernel.verify_capability),
                resources=tuple(op.resource for obj in self.objects.values() for op in obj.operators),not_before_us=now,expires_at_us=now+HOUR),runtime.authority)
            kernel.set_budgets({'write_attempts':32,'external_requests':128,'cost_micro_units':128},runtime.authority)

    def assess_later_use(self):
        """One independently verified new material may inform future C attention."""
        if not self.runtime.work.open_learning:return None
        r=self.runtime;strategy=r.work.open_learning.strategy('python-api','project-work')
        if not strategy:return None
        lesson=r.store.db.execute('SELECT * FROM lessons WHERE record_id=?',(strategy[0],)).fetchone()
        from ..world_loop.learning import EpisodeLearning
        from ..open_agency.learning import LearningCase
        for material in self.port.materials.values():
            goal=self.goal_for(material.material_id)
            if not goal or goal['state']!='COMPLETED':continue
            actions=r.store.db.execute("SELECT * FROM actions WHERE resource=? AND capability='world.compute' AND state='SUCCEEDED' ORDER BY rowid LIMIT 16",('project://'+material.material_id+'/inventory',)).fetchall()
            results=[]
            for action in actions:
                try:results.append((action,json.loads(r.work.agency.realization.kernel.payload(action,'result_json'))))
                except CoreError:continue
            # Exclude the original failure/repaired material, not just training
            # cases. A genuinely later object must have no baseline exposure.
            if not results or any(x['method']!=strategy[1] for _,x in results):continue
            action,actual=results[-1];key='later-'+digest([lesson['lesson_id'],material.sha256])[:40]
            if r.store.db.execute('SELECT 1 FROM strategy_assessments WHERE lesson_id=? AND episode_key=?',(lesson['lesson_id'],key)).fetchone():continue
            source=read_material(self.port.root,material)
            case=LearningCase(case_id='later-material',context='later-project-navigation',data=source,expected=expected_inventory(source))
            mid=r.store.db.execute("SELECT memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_namespace='recorded.project.local-action' AND e.source_reference=? AND m.lifecycle='ACTIVE' LIMIT 1",(action['action_id'],)).fetchone()
            if not mid:continue
            episode={'episode_key':key,'lesson_id':lesson['lesson_id'],'case':case.model_dump(mode='json'),'action_id':action['action_id'],'actual_result_digest':digest(actual['data'])}
            reuse=capture(r,key,{'strategy_episode':episode},kind='SYSTEM_VERIFICATION',parents=(mid[0],))
            assessment=EpisodeLearning(r.store,r.authority,scopes=('project-work',),privacy_classes=r.config.privacy_classes).assess(lesson['lesson_id'],reuse,authority=r.authority)
            r.refresh_attention()
            return {'later_use_assessment_id':assessment,'source_memory_id':reuse}
        return None

    def goal_for(self, material_id):
        obj=self.objects[material_id]
        row=self.runtime.store.db.execute("SELECT g.* FROM goals g JOIN continuity_records r ON r.record_id=json_extract(g.body_json,'$.record_id') JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE json_extract(CAST(a.payload AS TEXT),'$.objective.objective_id')=? ORDER BY g.rowid DESC LIMIT 1",(obj.objective_id,)).fetchone()
        return dict(row) if row else None

    def request(self, material_id):
        r=self.runtime;obj=self.objects[material_id]
        material=self.port.materials[material_id];source=read_material(self.port.root,material)
        root=capture(r,'input:'+material_id,{'origin':'DEVELOPMENT_PROJECT','source':source})
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=obj.objective_id,motivation_source=obj.motivation_source,program_id=obj.objective_id)
        mid=capture(r,'request:'+obj.objective_id,cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(root,),predicate='concern.'+obj.objective_id)
        post(r,'request.'+obj.objective_id,(mid,))
        return root

    def run_until(self, predicate, *, max_steps=96):
        start=time.monotonic();r=self.runtime
        for _ in range(max_steps):
            if predicate():return time.monotonic()-start
            r.clock.source.advance(SECOND);r.step()
        raise CoreError('PROJECT_BOUNDED_RUN_INCOMPLETE')

    def reflect_failure(self, experience_id):
        """Offer a real recorded failure, NOT a command to learn or a fabricated wish."""
        exp=self.runtime.store.one('experiences',experience_id)
        if not exp or exp['outcome']!='FAILURE' or exp['task_class']!='python-api':raise CoreError('PROJECT_CHECKED_FAILURE_REQUIRED')
        return post(self.runtime,'review.'+experience_id,(exp['result_memory_id'],exp['verification_memory_id'],*self.training_sources),reflection_experience_id=experience_id)

    def lookup(self, material_id, qualified_name):
        """Read-only view from a still-supported independently verified inventory."""
        r=self.runtime;material=self.port.materials[material_id]
        source=read_material(self.port.root,material)
        rows=r.store.db.execute("SELECT * FROM actions WHERE resource=? AND capability='world.compute' AND state='SUCCEEDED' ORDER BY rowid DESC LIMIT 16",('project://'+material_id+'/inventory',)).fetchall()
        for action in rows:
            try:result=json.loads(r.work.agency.realization.kernel.payload(action,'result_json'))
            except CoreError:continue
            match=next((x for x in result['data'] if x['name']==qualified_name),None)
            if not match:continue
            line=match['line'];excerpt='\n'.join(source['source'].splitlines()[line-1:line+11])
            return {'source_path':material.relative_path,'source_digest':material.sha256,'symbol':qualified_name,'line':line,'excerpt':excerpt,
                    'coverage':'AT_MOST_12_SOURCE_LINES_NOT_FULL_FUNCTION','verified_action_id':action['action_id'],'execution':'NO_CODE_EXECUTED'}
        raise CoreError('PROJECT_SYMBOL_NOT_IN_CURRENT_VERIFIED_INVENTORY')

    def artifacts(self):
        return tuple(sorted(str(p) for p in self.port.output.iterdir() if p.suffix in {'.md','.json'}))


def material_for(repo, relative_path):
    # Caller supplies one explicit approved repository file; never auto-discover.
    raw=read_material_bytes(repo,relative_path)
    material=ProjectMaterial(material_id='m'+hashlib.sha256(relative_path.encode()+raw).hexdigest()[:20],relative_path=relative_path,sha256=hashlib.sha256(raw).hexdigest())
    read_material(repo,material)
    return material
