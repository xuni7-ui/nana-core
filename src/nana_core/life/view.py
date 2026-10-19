"""On-demand source-filtered life board; rebuilt from original authoritative data."""
import json
from ..contracts import CoreError
from ..continuity.records import RecordService
from ..continuity.memory import MemoryService
from ..continuity.journal import living_journal
from ..continuity.subject.growth_life import opportunities
from ..continuity.subject.context_fit import depth_boundary
from ..continuity.project_work.port import read_material


def life_board(app):
    r=app.runtime;records=RecordService(r.store);materials=[];learned=[];facts=[]
    for m in app.config.materials:
        goal=app.work.goal_for(m.material_id)
        root=r.store.db.execute("SELECT m.memory_id,m.lifecycle FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.material' AND e.source_reference=? ORDER BY m.rowid DESC LIMIT 1",('input:'+m.material_id,)).fetchone()
        supported=True
        if root:
            try:MemoryService(r.store).read(root[0])
            except CoreError:supported=False
        try:read_material(app.config.project_root,m);source='CURRENT' if supported else 'WITHDRAWN'
        except CoreError as exc:source=exc.code
        materials.append({'material_id':m.material_id,'task_type':m.task_type,'source_path':m.relative_path,'source_state':source,'source_memory_id':root[0] if root else None,
            'state':goal['state'] if goal else 'AVAILABLE_NOT_ADOPTED','estimated_cost':'BOUNDED_LOCAL_NO_PROVIDER_CALL','reversibility':'REPORTS_ONLY_NO_SOURCE_WRITES','execution_authority':'ORIGINAL_GATES_REQUIRED',
            'reason':'Prior C choice' if goal else 'Explicit host manifest opportunity; C may defer or decline'})
    for row in r.store.db.execute("SELECT * FROM lessons WHERE state IN ('ACTIVE','SUSPENDED') ORDER BY rowid DESC LIMIT 8"):
        head=r.store.one('continuity_records',row['record_id'])
        if head['scope']!='project-work' or head['privacy_class'] not in app.policy.readable_privacy or head['lifecycle']!='ACTIVE' or not records.current_support(row['record_id']):continue
        rule=records.read(row['record_id'])['payload'].get('rule',{})
        learned.append({'lesson_id':row['lesson_id'],'domain':row['task_class'],'state':row['state'],'method':rule.get('method'),'evidence_record_id':rule.get('trial_record_id'),'claim':'FINITE_RECIPE_SELECTION_NOT_GENERAL_ALGORITHM_INVENTION'})
    for view in opportunities(r.store,scope='project-work',privacy_classes=app.policy.readable_privacy):
        closed,_,_=depth_boundary(r.store,'project-user','project-work',view.topic,app.policy.readable_privacy)
        if not closed:facts.append({'topic':view.topic,'lesson_id':view.lesson_id,'support_memory_ids':view.source_memory_ids,'status':'SUPPORTED_SHARED_CONTEXT_CANDIDATE_NOT_DELIVERED'})
    extension=r.work.skill_development
    skills=[] if not extension or not extension.engine else [{'task':task,'record_id':rid,'realm':'ISOLATED_DATA_ONLY','installed':False} for task,rid in extension.engine.active()]
    return {'derived':True,'coverage':'BOUNDED_CURRENT_SUPPORT_ONLY','identity_id':r.identity_id,'materials':materials,'learning':learned,'skills':skills,'shared_context':facts,
        'journal':living_journal(r.store,scopes=('project-work',),privacy_classes=app.policy.readable_privacy,limit=16).model_dump(mode='json'),
        'first_life_experience_ready':'NOT_READY_REAL_PROVIDER_AND_HUMAN_REVIEW_NOT_RUN','pause':r.work.paused,'report_directory':str(app.home/'reports'),'raw_dialogue_retention':'MEMORY_ONLY_BOUNDED_UNTIL_EXIT',
        'portable':'IDENTITY_MEMORY_EXPERIENCE_LESSONS','rebuildable':'THIS_BOARD_JOURNAL','host_local':'PROVIDERS_MANIFEST_GRANTS_PAUSE_RUNTIME_LEASE','external_delivery':'DISABLED'}
