"""Actual bounded child SIGKILL cut points; no real model/world."""
import os,signal,sys
from pathlib import Path
from .helpers import *
from .test_learning import number_learning

def main():
    root=Path(sys.argv[1]);mode=sys.argv[2]
    with fresh(root/'s'/'self.db') as r:
        if mode=='action':
            obj=objective();port=configure(r,root/'w'/'world.fixture.json',(obj,));port.seed_observation(obj.operators[0].resource,[1.2,2.3])
            mid=cue(r,obj);send(r,'crash-adopt',(mid,));r.step()
            kernel=r.work.agency.realization.kernel;original=kernel.dispatch
            def kill(stage):
                if stage=='after_effect':os.kill(os.getpid(),signal.SIGKILL)
            kernel.dispatch=lambda aid,fault=None:original(aid,fault=kill)
            r.step()
        elif mode=='learning':
            from nana_core.continuity.records import RecordService
            from nana_core.continuity.open_agency.learning import LearningService
            spec=number_learning();r.work.configure_open_learning((spec,))
            original=RecordService.create
            def create(self,tx,**kw):
                if kw['kind']=='OPEN_LEARNING' and kw['payload'].get('lesson_id') and kw['payload'].get('stage')=='MONITOR':os.kill(os.getpid(),signal.SIGKILL)
                return original(self,tx,**kw)
            RecordService.create=create
            c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',topic_key='recover-learning',program_id=spec.learning_key,possible_behaviors=('LEARN',))
            mid=capture(r,'learning-crash',c.model_dump_json(),predicate='concern.recover-learning');send(r,'learning-crash',(mid,));r.drain(32)
        else:raise ValueError('unknown fixture cut')
if __name__=='__main__':main()
