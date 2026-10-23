"""Actual owned process cuts; atomic marker only after the named real boundary."""
import argparse,json,os,signal,time
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.life.cloud import backup
from nana_core.continuity.records import RecordService
from nana_core.continuity.controlled_world.lab import _atomic


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--marker',type=Path,required=True);p.add_argument('--cut',required=True);a=p.parse_args()
    with LifeApplication(a.home) as app:
        r=app.runtime;s=r.store;running=True
        def stop(*_):
            nonlocal running
            running=False
        signal.signal(signal.SIGTERM,stop)
        def cut():
            _atomic(a.marker,{'cut':a.cut,'identity_id':r.identity_id,'actions':s.db.execute('SELECT count(*) FROM actions').fetchone()[0],'effects':len(json.loads((Path(app.work.port.target.workspace)/'application-state.json').read_text())['effects']),'goals':s.db.execute('SELECT count(*) FROM goals').fetchone()[0]})
            if a.cut=='IDLE_TERM':
                while running:time.sleep(.02)
            else:os.kill(os.getpid(),signal.SIGSTOP)
        if a.cut in {'IDLE','IDLE_TERM','IDLE_GRACEFUL'}:
            if a.cut=='IDLE_GRACEFUL':_atomic(a.marker,{'identity_id':r.identity_id,'cut':a.cut});return
            cut()
            if not running:return
        kernel=r.work.agency.realization.kernel
        original_dispatch=kernel.dispatch;original_verify=kernel.verify;original_port_verify=app.work.port.verify
        def dispatch(aid,*args,**kwargs):
            if a.cut=='BEFORE_ACTION':cut()
            return original_dispatch(aid,*args,**kwargs)
        def verify(aid,*args,**kwargs):
            row=s.one('actions',aid)
            if a.cut=='AFTER_ACTION_BEFORE_VERIFY' and row['capability']=='world.publish':cut()
            return original_verify(aid,*args,**kwargs)
        def port_verify(inv):
            value=original_port_verify(inv)
            if a.cut=='DURING_VERIFY' and inv.capability=='world.publish':cut()
            return value
        kernel.dispatch=dispatch;kernel.verify=verify;app.work.port.verify=port_verify
        end=time.monotonic()+60
        while running and time.monotonic()<end:
            app.tick()
            if a.cut=='RESEARCH' and s.db.execute("SELECT 1 FROM jobs WHERE work_kind='LIFE_RESEARCH' AND cursor=1 AND state='WAITING'").fetchone():cut()
            if a.cut=='AFTER_EXPERIENCE' and s.db.execute('SELECT 1 FROM experiences').fetchone():cut()
            if a.cut=='LEARNING' and s.db.execute("SELECT 1 FROM jobs WHERE work_kind='LEARNING' AND cursor=3 AND state='WAITING'").fetchone():cut()
            if a.cut=='SKILL_QUALIFICATION':
                for j in s.db.execute("SELECT * FROM jobs WHERE work_kind='CODE_DEVELOPMENT' AND state='WAITING'"):
                    b=RecordService(s).read(j['record_id'])['payload'];rid=b.get('candidate_record_id')
                    if rid and RecordService(s).read(rid)['payload']['state']=='TESTING':cut()
            if a.cut=='AFTER_DELIVERY_CANDIDATE' and s.db.execute("SELECT 1 FROM events WHERE kind='life.share_candidate_formed'").fetchone():cut()
            if a.cut=='BACKUP' and s.db.execute('SELECT 1 FROM experiences').fetchone():backup(s,a.marker.with_name('quarantined.db'));cut()
            time.sleep(.015)
        if running:raise RuntimeError('EXACT_CUT_NOT_REACHED_'+a.cut)
if __name__=='__main__':main()
