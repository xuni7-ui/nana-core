"""Same real synthetic Store, same selector outputs, local training-memo ablation."""
import json,statistics,time,sys
from pathlib import Path
from unittest.mock import patch
from nana_core.continuity.subject import growth_life
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.presence.authority import VirtualClock
from tools.nana_vision_first.demo import source
from tests.person_self.test_growth_inner_choice import grown
root=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/nana-growth-context-read-profile');root.mkdir(exist_ok=False)
outputs=[];project=growth_life.project;read=MemoryService.read
with grown(root,VirtualClock()) as (r,view,origin,reuse,lesson):
 review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
 for i in range(32):
  mid=source(r,'profile-practice-'+str(i),{'strategy_episode':{'episode_key':'profile-practice-'+str(i),
    'lesson_id':lesson,'case':numeric_learning().practice[0].model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
  review.assess(lesson,mid,authority=r.authority)
 counts={'calls':0,'reads':0}
 def measured_read(self,*a,**kw):counts['reads']+=1;return read(self,*a,**kw)
 def tracked(*a,**kw):counts['calls']+=1;return project(*a,**kw)
 def no_memo(*a,**kw):kw.pop('_training_contexts',None);return tracked(*a,**kw)
 before=r.store.db.total_changes;requests=len(r.store.all('cognitive_requests'))
 for _ in range(5):
  for mode,fn in [('without_training_memo',no_memo),('with_training_memo',tracked)]:
   counts={'calls':0,'reads':0};start=time.perf_counter();cpu=time.process_time()
   with patch.object(MemoryService,'read',measured_read),patch.object(growth_life,'project',fn):
    result=growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))
   assert [v.assessment_id for v in result]==[view.assessment_id]
   outputs.append({'mode':mode,'wall_ms':(time.perf_counter()-start)*1000,'cpu_ms':(time.process_time()-cpu)*1000,**counts})
 assert r.store.db.total_changes==before and len(r.store.all('cognitive_requests'))==requests
print(json.dumps({'scope':'SAME_SYNTHETIC_CORE_STORE_LOCAL_READ_COST_NOT_PROVIDER_TOKENS','samples':outputs,
 'writes':0,'extra_model_requests':0,'sqlite_indexes':'same_two_rebuildable_lookups_both_modes'},indent=2))
