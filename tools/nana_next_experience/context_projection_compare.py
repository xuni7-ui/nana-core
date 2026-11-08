"""Compare restricted context assembly on one disposable synthetic Subject.

Baseline source is pinned; no model, network, external memories or production.
Actual serialization and source selection must match exactly in every pair.
"""
import json
import math
import statistics
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from unittest.mock import patch

from nana_core.continuity.context import ContextAssembler, ContextPolicy, ContextRequest
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.presence.authority import VirtualClock
from tests.independent_life.conftest import initialize


BASELINE='ef14a72e08ea5f5ec4b58c353e123070ce99f082'
ROOT=Path(__file__).resolve().parents[2]


def main():
    source=subprocess.check_output(['git','show',BASELINE+':src/nana_core/continuity/context.py'],cwd=ROOT)
    module=types.ModuleType('nana_core.continuity._selection_comparison_baseline')
    module.__package__='nana_core.continuity';sys.modules[module.__name__]=module
    exec(compile(source,'<pinned-baseline>','exec'),module.__dict__)
    durations={name:[] for name in ('baseline','candidate')}
    counts={name:{'world':0,'lessons':0} for name in durations}
    with tempfile.TemporaryDirectory(prefix='nana-context-comparison-',dir='/tmp') as tmp:
        home=Path(tmp)/'home';initialize(home,active=0)
        with LifeApplication(home,clock=VirtualClock()) as app:
            app.pause()
            note=save(app,text='SYNTHETIC planning note: ORCHID gathering is on Friday.',privacy='PROJECT',request_id='compare.note')['memory_id']
            req=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='world.social',
                task='SYNTHETIC review ORCHID',task_privacy_class='PROJECT',query_terms=('ORCHID',),
                max_input_tokens=8192,output_reserve_tokens=512)
            policy=ContextPolicy(policy_id='synthetic.projection',allowed_scopes=('project-work',),readable_privacy=('PROJECT',))
            world_original=WorldModel.snapshot
            classes={'baseline':module.ContextAssembler,'candidate':ContextAssembler}
            for scenario in ('pinned','source_only'):
                for n in range(12):
                    outcomes={}
                    for arm in (('baseline','candidate') if n%2==0 else ('candidate','baseline')):
                        cls=classes[arm];lesson_original=cls._lessons
                        def world_counted(instance,*args,**kwargs):
                            counts[arm]['world']+=1
                            return world_original(instance,*args,**kwargs)
                        def lessons_counted(instance,*args,**kwargs):
                            counts[arm]['lessons']+=1
                            return lesson_original(instance,*args,**kwargs)
                        with patch.object(WorldModel,'snapshot',world_counted),patch.object(cls,'_lessons',lessons_counted):
                            start=time.perf_counter();assembler=cls(app.runtime.store,app.runtime.authority)
                            options={'pinned_only':True,'conversation_topic':'daily'} if scenario=='pinned' else {'source_only':True,'required_memory_ids':(note,)}
                            package=assembler.assemble(req,policy,**options)
                            assembler.validate(package,req,policy)
                            durations[arm].append((time.perf_counter()-start)*1000)
                            outcomes[arm]=package.model_dump(mode='json')
                    if outcomes['baseline']!=outcomes['candidate']:
                        raise AssertionError('CONTEXT_OR_SOURCE_DEPENDENCIES_DIFFER')
    result={'qualification':'SYNTHETIC_SAME_SUBJECT_NOT_REAL_DIALOGUE',
        'baseline_commit':BASELINE,'pairs_per_scenario':12,'scenarios':['pinned','source_only'],
        'exact_package_and_source_equality':True,'model_calls':0,'provider_tokens':'NOT_RUN','real_cost':'NOT_RUN',
        'arms':{}}
    for arm,values in durations.items():
        result['arms'][arm]={'samples':len(values),'p50_ms':statistics.median(values),
            'p95_ms':sorted(values)[math.ceil(.95*len(values))-1],**counts[arm]}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
