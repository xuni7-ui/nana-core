"""Read-only-cohort counterexample; only fresh synthetic DEV material."""
import json,itertools,uuid,tempfile
from pathlib import Path
from unittest.mock import patch
from nana_core.life.application import LifeApplication
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject import SubjectInput
from tests.person_self.conftest import initialize
from tests.person_self.test_dream_recall import source

with tempfile.TemporaryDirectory(prefix='nana-review-cues-',dir='/tmp') as folder:
 home=Path(folder)/'home';initialize(home)
 with LifeApplication(home) as app:
  app.pause();r=app.runtime
  mid=source(app,'retained-summary-parent','SYNTHETIC original stable source.',importance=.9)
  rid=r.work.maintenance._offer((r.subject.records.memory.read(mid),),'project-work','INCREMENTAL')
  serial=itertools.count(1)
  with patch('nana_core.continuity.memory.uid',side_effect=lambda:str(uuid.UUID(int=next(serial)))):
   for i in range(130):
    cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='cohort-'+str(i),motivation_source='CURIOSITY',possible_behaviors=('WATCH',))
    source(app,'cohort-'+str(i),cue.model_dump_json(),predicate_key='concern.cohort.'+str(i))
   event=SubjectInput(source_key='synthetic.cohort-pause',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
    scope='project-work',privacy_class='PROJECT',source_memory_ids=(mid,),memory_review_id=rid,observed_at_us=r.clock.utc_now_us())
   class Rest:
    descriptor='synthetic-cohort-pause'
    def propose(self,request):
     value=json.loads(AnalyticalFixturePort().propose(request));value['preferred_behavior']='REST';return json.dumps(value)
   cycle=r.subject.cognize(event,model=Rest(),authority=r.authority,policy=app.policy);r.work.after_cycle(cycle,event)
   job=r.store.db.execute("SELECT * FROM jobs WHERE occurrence_key=?",('maintenance-review:'+rid,)).fetchone();assert job['state']=='PAUSED'
   before=r.work._memory_review_blockers('project-work');writes=r.store.db.total_changes
   assert r.work._memory_review_blockers('project-work')==before and r.store.db.total_changes==writes
   cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='a-new-current-concern',motivation_source='CURIOSITY',possible_behaviors=('WATCH',))
   added=source(app,'cohort-new',cue.model_dump_json(),predicate_key='concern.cohort.new')
   sample=r.store.db.execute("SELECT memory_id FROM memories WHERE substr(predicate_key,1,8)='concern.' ORDER BY memory_id LIMIT 129").fetchall()
   assert added not in {row[0] for row in sample}
   after=r.work._memory_review_blockers('project-work');app.pause(False)
   activity=r.work.opportunity();current=r.store.one('jobs',job['job_id'])
   print(json.dumps({'source_head':'9c8fe1e','eligible_concern_rows':131,'new_concern_outside_first129':True,
    'condition_changed_after_new_concern':after!=before,'same_condition_read_only':True,
    'job_state_after_new_concern':current['state'],'review_enqueued':bool(activity and activity.get('review_enqueued')==rid),
    'original_candidate_supported':bool(r.work.maintenance.candidate(rid)),
    'model_calls':len(r.store.all('cognitive_requests')),'external_actions':len(r.store.all('actions'))}))
