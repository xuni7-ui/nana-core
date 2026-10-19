from pathlib import Path
import pytest
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import material_for
from nana_core.presence.authority import VirtualClock

REPO=Path(__file__).resolve().parents[2]
SOURCES=('src/nana_core/continuity/recurrence.py','src/nana_core/continuity/extensions.py')
TRAINING=('src/nana_core/continuity/identity.py','src/nana_core/continuity/autonomy/requests.py','src/nana_core/continuity/subject/social.py')

def initialize(home,*,active=2):
    config=LifeConfig(project_root=str(REPO),materials=tuple(material_for(REPO,p) for p in SOURCES),practice=material_for(REPO,TRAINING[0]),heldout=material_for(REPO,TRAINING[1]),transfer=material_for(REPO,TRAINING[2]),max_autonomous_materials=active,activity_interval_seconds=.5)
    write_config(home,config);return config

@pytest.fixture
def app(tmp_path):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock(),bootstrap_grant=True) as a:yield a

def advance(app,n=1):
    rows=[]
    for _ in range(n):app.clock.advance(250_000);rows.append(app.tick())
    return rows
