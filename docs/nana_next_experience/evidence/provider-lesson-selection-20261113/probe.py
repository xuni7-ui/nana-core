"""Measure the existing active-lesson behavioral test; owned HTTP only."""
import json,time,sys
from pathlib import Path
from nana_core.continuity.subject import SubjectLoop
from nana_core.continuity.world_loop.cognition import CognitionSession
from tests.person_self.test_provider_subject_learning import test_original_qualified_lesson_changes_a_later_self_choice_and_withdrawal_removes_its_influence as run
root=Path(sys.argv[1]);report_path=Path(sys.argv[2]);assert root.is_absolute() and str(root).startswith(('/tmp/','/dev/shm/')) and not root.exists() and not report_path.exists();root.mkdir()
original=CognitionSession.execute;original_c=SubjectLoop.cognize;requests=[];cycles=[]
def size(path):return sum(p.stat().st_blocks*512 for p in (path,Path(str(path)+'-wal'),Path(str(path)+'-shm')) if p.exists())
def execute(self,rid):
 result=original(self,rid);row=self.store.one('cognitive_requests',rid);body=self.records.read(row['record_id'])['payload']['request'];package=json.loads(body['context_json'])
 requests.append({'state':result['state'],'input_bytes':row['input_bytes'],'output_bytes':row['output_bytes'],'reserved_bytes':row['reserved_bytes'],'lesson_blocks':sum(b['kind']=='LESSON' for b in package['blocks']),'budget':body['budget']});return result
def cognize(self,*args,**kw):
 before=size(self.store.path);wall=time.perf_counter_ns();cpu=time.process_time_ns();result=original_c(self,*args,**kw)
 cycles.append({'behavior':result.intention.behavior,'stance':result.judgment.stance,'wall_us':(time.perf_counter_ns()-wall)//1000,'cpu_us':(time.process_time_ns()-cpu)//1000,'family_allocated_bytes_delta':size(self.store.path)-before,'goals':len(self.store.all('goals')),'provider_ledger_rows':len(self.store.all('cognitive_requests')),'fixture_ledger_rows':len(self.store.all('runtime_cognition_calls')),'actions':len(self.store.all('actions'))});return result
CognitionSession.execute=execute;SubjectLoop.cognize=cognize
assertion_failed=False
try:run(root,'active')
except AssertionError:assertion_failed=True
report={'active_behavior_assertion_failed':assertion_failed,'requests':requests,'cycles':cycles,'real_model_calls':0,'actual_commercial_tokens':None,'actual_commercial_cost':None,'limits':'One same-input/same-budget owned HTTP probe. Qualified fixture lesson and deterministic proposer, no real LLM, P95, installation or long-term effect.'}
with report_path.open('x') as out:out.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
