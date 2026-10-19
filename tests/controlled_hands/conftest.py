import time
from pathlib import Path
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import material_for
REPO=Path(__file__).resolve().parents[2]
def initialize(home,profile,*,skills=True):
    cfg=LifeConfig(project_root=str(REPO),materials=(material_for(REPO,'src/nana_core/continuity/recurrence.py'),),practice=material_for(REPO,'src/nana_core/continuity/identity.py'),heldout=material_for(REPO,'src/nana_core/continuity/autonomy/requests.py'),transfer=material_for(REPO,'src/nana_core/continuity/subject/social.py'),owned_application_profile=str(profile),allow_local_skills=skills)
    write_config(home,cfg);return cfg

def until(app,predicate,seconds=35):
    start=time.monotonic()
    while time.monotonic()-start<seconds:
        if predicate():return
        app.tick();time.sleep(.015)
    raise AssertionError('bounded owned-application progress incomplete: '+str([(g['template'],g['state']) for g in app.runtime.store.all('goals')]))
