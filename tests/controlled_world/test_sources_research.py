import json
import pytest
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.open_life.sources import WorldIntake,IntakeSource
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.contracts import CoreError


def test_explicit_source_lifecycle_revision_collision_and_no_cross_source(owned_root):
    clock=VirtualClock()
    with open_runtime(owned_root/'self.db',clock) as r:
        root=owned_root/'sources';root.mkdir()
        def data(revision,state='CURRENT',value='first'):
            return {'revision':revision,'lifecycle':state,'world_claim':{'entity_id':'device','predicate':'lab.version','value':value,'kind':'INTERPRETED','valid_from_us':clock.utc_now_us(),'confidence':.5}}
        for n in ('a','b'):(root/(n+'.json')).write_text(json.dumps(data(1)))
        sources=tuple(IntakeSource(source_id=n,channel='LOCAL_FILE',location=n+'.json',privacy='PUBLIC',accept_lifecycle=True,semantic_format='SOURCED_CLAIM_JSON') for n in ('a','b'))
        intake=WorldIntake(r,root,sources,scope='world');a=intake.read('a');b=intake.read('b');intake.process(a);intake.process(b)
        (root/'a.json').write_text(json.dumps(data(2,'CORRECTED','revised')));new=intake.read('a');intake.process(new)
        assert r.store.one('memories',a)['lifecycle']=='SUPPRESSED'
        assert MemoryService(r.store).read(b)['lifecycle']=='ACTIVE'
        # Retiring support does not magically establish a corrected truth.
        assert WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',)).view('device','lab.version').state=='UNKNOWN'
        (root/'a.json').write_text(json.dumps(data(2,'CORRECTED','collision')))
        with pytest.raises(CoreError,match='COLLISION'):intake.process(intake.read('a'))
        (root/'a.json').write_text(json.dumps(data(1)))
        with pytest.raises(CoreError):intake.process(intake.read('a'))
        (root/'a.json').write_text(json.dumps(data(3,'WITHDRAWN')));assert intake.process(intake.read('a')) is None
        assert r.store.one('memories',new)['lifecycle']=='SUPPRESSED' and MemoryService(r.store).read(b)
        assert not r.store.all('grants') and not r.store.all('actions')
