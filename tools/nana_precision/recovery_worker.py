"""Owned SIGKILL cut inside original C/G/checkpoint transaction boundaries."""
import json,os,signal,sys
from contextlib import contextmanager
from pathlib import Path
from nana_core.continuity.open_agency.contracts import TaskGroup
from tests.open_autonomy.helpers import objective,fresh,configure,cue,send,advance
from tests.open_autonomy.test_learning import number_learning


def described():
    base=objective('precision.recovery',method='NAIVE_SUM')
    first=objective('precision.prefix');ops=[]
    for prefix,obj in (('a.',first),('b.',base)):
        for op in obj.operators:
            args=dict(op.args)
            if args.get('input_from'):args['input_from']=prefix+args['input_from']
            ops.append(op.model_copy(update={'operator_id':prefix+op.operator_id,'requires':tuple(prefix+f for f in op.requires)+(('a.published',) if prefix=='b.' and not op.requires else ()),'produces':tuple(prefix+f for f in op.produces),'args':args}))
    return base.model_copy(update={'operators':tuple(ops),'desired':('b.published',),'task_groups':(TaskGroup(group_id='group.a',members=('a.inspect','a.compute','a.publish')),TaskGroup(group_id='group.b',members=('b.inspect','b.compute','b.publish')))})


def main():
    root,cut=Path(sys.argv[1]),sys.argv[2]
    with fresh(root/'state'/'self.db') as r:
        obj=described();port=configure(r,root/'world'/'effect.fixture.json',(obj,))
        for op in obj.operators:
            if op.capability=='world.observe':port.seed_observation(op.resource,[1.2,2.3])
        r.work.configure_open_learning((number_learning(),))
        def stop():
            goal=r.store.all('goals')[0]
            value={'identity_id':r.identity_id,'goal_id':goal['goal_id'],'cut':cut,'actions':len(r.store.all('actions'))}
            (root/'cut.json').write_text(json.dumps(value))
            os.kill(os.getpid(),signal.SIGSTOP)
        original=r.work.agency._plan_record
        def plan_record(*args,**kwargs):
            if kwargs.get('checkpoint') and cut=='BEFORE_PLAN_COMMIT':stop()
            return original(*args,**kwargs)
        r.work.agency._plan_record=plan_record
        transaction=r.store.transaction
        @contextmanager
        def wrapped(kind,*args,**kwargs):
            with transaction(kind,*args,**kwargs) as tx:yield tx
            if kind=='open.goal_replanned' and cut=='AFTER_PLAN_COMMIT':stop()
        r.store.transaction=wrapped
        mid=cue(r,obj)
        send(r,'adopt',(mid,));r.step();advance(r,8)
        goal=r.store.all('goals')[0];assert goal['state']=='FAILED'
        exp=next(e for e in r.store.all('experiences') if e['outcome']=='FAILURE')
        send(r,'reflect',(mid,),reflection_experience_id=exp['experience_id'],task_class='numbers')
        r.drain(24);advance(r,20)
        raise RuntimeError('EXACT_CUT_NOT_REACHED')


if __name__=='__main__':main()
