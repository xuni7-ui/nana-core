"""Original paused maintenance sees eligible changes beyond its bounded cue sample."""
import itertools
import json
import uuid
from unittest.mock import patch

import pytest
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from .test_dream_recall import source


class Rest:
    descriptor='synthetic-paused-review'
    def propose(self,request):
        value=json.loads(AnalyticalFixturePort().propose(request))
        value['preferred_behavior']='REST'
        return json.dumps(value)


def pause_candidate(app,key):
    r=app.runtime
    mid=source(app,'review-parent-'+key,'SYNTHETIC retained source '+key,importance=.9)
    rid=r.work.maintenance._offer((r.subject.records.memory.read(mid),),'project-work','INCREMENTAL')
    event=SubjectInput(source_key='synthetic.paused-review.'+key,kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',
        source_memory_ids=(mid,),memory_review_id=rid,observed_at_us=r.clock.utc_now_us())
    cycle=r.subject.cognize(event,model=Rest(),authority=r.authority,policy=app.policy)
    r.work.after_cycle(cycle,event)
    job=r.store.db.execute('SELECT * FROM jobs WHERE occurrence_key=?',('maintenance-review:'+rid,)).fetchone()
    assert job['state']=='PAUSED'
    return rid,dict(job)


def cue(app,key,*,scope='project-work',entity='project-user',privacy='PROJECT',predicate=None):
    memory=MemoryService(app.runtime.store)
    if not memory.store.one('entities',entity):memory.entity(entity,'PERSON')
    text=ConcernCue(cue_kind='OPPORTUNITY',topic_key=key,motivation_source='CURIOSITY',possible_behaviors=('WATCH',)).model_dump_json()
    eid=memory.capture(EvidenceInput(provenance=Provenance(domain='SYNTHETIC_ONLY',source_namespace='synthetic.review-condition',
        source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,privacy_class=privacy,
        event_time_us=11,observed_time_us=app.clock.utc_now_us()))
    return memory.add(MemoryCandidate(entity_id=entity,scope=scope,memory_type=MemoryType.EPISODIC,
        epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,predicate_key=predicate or 'concern.review.'+key))


@pytest.mark.parametrize('change',['new','withdraw'])
def test_tail_cue_change_reconsiders_original_paused_review_after_restart(app,change):
    serial=itertools.count(1)
    with patch('nana_core.continuity.memory.uid',side_effect=lambda:str(uuid.UUID(int=next(serial)))):
        mids=[cue(app,'tail-'+str(n)) for n in range(130)]
        rid,job=pause_candidate(app,'tail');r=app.runtime
        before=r.work._memory_review_blockers('project-work')
        sampled={row[0] for row in r.store.db.execute("SELECT memory_id FROM memories WHERE predicate_key>='concern.' AND predicate_key<'concern/' ORDER BY memory_id LIMIT 129")}
        assert mids[-1] not in sampled
        if change=='new':
            added=cue(app,'tail-new');assert added not in sampled
        else:app.forget(mids[-1])
        assert r.work._memory_review_blockers('project-work')!=before
        identity=r.identity_id;home=app.home;clock=app.clock;app.close()
        with LifeApplication(home,clock=clock) as current:
            current.pause(False);r=current.runtime
            assert r.identity_id==identity and r.store.one('jobs',job['job_id'])['state']=='PAUSED'
            stepped=r.step()
            assert stepped and stepped['reason']=='BOUNDED_MAINTENANCE_SLICE'
            activity=stepped['maintenance']
            assert activity and activity.get('review_enqueued')==rid
            waiting=r.store.one('jobs',job['job_id'])
            assert waiting['state']=='WAITING' and waiting['revision']==job['revision']+1
            queued=r.store.db.execute("SELECT count(*) FROM runtime_queue WHERE state='READY'").fetchone()[0]
            assert queued>=1
            r.work.maintenance_slice()
            assert r.store.db.execute("SELECT count(*) FROM runtime_queue WHERE state='READY'").fetchone()[0]==queued
            assert not r.store.all('cognitive_requests') and not r.store.all('actions')


@pytest.mark.parametrize('values',[
    {'scope':'another-scope'},{'entity':'another-entity'},{'privacy':'PERSONAL'},
    {'predicate':'concernX.not-a-cue'},{'predicate':'Concern.not-a-cue'},
])
def test_unrelated_events_do_not_reactivate_a_paused_review(app,values):
    if values.get('privacy')=='PERSONAL':
        app.runtime.config=app.runtime.config.model_copy(update={'privacy_classes':('PUBLIC','PROJECT')})
    rid,job=pause_candidate(app,'unrelated');r=app.runtime
    before=r.work._memory_review_blockers('project-work')
    cue(app,'unrelated',**values)
    assert r.work._memory_review_blockers('project-work')==before
    writes=r.store.db.total_changes
    assert r.work._memory_review_blockers('project-work')==before
    assert r.store.db.total_changes==writes
    app.pause(False);r.work.maintenance_slice()
    assert r.store.one('jobs',job['job_id'])['state']=='PAUSED'
    assert not r.store.db.execute("SELECT 1 FROM subject_events WHERE source_key LIKE ?",('synthetic.living.review.'+rid+'%',)).fetchone()
    assert not r.store.all('cognitive_requests') and not r.store.all('actions')


def test_same_scope_paused_candidates_share_only_one_slice_condition_read(app):
    jobs=[pause_candidate(app,'batch-'+str(n))[1] for n in range(3)]
    r=app.runtime;app.pause(False)
    with patch.object(r.work,'_memory_review_blockers',wraps=r.work._memory_review_blockers) as read:
        r.work.maintenance_slice();assert read.call_count==1
        r.work.maintenance_slice();assert read.call_count==2
    assert all(r.store.one('jobs',job['job_id'])['state']=='PAUSED' for job in jobs)
    assert not r.store.all('cognitive_requests') and not r.store.all('actions')


def test_candidate_safe_point_write_invalidates_the_within_slice_condition(app):
    old=cue(app,'safe-point-old')
    pairs=[pause_candidate(app,'safe-point-'+str(n)) for n in range(2)]
    r=app.runtime;app.pause(False);original=r.work.maintenance.candidate;seen=[]
    def safe_point(rid):
        seen.append(rid)
        if len(seen)==2:app.forget(old)
        return original(rid)
    # Same owner, genuine source withdrawal at the second candidate safe point.
    # The wrapper controls timing only; all candidate/privacy/store logic is original.
    with patch.object(r.work.maintenance,'candidate',side_effect=safe_point):
        with patch.object(r.work,'_memory_review_blockers',wraps=r.work._memory_review_blockers) as read:
            activity=r.work.maintenance_slice()
            assert read.call_count==2
    # Virtual-clock heads share a timestamp; SQLite need not use insertion order.
    by_rid=dict(pairs)
    assert len(seen)==2 and activity.get('review_enqueued')==seen[1]
    assert r.store.one('jobs',by_rid[seen[0]]['job_id'])['state']=='PAUSED'
    assert r.store.one('jobs',by_rid[seen[1]]['job_id'])['state']=='WAITING'
    assert r.store.one('memories',old)['lifecycle']=='DELETED'
    assert not r.store.all('cognitive_requests') and not r.store.all('actions')
