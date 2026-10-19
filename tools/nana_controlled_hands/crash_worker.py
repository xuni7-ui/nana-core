"""Crash cuts surround real original operations; no hand-created Action or goal."""
import argparse,os,signal,time
from pathlib import Path
from nana_core.life.application import LifeApplication

def run(home,mode,marker):
    with LifeApplication(home) as app:
        port=app.work.port;k=app.runtime.work.agency.realization.kernel
        def cut(action=None):
            marker.write_text(str(action or mode));os.kill(os.getpid(),signal.SIGSTOP)
        if mode in {'BEFORE_EFFECT','AFTER_EFFECT'}:
            original=port.execute
            def execute(inv):
                if inv.capability=='world.publish' and mode=='BEFORE_EFFECT':cut(inv.action_id)
                reply=original(inv)
                if inv.capability=='world.publish' and mode=='AFTER_EFFECT':cut(inv.action_id)
                return reply
            port.execute=execute
        if mode=='DURING_VERIFY':
            original=port.verify
            def verify(inv):
                result=original(inv)
                if inv.capability=='world.publish':cut(inv.action_id)
                return result
            port.verify=verify
        if mode=='DURING_LEARNING':
            original=app.runtime.work.open_learning.evaluator.evaluate
            def evaluate(method,cases):
                result=original(method,cases);cut('learning-trial-computed-before-cursor-commit');return result
            app.runtime.work.open_learning.evaluator.evaluate=evaluate
        if mode=='DURING_SKILL_TEST':
            original=app.work.skills.engine.codes.runner.run
            def invoke(source,data):
                result=original(source,data);cut('isolated-code-executed-before-test-commit');return result
            app.work.skills.engine.codes.runner.run=invoke
        if mode=='BEFORE_PREPARE':
            original=k.prepare
            def prepare(aid):
                if app.runtime.store.one('actions',aid)['capability']=='world.publish':cut(aid)
                return original(aid)
            k.prepare=prepare
        until=time.monotonic()+60
        while time.monotonic()<until:app.tick();time.sleep(.02)
        raise RuntimeError('expected crash cut not reached')

def main():
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--mode',required=True);p.add_argument('--marker',type=Path,required=True);a=p.parse_args();run(a.home,a.mode,a.marker)
if __name__=='__main__':main()
