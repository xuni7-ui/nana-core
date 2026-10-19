"""Actual process cut after C commit, before the original D work follow-up."""
import argparse,os,signal,time
from pathlib import Path
from nana_core.life.application import LifeApplication

def main():
 p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--marker',type=Path,required=True);p.add_argument('--cut',choices=['GOAL','REFLECTION'],required=True);a=p.parse_args()
 with LifeApplication(a.home) as app:
  old=app.runtime.subject.run
  def run(event,*args,**kwargs):
   cycle=old(event,*args,**kwargs)
   selected=(a.cut=='GOAL' and cycle.proposed_program_id) or (a.cut=='REFLECTION' and event.reflection_experience_id and cycle.intention.kind=='REFLECTION')
   if selected:a.marker.write_text(cycle.cycle_id);os.kill(os.getpid(),signal.SIGSTOP)
   return cycle
  app.runtime.subject.run=run
  until=time.monotonic()+40
  while time.monotonic()<until:app.tick();time.sleep(.02)
  raise RuntimeError('cut not reached')
if __name__=='__main__':main()
