import ast,json,time,statistics,hashlib,subprocess,sys
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.subject import SubjectInput,PreferenceSignal
from nana_core.continuity.subject.growth import Growth
from tests.person_self.conftest import initialize
root=Path('/workspace/nana-next-refinement-work');home=Path('/dev/shm/nana-growth-signal-profile-home-2')
if not home.exists():
 initialize(home)
 with LifeApplication(home,clock=VirtualClock()) as app:
  app.pause();r=app.runtime
  for i in range(96):
   r.subject.run(SubjectInput(source_key='synthetic.growth-profile.'+str(i),kind='PLAY',origin='ENVIRONMENT',entity_id='project-user',scope='project-work',privacy_class='PERSONAL' if i%4<2 else 'PROJECT',observed_at_us=r.clock.utc_now_us(),text='SYNTHETIC independent lived preference occurrence '+str(i),preference_signal=PreferenceSignal(topic='own-interest-'+str(i//2),direction='SUPPORT',interpretation='SYNTHETIC a personal exploratory preference, not a command')))
# Read-only workload inside the original owner; no new SubjectLoop/model/action.
with LifeApplication(home,clock=VirtualClock()) as app:
 app.pause();store=app.runtime.store;growth=Growth(store)
 source=subprocess.check_output(['git','show','d5c0a42:src/nana_core/continuity/subject/growth.py'],cwd=root,text=True)
 tree=ast.parse(source);oldtype=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Growth')
 old={}
 for node in oldtype.body:
  if isinstance(node,ast.FunctionDef) and node.name in {'assertion_view','assertions'}:
   code=compile(ast.Module(body=[node],type_ignores=[]),'<fixed-d5c0a42-growth>','exec');from nana_core.continuity.subject import growth as growth_module
   ns=dict(vars(growth_module));exec(code,ns);old[node.name]=ns[node.name]
 class OriginalGrowth(Growth):pass
 for name,method in old.items():setattr(OriginalGrowth,name,method)
 before=store.snapshot();writes=store.db.total_changes
 scenes=[('all',None,('PUBLIC','PROJECT','PERSONAL','SECRET')),('personal',None,('PERSONAL',)),('project',None,('PROJECT',)),('kind','SELF_BELIEF',('PUBLIC','PROJECT','PERSONAL','SECRET')),('empty',None,())]
 records=[]
 for name,kind,privacy in scenes:
  expected=OriginalGrowth(store).assertions('project-work',kind,privacy_classes=privacy)
  actual=growth.assertions('project-work',kind,privacy_classes=privacy)
  assert actual==expected,(name,'different assertion output')
  values=[]
  for iteration in range(6):
   for variant,service in ([('old',OriginalGrowth(store)),('new',growth)] if iteration%2==0 else [('new',growth),('old',OriginalGrowth(store))]):
    vm=[0];statements=[]
    def progress():vm[0]+=100;return 0
    store.db.set_progress_handler(progress,100);store.db.set_trace_callback(statements.append)
    wall=time.perf_counter_ns();cpu=time.process_time_ns();result=service.assertions('project-work',kind,privacy_classes=privacy);cpu=time.process_time_ns()-cpu;wall=time.perf_counter_ns()-wall
    store.db.set_trace_callback(None);store.db.set_progress_handler(None,0)
    assert result==expected
    values.append({'variant':variant,'wall_ms':wall/1e6,'cpu_ms':cpu/1e6,'vm_approx':vm[0],'sql_count':len(statements),'unfiltered_signal_selects':sum('SELECT * FROM assertion_signals ORDER BY rowid' in s for s in statements),'indexed_signal_selects':sum('FROM assertion_signals WHERE assertion_id=' in s for s in statements)})
  records.append({'scene':name,'assertions':len(actual),'result_digest':hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest(),'samples':values})
 import sqlite3
 from nana_core.life.inspector import _ReadView
 db=sqlite3.connect('file:'+str(store.path)+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 try:
  view=_ReadView(db,store.path,'project-work',('PERSONAL',))
  old_view=OriginalGrowth(view).assertions('project-work',privacy_classes=('PERSONAL',))
  new_view=Growth(view).assertions('project-work',privacy_classes=('PERSONAL',))
  assert new_view==old_view and len(new_view)==24
 finally:db.close()
 explain=[tuple(row) for row in store.db.execute('EXPLAIN QUERY PLAN SELECT * FROM assertion_signals WHERE assertion_id=? ORDER BY rowid',(store.all('self_assertions')[0]['assertion_id'],))]
 assert store.snapshot()==before and store.db.total_changes==writes
 print(json.dumps({'source_anchor':'d5c0a42c65bc348074952c9663418c636c1817f6','assertions':len(store.all('self_assertions')),'signals':len(store.all('assertion_signals')),'scenes':records,'read_only_personal_assertions':len(new_view),'query_plan':explain,'writes':0,'provider_calls':0,'actions':len(store.all('actions')),'goals':len(store.all('goals'))},indent=2))
