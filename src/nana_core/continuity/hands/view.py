"""Source-filtered projection of the original Store, never a life authority."""
import json
from ...contracts import CoreError
from ..records import RecordService
from ..journal import living_journal
from ..subject.growth_life import opportunities
from ..subject.context_fit import depth_boundary

def hands_board(app):
    r=app.runtime;records=RecordService(r.store);work=app.work;tasks=[];learning=[];shared=[];outcomes=[]
    try:work.port.assert_owned();health='AVAILABLE'
    except (CoreError,OSError):health='TARGET_UNAVAILABLE_NO_FALLBACK'
    for t in work.port.tasks.values():
        goal=work.goal_for(t.task_id)
        tasks.append({'task_type':t.kind,'source_path':'hands://'+work.port.target.instance_id+'/'+t.task_id,'state':goal['state'] if goal else 'AVAILABLE_NOT_ADOPTED','source_state':health,'task_id':t.task_id})
    for row in r.store.db.execute("SELECT * FROM lessons WHERE task_class IN ('owned-document','owned-form') AND state IN ('ACTIVE','SUSPENDED') ORDER BY rowid DESC LIMIT 8"):
        try:
            head=records.read(row['record_id'])
            if head['scope']!='project-work' or not records.current_support(row['record_id']):continue
            rule=head['payload']['rule'];learning.append({'lesson_id':row['lesson_id'],'state':row['state'],'method':rule.get('method'),'evidence_record_id':rule.get('trial_record_id'),'reason':'Real externally verified task failure; practice/evaluation preparation trials plus later actual use'})
        except CoreError:continue
    for row in r.store.db.execute("SELECT data_json FROM events WHERE kind='living.goal_step_completed' AND json_extract(data_json,'$.data.operator_id')='apply' ORDER BY seq DESC LIMIT 16"):
        x=json.loads(row[0])['data']
        try:
            m=records.memory.read(x['memory_id'])
            if m['scope']!='project-work' or m['privacy_class'] not in app.policy.readable_privacy:continue
            body=json.loads(m['text']);outcomes.append({'action_id':x['action_id'],'experience_id':x['experience_id'],'goal_quality':'SUCCESS' if x['quality'] else 'FAILURE_VERIFIED','effect':'VERIFIED_APPLICATION_CHANGE','verify_paths':body['verify_paths'],'source_memory_id':m['memory_id'],'target_revision':body['revision']})
        except (CoreError,KeyError):continue
    for view in opportunities(r.store,scope='project-work',privacy_classes=app.policy.readable_privacy):
        closed,_,_=depth_boundary(r.store,'project-user','project-work',view.topic,app.policy.readable_privacy)
        if not closed:shared.append({'topic':view.topic,'source_memory_ids':view.source_memory_ids,'status':'C_MAY_SHARE_NOT_DELIVERED'})
    extension=work.skills;skills=[] if not extension else [{'task':task,'record_id':rid,'realm':'BWRAP_LOCAL_DATA_ONLY','installed':False} for task,rid in extension.engine.active()]
    return {'derived':True,'identity_id':r.identity_id,'materials':tasks,'learning':learning,'skills':skills,'shared_context':shared,'external_outcomes':outcomes,
        'unknown_actions':[{'action_id':a['action_id'],'state':a['state']} for a in r.store.db.execute("SELECT action_id,state FROM actions WHERE state IN ('DISPATCHING','UNKNOWN','PENDING_VERIFY') ORDER BY rowid DESC LIMIT 16")],
        'journal':living_journal(r.store,scopes=('project-work',),privacy_classes=app.policy.readable_privacy,limit=16).model_dump(mode='json'),
        'target_scope':{'binding':work.port.target.binding,'kind':'OWNED_DEV_APPLICATION_PROCESS','uid_checked':True,'pid_start_checked':True,'scope':'FINITE_DOCUMENT_FORM_CONTENT_FILES_ONLY','health':health},
        'first_life_experience_ready':'NOT_READY_REAL_NATURAL_DIALOGUE_NOT_REVIEWED','pause':r.work.paused,'report_directory':work.port.target.workspace,'external_delivery':'NO_SOCIAL_SEND','portable':'IDENTITY_EXPERIENCE_LESSONS','host_local':'PROCESS_BINDING_GRANTS_APPLICATION_FILES','rebuildable':'THIS_VIEW','current_silence_reason':'No forced sharing; bounded owned tasks, C may choose rest/defer/no-action'}
