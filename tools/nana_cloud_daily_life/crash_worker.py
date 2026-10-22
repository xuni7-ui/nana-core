"""Actual process cut after C commit, before the original D work follow-up."""
import argparse,os,signal,time,tempfile
from pathlib import Path
from nana_core.life.application import LifeApplication

def publish_cut(path,cycle_id):
 # The parent watches path.exists(). A directly created empty marker lets it
 # SIGKILL the writer before cycle_id is written. Publish only the complete,
 # durable marker; this changes no C transaction or recovery assertion.
 if path.exists():raise RuntimeError('cut marker already exists')
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.committed-cut-')
 try:
  with os.fdopen(fd,'w') as stream:stream.write(cycle_id);stream.flush();os.fsync(stream.fileno())
  os.replace(name,path)
  directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(directory)
  finally:os.close(directory)
 finally:
  if os.path.exists(name):os.unlink(name)

def main():
 p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--marker',type=Path,required=True);p.add_argument('--cut',choices=['GOAL','REFLECTION'],required=True);a=p.parse_args()
 with LifeApplication(a.home) as app:
  old=app.runtime.subject.run
  def run(event,*args,**kwargs):
   cycle=old(event,*args,**kwargs)
   selected=(a.cut=='GOAL' and cycle.proposed_program_id) or (a.cut=='REFLECTION' and event.reflection_experience_id and cycle.intention.kind=='REFLECTION')
   if selected:publish_cut(a.marker,cycle.cycle_id);os.kill(os.getpid(),signal.SIGSTOP)
   return cycle
  app.runtime.subject.run=run
  until=time.monotonic()+40
  while time.monotonic()<until:app.tick();time.sleep(.02)
  raise RuntimeError('cut not reached')
if __name__=='__main__':main()
