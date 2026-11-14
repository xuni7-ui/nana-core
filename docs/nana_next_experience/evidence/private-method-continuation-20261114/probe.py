"""Same owned HTTP continuation test, with metadata-only resource observation."""
import json,sys,time
from pathlib import Path
import pytest
from nana_core.continuity.subject import SubjectLoop
from nana_core.continuity.world_loop.cognition import CognitionSession
from tests.person_self.test_private_method_continuation import test_normal_taskless_d_uses_only_current_explicit_private_method_selection as probe
root=Path(sys.argv[1]);report_path=Path(sys.argv[2]);assert root.is_absolute() and str(root).startswith(('/tmp/','/dev/shm/')) and not root.exists() and not report_path.exists();root.mkdir()
execute=CognitionSession.execute;cognize=SubjectLoop.cognize;requests=[];cycles=[]
def family(path):return sum(p.stat().st_blocks*512 for p in (path,Path(str(path)+'-wal'),Path(str(path)+'-shm')) if p.exists())
def observed_execute(self,rid):
 result=execute(self,rid);row=self.store.one('cognitive_requests',rid);payload=self.records.read(row['record_id'])['payload'];body=payload['request'];package=json.loads(body['context_json'])
 requests.append({'state':result['state'],'wire_input_bytes':row['input_bytes'],'wire_output_bytes':row['output_bytes'],'reserved_bytes':row['reserved_bytes'],'lesson_blocks':sum(b['kind']=='LESSON' for b in package['blocks']),'budget':body['budget'],'fixture_token_accounting':payload.get('token_accounting')});return result
def observed_cognize(self,*args,**kw):
 provider=hasattr(kw.get('model'),'session');before=family(self.store.path);wall=time.perf_counter_ns();cpu=time.process_time_ns();result=cognize(self,*args,**kw)
 if provider:cycles.append({'behavior':result.intention.behavior,'stance':result.judgment.stance,'wall_us':(time.perf_counter_ns()-wall)//1000,'cpu_us':(time.process_time_ns()-cpu)//1000,'family_allocated_bytes_delta':family(self.store.path)-before,'goals':len(self.store.all('goals')),'actions':len(self.store.all('actions')),'provider_ledger_rows':len(self.store.all('cognitive_requests')),'fixture_ledger_rows':len(self.store.all('runtime_cognition_calls'))})
 return result
CognitionSession.execute=observed_execute;SubjectLoop.cognize=observed_cognize
failed=False
try:
 with pytest.MonkeyPatch.context() as patch:probe(root,patch,'active')
except AssertionError:failed=True
report={'active_continuation_assertion_failed':failed,'requests':requests,'cycles':cycles,'real_model_calls':0,'commercial_tokens':None,'commercial_cost':None,'limits':'One owned HTTP fixture; character-framing tokenizer, not commercial tokens/P95/long-term growth or installation.'}
with report_path.open('x') as out:out.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
