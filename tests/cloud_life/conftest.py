import time
from pathlib import Path
from nana_core.life.config import LifeConfig,write_config
from nana_core.continuity.project_work.service import material_for
REPO=Path(__file__).resolve().parents[2]
def config(**kw):
 return LifeConfig(project_root=str(REPO),materials=(material_for(REPO,'src/nana_core/continuity/recurrence.py'),),practice=material_for(REPO,'src/nana_core/continuity/identity.py'),heldout=material_for(REPO,'src/nana_core/continuity/autonomy/requests.py'),transfer=material_for(REPO,'src/nana_core/continuity/subject/social.py'),**kw)
def initialize(home,**kw):
 c=config(**kw);write_config(home,c);return c
def until(app,test,seconds=35):
 start=time.monotonic()
 while time.monotonic()-start<seconds:
  if test():return
  app.tick();time.sleep(.015)
 raise AssertionError('bounded cloud life progress not reached')
