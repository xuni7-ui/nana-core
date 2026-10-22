from pathlib import Path
import pytest
from nana_core.life.config import LifeConfig,write_config
from nana_core.continuity.project_work.service import material_for
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
REPO=Path(__file__).resolve().parents[2]

def initialize(home):
    material=lambda p:material_for(REPO,'src/nana_core/continuity/'+p)
    write_config(home,LifeConfig(project_root=str(REPO),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),max_autonomous_materials=0,provider_calls_per_hour=24,provider_calls_per_day=24,per_provider_calls_per_day=24,provider_context_tokens=16384,provider_output_tokens=2048))

@pytest.fixture
def app(tmp_path):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as a:
        a.pause();yield a
