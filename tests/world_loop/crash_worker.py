"""Real process cut points; no live provider or production world."""
import os,signal,sys
from contextlib import contextmanager
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime,configure,capture
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.world import SourcedClaim
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND

def kill_after_commit(store,kind):
    original=store.transaction
    @contextmanager
    def transaction(event,*args,**kwargs):
        with original(event,*args,**kwargs) as tx:yield tx
        if event==kind:os.kill(os.getpid(),signal.SIGKILL)
    store.transaction=transaction

def checked_counterexample(r):
    from nana_core.continuity.open_agency.fixtures import numeric_learning
    from nana_core.continuity.open_agency.learning import LearningCase
    from nana_core.continuity.subject.opportunities import ConcernCue
    from nana_core.continuity.subject import SubjectInput
    from nana_core.presence.contracts import RuntimeEvent,Cause
    from nana_core.continuity.world_loop.learning import EpisodeLearning
    r.work.configure_open_learning((numeric_learning(),))
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='numbers',program_id='learn.numbers',possible_behaviors=('LEARN',))
    mid=capture(r,'learn',cue.model_dump_json(),predicate='concern.numbers')
    inp=SubjectInput(source_key='synthetic.crash-learning',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us())
    r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us()));r.drain(32)
    lesson=r.store.all('lessons')[0];assert lesson['state']=='ACTIVE'
    case=LearningCase(case_id='counter',context='independent-episode',data=[.1,.2],expected=.3)
    mid=capture(r,'counter',{'strategy_episode':{'episode_key':'counter','lesson_id':lesson['lesson_id'],'case':case.model_dump(mode='json')}})
    kill_after_commit(r.store,'world.strategy_episode_checked')
    EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',)).assess(lesson['lesson_id'],mid,authority=r.authority)

def main():
    root=Path(sys.argv[1]);mode=sys.argv[2];clock=VirtualClock()
    with provider_harness() as (transport,_),open_runtime(root/'subject'/'self.db',clock) as r:
        port=configure(r,root,transport,('synthetic://recover',),planner=False);port.seed_observation('synthetic://recover',{'data':'public recoverable observation'})
        mid=capture(r,'recover-world',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=True,kind='RAW_OBSERVATION',valid_from_us=r.clock.utc_now_us()).model_dump(mode='json'),'opportunities':[{'topic':'recover','resource':'synthetic://recover','value':'HIGH','motive':'CURIOSITY'}]})
        r.work.world.world.ingest(mid);r.work.world.observe(mid)
        if mode=='calling':
            def cut(request):os.kill(os.getpid(),signal.SIGKILL)
            transport.exchange=cut
        elif mode=='goal':
            def cut(*args,**kwargs):os.kill(os.getpid(),signal.SIGKILL)
            r.work.world.after_cycle=cut # after Agency adoption, before concern ACK
        elif mode in {'prepared','proposed','concern','cycle','skill'}:
            kind={'prepared':'world.cognition_prepared','proposed':'world.cognition_proposed','concern':'world.concern_formed','cycle':'subject.cycle_accepted','skill':'world.skill_development_slice'}[mode]
            if mode=='skill':
                mid=capture(r,'skill-need',{'opportunities':[{'topic':'clean','value':'HIGH','skill_task':'TEXT_CLEAN'}]});r.work.world.observe(mid)
            kill_after_commit(r.store,kind)
        elif mode=='revision':
            kill_after_commit(r.store,'world.belief_revision')
            correction=capture(r,'corrected-world',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=False,kind='RAW_OBSERVATION',valid_from_us=r.clock.utc_now_us(),corrects=r.store.all('world_beliefs')[0]['belief_id']).model_dump(mode='json')})
            r.work.world.world.ingest(correction)
        elif mode=='strategy':checked_counterexample(r)
        elif mode=='delete':
            from nana_core.continuity import privacy
            from nana_core.continuity.memory import MemoryService
            original=privacy._atomic
            def erase_intent(path,data):
                original(path,data)
                if path==r.store.privacy.path and data.get('intents'):os.kill(os.getpid(),signal.SIGKILL)
            privacy._atomic=erase_intent
            MemoryService(r.store,r.authority).forget(mid,r.authority)
        else:raise ValueError('unknown cut')
        for _ in range(32):clock.advance(SECOND);r.step()
    raise RuntimeError('cut not reached')
if __name__=='__main__':main()
