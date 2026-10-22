import json
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.reference import open_runtime,capture
from nana_core.continuity.open_life.opportunities import OpportunityQueue,LifeOpportunity
from nana_core.continuity.open_life.sources import WorldIntake,IntakeSource
from nana_core.continuity.open_life.research import ResearchService
from nana_core.continuity.world_loop.world import SourcedClaim,WorldModel
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,DAY

@pytest.fixture
def runtime(tmp_path):
    with open_runtime(tmp_path/'s.db',VirtualClock()) as r:yield r

def candidate(r,m,**kwargs):
    return LifeOpportunity(kind='CURIOSITY',topic='world.question',source_memory_ids=(m,),cue=ConcernCue(cue_kind='DISCOVERY',topic_key='world.question',motivation_source='CURIOSITY',possible_behaviors=('EXPLORE','WATCH'),resource_class='ORDINARY'),expires_at_us=r.clock.utc_now_us()+DAY,**kwargs)

def judge(r,q,j):
    q.opportunity()
    for _ in range(12):
        r.clock.source.advance(SECOND);r.step();q.opportunity()
        if r.store.one('jobs',j)['state']=='DONE':break
    assert r.store.one('jobs',j)['state']=='DONE'
    return RecordService(r.store).read(r.store.one('jobs',j)['record_id'])['payload']

def test_queue_original_c_restart_idempotency_and_suppression(runtime):
    r=runtime;m=capture(r,'question',{'needs_review':True});q=OpportunityQueue(r)
    j=q.offer(candidate(r,m));b=judge(r,q,j)
    assert b['behavior']=='EXPLORE' and b['normative']=='ENDORSED'
    before=r.store.db.execute('SELECT count(*) FROM subject_cycles').fetchone()[0]
    assert OpportunityQueue(r).offer(candidate(r,m))==j
    for _ in range(50):q.opportunity()
    assert r.store.db.execute('SELECT count(*) FROM subject_cycles').fetchone()[0]==before
    assert not r.store.all('actions') and not r.store.all('grants')
    m2=capture(r,'irrelevant',{'unimportant':True})
    low=q.offer(candidate(r,m2,value='LOW'))
    assert r.store.one('jobs',low)['state']=='CANCELLED'
    assert q.view()[0]['state']=='SUPPRESSED'


def test_load_and_expensive_learning_allow_rest(runtime):
    r=runtime;m=capture(r,'cost',{'expensive':True});q=OpportunityQueue(r)
    j=q.offer(candidate(r,m,cost='HEAVY'))
    b=judge(r,q,j)
    assert b['behavior'] in {'REST','DEFER','DO_NOTHING','WATCH','STAY_SILENT'}
    assert not r.store.all('actions')


def test_deleted_source_never_wakes_again(runtime):
    r=runtime;m=capture(r,'delete',{'exists':True});q=OpportunityQueue(r);j=q.offer(candidate(r,m))
    MemoryService(r.store,r.authority).forget(m,r.authority)
    assert q.opportunity() is None
    assert q.view()==()
    with pytest.raises(CoreError):q.offer(candidate(r,m))
    assert not r.store.all('subject_cycles')


def test_intake_research_contradiction_withdrawal_and_no_learning(runtime,tmp_path):
    r=runtime;root=tmp_path/'sources';root.mkdir()
    for name in ('a','b'):(root/(name+'.json')).write_text('{"answer": 3}')
    sources=tuple(IntakeSource(source_id=n,channel='LOCAL_FILE',location=n+'.json',privacy='PUBLIC') for n in ('a','b'))
    intake=WorldIntake(r,root,sources,scope='world');q=OpportunityQueue(r);research=ResearchService(r,q,intake)
    rootm=capture(r,'question',{'question':'compare independent project documents'})
    j=research.notice('research.answer',(rootm,))
    with pytest.raises(CoreError,match='RESEARCH_C_JUDGMENT_REQUIRED'):research.gather(j,'a')
    judge(r,q,j)
    mids=[];raws=[]
    for name in ('a','b'):
        raw=research.gather(j,name);raws.append(raw)
        assert research.gather(j,name)==raw
        mid,bid=intake.interpret(raw,SourcedClaim(entity_id='device',predicate='answer',value=3,kind='INTERPRETED',valid_from_us=r.clock.utc_now_us(),confidence=.6));mids.append(mid)
    rid=research.compare(j,'device','answer',tuple(mids))
    assert RecordService(r.store).read(rid)['payload']['state']=='ENOUGH_FOR_BOUNDED_BELIEF'
    assert not r.store.all('lessons') and not r.store.all('experiences')
    (root/'b.json').write_text('{"answer": 4}')
    revised=intake.read('b')
    mid,_=intake.interpret(revised,SourcedClaim(entity_id='device',predicate='answer',value=4,kind='INTERPRETED',valid_from_us=r.clock.utc_now_us(),confidence=.6))
    rid=research.compare(j,'device','answer',(mids[0],mid))
    assert RecordService(r.store).read(rid)['payload']['state']=='CONTRADICTION'
    MemoryService(r.store,r.authority).forget(raws[0],r.authority)
    assert WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',)).view('device','answer').state=='UNKNOWN'
    with pytest.raises(CoreError):RecordService(r.store).read(rid)
    with pytest.raises(CoreError):intake.read('a')

@pytest.mark.parametrize('location',['../outside','/etc/passwd','link/secret','link.txt'])
def test_source_path_escape_denied(runtime,tmp_path,location):
    root=tmp_path/'sources';root.mkdir();(root/'link').symlink_to('/etc',target_is_directory=True);(root/'link.txt').symlink_to('/etc/passwd')
    if location.startswith(('/','..')):
        with pytest.raises(ValueError):IntakeSource(source_id='bad',channel='LOCAL_FILE',location=location)
    else:
        intake=WorldIntake(runtime,root,(IntakeSource(source_id='bad',channel='LOCAL_FILE',location=location),),scope='world')
        with pytest.raises(CoreError):intake.read('bad')

@pytest.mark.parametrize('url',['https://example.com/','http://localhost:80/x','http://127.0.0.1:80/x#f','http://u:p@127.0.0.1:80/x','file:///etc/passwd'])
def test_no_arbitrary_network(url):
    with pytest.raises(ValueError):IntakeSource(source_id='bad',channel='OWNED_HTTP',location=url)

@pytest.mark.parametrize('factors,expected',[
    ({'goal_value':'LOW','future_reuse':'LOW'},'WATCH'),
    ({'goal_value':'HIGH','future_reuse':'HIGH','alternative':'AVAILABLE'},'WATCH'),
    ({'goal_value':'HIGH','future_reuse':'HIGH','time_compute_cost':'HEAVY'},'REST'),
    ({'goal_value':'HIGH','future_reuse':'HIGH','risk':'HIGH'},'REST'),
    ({'goal_value':'HIGH','future_reuse':'HIGH'},'LEARN'),
])
def test_original_c_learning_value_optional(runtime,factors,expected):
    from nana_core.continuity.subject.opportunities import LearningValue
    r=runtime;m=capture(r,'learning-assessment',{'assessment_basis':'explicit project fixture'})
    q=OpportunityQueue(r);c=candidate(r,m)
    c=c.model_copy(update={'cue':c.cue.model_copy(update={'motivation_source':'SELF_DEVELOPMENT','possible_behaviors':('LEARN','REST'),'learning_value':LearningValue(**factors)})})
    b=judge(r,q,q.offer(c));assert b['behavior']==expected
    assert not r.store.all('actions') and not r.store.all('grants')


def test_pending_queue_reentry_uses_original_load_snapshot(runtime):
    r=runtime;m=capture(r,'reentry',{'test':'crash before C'})
    q=OpportunityQueue(r);c=candidate(r,m);j=q.offer(c)
    first=q.opportunity();second=OpportunityQueue(r).opportunity()
    assert first['queue_id']==second['queue_id']
    assert r.store.db.execute('SELECT count(*) FROM runtime_queue').fetchone()[0]==1
