"""Same live synthetic Store, exact old/new policy, no write or model in timing."""
import ast,hashlib,json,statistics,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
root=Path('/workspace/nana-next-refinement-work');sys.path.insert(0,str(root/'src'));sys.path.insert(1,str(root))
import nana_core.continuity.lived_language as language
from nana_core.continuity.memory import MemoryService
source=subprocess.check_output(['git','show','46fa16b1a5f302b3fa8d32a97d1bed35342f2eb6:src/nana_core/continuity/lived_language.py'],cwd=root).decode()
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='expression_policy')
scope=dict(language.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed46fa-expression-policy>','exec'),scope)
old=scope['expression_policy'];new=language.expression_policy;done=False;original_read=MemoryService.read
def profiled(store,**args):
    global done
    if not done and store.db.execute("SELECT count(*) FROM lessons WHERE task_class='interaction.expression' AND state='ACTIVE'").fetchone()[0]==17:
        done=True;writes=store.db.total_changes;measure={name:[] for name in ('old','new')};reads={}
        for i in range(5):
            for name,fn in ([('old',old),('new',new)] if i%2==0 else [('new',new),('old',old)]):
                count=[0]
                def counted(self,*a,**kw):count[0]+=1;return original_read(self,*a,**kw)
                with patch.object(MemoryService,'read',counted):
                    start=time.perf_counter_ns();cpu=time.process_time_ns();result=fn(store,**args)
                    measure[name].append({'wall_ms':(time.perf_counter_ns()-start)/1e6,'cpu_ms':(time.process_time_ns()-cpu)/1e6,'memory_read_calls':count[0],'has_rule':bool(result.get('rule'))})
        assert store.db.total_changes==writes
        proof={'scope':'same actual synthetic Core Store / 17 active lessons, not large-scale timing',
            'base':'46fa16b1a5f302b3fa8d32a97d1bed35342f2eb6','old_function_sha256':hashlib.sha256(ast.get_source_segment(source,node).encode()).hexdigest(),
            'measurements':measure,'median_wall_ms':{name:statistics.median(x['wall_ms'] for x in values) for name,values in measure.items()},
            'median_read_calls':{name:statistics.median(x['memory_read_calls'] for x in values) for name,values in measure.items()},
            'db_writes':0,'model_calls_within_profile':0,'provider_tokens':None}
        Path('/workspace/nana-expression-policy-profile.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
    return new(store,**args)
language.expression_policy=profiled
import pytest
result=pytest.main(['-q','-s','-o','pythonpath='+str(root/'src'),
    'tests/person_self/test_expression_lesson_population.py::test_later_qualified_original_candidate_reaches_normal_dialogue_without_population_crowding[16]'])
assert done
sys.exit(result)
