import json
import pytest
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.open_life.sources import WorldIntake,IntakeSource
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.contracts import CoreError


def test_explicit_source_lifecycle_revision_collision_and_no_cross_source(owned_root):
    clock=VirtualClock()
    with open_runtime(owned_root/'self.db',clock) as r:
        root=owned_root/'sources';root.mkdir()
        def data(revision,state='CURRENT',value='first'):
            return {'revision':revision,'lifecycle':state,'world_claim':{'entity_id':'device','predicate':'lab.version','value':value,'kind':'INTERPRETED','valid_from_us':clock.utc_now_us(),'confidence':.5}}
        for n in ('a','b'):(root/(n+'.json')).write_text(json.dumps(data(1)))
        sources=tuple(IntakeSource(source_id=n,channel='LOCAL_FILE',location=n+'.json',privacy='PUBLIC',accept_lifecycle=True,semantic_format='SOURCED_CLAIM_JSON') for n in ('a','b'))
        intake=WorldIntake(r,root,sources,scope='world');a=intake.read('a');b=intake.read('b');intake.process(a);intake.process(b)
        (root/'a.json').write_text(json.dumps(data(2,'CORRECTED','revised')));new=intake.read('a');intake.process(new)
        assert r.store.one('memories',a)['lifecycle']=='SUPPRESSED'
        assert MemoryService(r.store).read(b)['lifecycle']=='ACTIVE'
        # Retiring support does not magically establish a corrected truth.
        assert WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',)).view('device','lab.version').state=='UNKNOWN'
        (root/'a.json').write_text(json.dumps(data(2,'CORRECTED','collision')))
        with pytest.raises(CoreError,match='COLLISION'):intake.process(intake.read('a'))
        (root/'a.json').write_text(json.dumps(data(1)))
        with pytest.raises(CoreError):intake.process(intake.read('a'))
        (root/'a.json').write_text(json.dumps(data(3,'WITHDRAWN')));assert intake.process(intake.read('a')) is None
        assert r.store.one('memories',new)['lifecycle']=='SUPPRESSED' and MemoryService(r.store).read(b)
        assert not r.store.all('grants') and not r.store.all('actions')


def test_managed_cue_not_redelivered_by_generic_watch(owned_root):
    from nana_core.continuity.open_life.opportunities import OpportunityQueue
    from nana_core.continuity.world_loop.reference import capture
    from tests.open_life.test_attention_research import candidate,judge
    clock=VirtualClock()
    with open_runtime(owned_root/'self.db',clock) as r:
        source=capture(r,'source',{'question':'real owned question'})
        q=OpportunityQueue(r);job=q.offer(candidate(r,source));body=judge(r,q,job)
        managed=r.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.material' AND e.source_reference=?",('open-life:cue:'+job,)).fetchone()[0]
        checks=r.subject.background_opportunities(entity_id='observer',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=0)
        assert managed not in {o.source_id for o in checks}
        assert body['behavior']=='EXPLORE' and r.store.one('memories',managed)['lifecycle']=='ACTIVE'
        # This is delivery dedup, not deleting the original considered desire.
        cycle=r.subject.result(r.store.one('subject_cycles',body['cycle_id']));assert cycle.evaluation.wanted


def test_expired_world_history_does_not_permanently_hide_current_belief(owned_root):
    from nana_core.continuity.world_loop.reference import capture
    from nana_core.continuity.world_loop.world import SourcedClaim
    clock=VirtualClock()
    with open_runtime(owned_root/'self.db',clock) as r:
        world=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',));now=clock.utc_now_us()
        for i in range(80):
            start=now-(100-i)*1000000
            claim=SourcedClaim(entity_id='device',predicate='lab.temporal',value=i,kind='MODEL_BELIEF',valid_from_us=start,valid_until_us=start+500000,confidence=.5)
            mid=capture(r,'expired-'+str(i),{'world_claim':claim.model_dump(mode='json')},kind='MODEL_DERIVATION');world.ingest(mid)
        assert world.view('device','lab.temporal').state=='UNKNOWN'
        claim=SourcedClaim(entity_id='device',predicate='lab.temporal',value='current',kind='MODEL_BELIEF',valid_from_us=now,confidence=.5)
        mid=capture(r,'current',{'world_claim':claim.model_dump(mode='json')},kind='MODEL_DERIVATION');world.ingest(mid)
        view=world.view('device','lab.temporal');assert view.state=='SUPPORTED_BELIEF' and view.alternatives[0]['value']=='current'
        assert r.store.db.execute('PRAGMA user_version').fetchone()[0]==13
        assert r.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='world_replaced_lookup'").fetchone()
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_parked_research_defers_lifecycle_without_rewriting_c_or_holding_load(owned_root):
    from nana_core.continuity.controlled_world.lab import ControlledWorld
    from nana_core.life.application import LifeApplication
    from nana_core.life.config import update_config
    from controlled_hands.conftest import initialize,until
    from nana_core.continuity.records import RecordService
    with ControlledWorld(owned_root/'world',interval=120) as world:
        home=owned_root/'life';cfg=initialize(home,world.host.profile,skills=False)
        sources=(IntakeSource(source_id='good',channel='OWNED_HTTP',location=world.services['feed'].url+'/source',semantic_format='SOURCED_CLAIM_JSON'),IntakeSource(source_id='bad',channel='OWNED_HTTP',location=world.services['api'].url+'/fault/malformed',semantic_format='SOURCED_CLAIM_JSON'))
        update_config(home,cfg.model_copy(update={'revision':2,'advanced_life':True,'world_sources':sources}),expected_revision=1)
        with LifeApplication(home) as app:
            app.advanced.previous=None;r=app.runtime
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM jobs WHERE work_kind='LIFE_RESEARCH' AND state='BLOCKED'").fetchone()))
            job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH' AND state='BLOCKED'").fetchone();body=RecordService(r.store).read(job['record_id'])['payload']
            assert body['state']=='PARKED_NO_RETRY' and body['desire_preserved']
            cycle=r.subject.result(r.store.one('subject_cycles',body['cycle_id']))
            assert cycle.evaluation.normative=='ENDORSED' and cycle.intention.behavior=='EXPLORE'
            assert r.store.one('subject_intentions',cycle.intention_id)['state']=='DEFERRED'
            before=r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind IN ('WORLD_INTAKE','LIFE_RESEARCH')").fetchone()[0]
            revision=job['revision']
            for _ in range(4):app.tick()
            assert r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind IN ('WORLD_INTAKE','LIFE_RESEARCH')").fetchone()[0]==before
            assert r.store.one('jobs',job['job_id'])['revision']==revision and not r.store.all('actions')


def test_noisy_burst_backpressure_daily_bound_and_unchanged_source_dedup(owned_root):
    from nana_core.continuity.world_loop.reference import capture
    from nana_core.continuity.open_life.opportunities import OpportunityQueue
    from tests.open_life.test_attention_research import candidate,judge
    clock=VirtualClock()
    with open_runtime(owned_root/'self.db',clock) as r:
        q=OpportunityQueue(r,capacity=4,daily_limit=2);offered=[]
        for i in range(10):
            mid=capture(r,'burst-'+str(i),{'noise_index':i})
            try:offered.append((q.offer(candidate(r,mid)),mid))
            except CoreError as exc:assert exc.code=='LIFE_QUEUE_BACKPRESSURE'
        assert len(offered)==4
        for _ in range(25):assert q.offer(candidate(r,offered[0][1]))==offered[0][0]
        for job,_ in offered[:2]:judge(r,q,job)
        for _ in range(20):q.opportunity()
        assert r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY' AND state='WAITING'").fetchone()[0]==2
        assert r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY'").fetchone()[0]==4
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
