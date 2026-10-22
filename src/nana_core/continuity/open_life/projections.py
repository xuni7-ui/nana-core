"""Rebuildable advanced views; no shadow goal, affect or learning authority."""
import json
from collections import defaultdict
from ...storage import digest
from ..records import RecordService
from ..subject.experience_need import project_need
from ..relational.projections import social_appetite


def advanced_view(store,*,scope,privacy):
    records=RecordService(store)
    def visible(rid):
        h=store.one('continuity_records',rid)
        return bool(h and h['scope']==scope and h['privacy_class'] in privacy and h['lifecycle']=='ACTIVE' and records.current_support(rid))
    problems=[];failures=defaultdict(list);goals=[];learning=[];meta=[]
    for row in store.db.execute('SELECT * FROM experiences ORDER BY created_at_us DESC LIMIT 32'):
        if row['outcome']=='FAILURE' and visible(row['record_id']):failures[row['task_class']].append(row)
    for domain,rows in failures.items():
        need=project_need(store,domain,scope=scope,privacy_classes=privacy)
        if need.state!='OPEN':continue
        problems.append({'problem_id':'failure.'+digest([domain,[r['experience_id'] for r in rows]])[:24],
            'kind':'REPEATED_CAPABILITY_FAILURE' if len(rows)>=2 else 'VERIFIED_CAPABILITY_GAP',
            'state':'CANDIDATE_NOT_ADOPTED','source_record_ids':[r['record_id'] for r in rows[:4]],'domain':domain})
    for row in store.db.execute('SELECT * FROM goals ORDER BY rowid DESC LIMIT 32'):
        b=json.loads(row['body_json']);rid=b.get('record_id')
        if not rid or not visible(rid):continue
        obj=records.read(rid)['payload'].get('objective',{})
        goals.append({'goal_id':row['goal_id'],'state':row['state'],'horizon':'DORMANT' if row['state']=='SUSPENDED' else 'ABANDONED' if row['state']=='ABANDONED' else obj.get('horizon','SHORT'),
            'parent_id':obj.get('parent_id'),'depends_on':obj.get('depends_on',[]),'deadline_us':obj.get('deadline_us'),
            'why_source_record_id':rid,'review_after_us':obj.get('review_after_us'),'review_condition':'SOURCE_CHANGE_OR_VERIFIED_OUTCOME','not_new_goal_authority':True})
        if row['state']=='BLOCKED':problems.append({'problem_id':'blocked.'+row['goal_id'],'kind':'GOAL_PATH_BLOCKED','state':'CANDIDATE_NOT_ADOPTED','source_record_ids':[rid]})
    for row in store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 16"):
        if not visible(row['record_id']):continue
        b=records.read(row['record_id'])['payload'];results=b.get('results',{})
        learning.append({'work_id':row['job_id'],'state':row['state'],'stage':b.get('stage'),'source_record_id':row['record_id'],
            'baseline':results.get('BASELINE',{}).get('passed'),'evaluation':results.get('EVALUATE',{}).get('passed'),'transfer':results.get('TRANSFER',{}).get('passed')})
        if {'BASELINE','EVALUATE','TRANSFER'}<=results.keys():
            # A sourced strategy observation, not automatic rewriting of the
            # learning evaluator/algorithm or a self-certified active Lesson.
            meta.append({'kind':'LEARNING_STRATEGY_CANDIDATE','state':'SUPPORTED_TRIAL_OBSERVATION',
                'method':b.get('selected_method'),'improved':results['EVALUATE']['passed']>results['BASELINE']['passed'],
                'transfer_passed':results['TRANSFER']['all_passed'],'source_record_id':row['record_id'],
                'changes_evaluator':False,'automatically_adopted':False})
    active=sum(g['state']=='ACTIVE' for g in goals)
    appetite=social_appetite(store,scope=scope,privacy_classes=privacy)
    return {'derived':True,'problem_candidates':problems[:16],'goals':goals,'learning_cycles':learning,
        'learning_strategy_candidates':meta,'rhythm':{'rest_need':'PRESENT' if active>=4 else 'NOT_ESTABLISHED',
        'unfinished_task_pull':'PRESENT' if active else 'NOT_ESTABLISHED','curiosity':'SOURCE_REQUIRED',
        'low_stimulation':'NOT_ESTABLISHED','exploration_desire':'SOURCE_REQUIRED','social_appetite':appetite.state},
        'execution_authority':False,'coverage':'BOUNDED_CURRENT_SUPPORT'}
