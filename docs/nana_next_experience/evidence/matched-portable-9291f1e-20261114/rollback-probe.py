import json,sys,sqlite3
from pathlib import Path
bundle=Path(sys.argv[1]).resolve();phase=sys.argv[2]
assert Path(sys.prefix).resolve()==bundle/'.venv';sys.dont_write_bytecode=True;sys.path.insert(0,str(bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
home=Path('/tmp/q929g/learn-return/home');db=home/'subject/self.db'
with sqlite3.connect(db) as c:high=c.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
with LifeApplication(home,clock=VirtualClock(high)) as app:
 app.pause();r=app.runtime
 if phase=='prepare':
  for label,field,kind in [('question','question','private_question'),('plan','plan','private_plan'),('tendency','tendency','private_tendency')]:
   class Own:
    descriptor='SYNTHETIC isolated rollback state preparation'
    def propose(self,request):
     v=json.loads(AnalyticalFixturePort().propose(request));v[kind]={'topic':'rollback.'+label,field:'SYNTHETIC rollback '+label};return json.dumps(v)
   r.subject.cognize(SubjectInput(source_key='synthetic.rollback.'+label,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',topic='rollback.'+label,observed_at_us=r.clock.utc_now_us()),model=Own(),authority=r.authority,policy=app.policy)
  rid,q=next((rid,q) for rid,q in candidates(r.store,'project-work',('PROJECT','PERSONAL')) if q.topic=='rollback.question')
  class Pause:
   descriptor='SYNTHETIC current C explicit pause before binary rollback'
   def propose(self,request):
    v=json.loads(AnalyticalFixturePort().propose(request));v['private_question']={'topic':q.topic,'question':q.content_summary,'revises_record_id':rid,'activity_state':'PAUSED'};return json.dumps(v)
  r.subject.cognize(SubjectInput(source_key='synthetic.rollback.pause',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',topic=q.topic,observed_at_us=r.clock.utc_now_us()),model=Pause(),authority=r.authority,policy=app.policy)
 now={'identity_id':r.identity_id,'lineage':None,
      'private':[(rid,q.model_dump(mode='json')) for rid,q in candidates(r.store,'project-work',('PROJECT','PERSONAL')) if q.topic.startswith('rollback.')],
      'requests':len(r.store.all('cognitive_requests')),'cycles':len(r.store.all('subject_cycles')),'actions':len(r.store.all('actions')),'learning_jobs':len([j for j in r.store.all('jobs') if j['work_kind']=='LEARNING'])}
 from nana_core.life.live_api.supervisor import existing_identity
 now['lineage']=existing_identity(home)[1]
 assert len(now['private'])==3 and {v['activity_state'] for _,v in now['private']}=={'ACTIVE','PAUSED'}
 now=json.loads(json.dumps(now))
 baseline=Path('/tmp/nana-929-rollback-state.json')
 if phase=='prepare':baseline.write_text(json.dumps(now,sort_keys=True))
 else:assert now==json.loads(baseline.read_text()),(phase,now,json.loads(baseline.read_text()))
report={'phase':phase,'source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'same_identity_lineage_and_private_state':True,'no_new_cognitive_requests_or_cycles_or_actions_after_prepare':phase!='prepare','request_count':now['requests'],'cycle_count':now['cycles'],'learning_jobs':now['learning_jobs'],'owner':'STOPPED_BETWEEN_EACH_PROCESS','real_provider_calls':0}
Path('/tmp/nana-929-rollback-'+phase+'.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
