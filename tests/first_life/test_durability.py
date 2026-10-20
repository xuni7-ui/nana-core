from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.life.durability import StorageGuard,profile
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.cloud_life.conftest import initialize


def test_profile_and_checkpoint_keep_history_and_privacy(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
 with LifeApplication(home) as app:
  app.pause();reply=app.chat('不要深入',topic='project',privacy='PROJECT');app.forget(reply['message_memory_id'])
  before=list(app.runtime.store.db.execute('SELECT event_id,data_json FROM events ORDER BY seq'))
  privacy=app.runtime.store.privacy.path.read_bytes()
  result=StorageGuard(app).observe(force=True);assert result['status']=='OBSERVING'
  view=profile(app.runtime.store);assert view['tables_and_indexes'] and view['event_kinds']
  assert list(app.runtime.store.db.execute('SELECT event_id,data_json FROM events ORDER BY seq'))==before
  assert app.runtime.store.privacy.path.read_bytes()==privacy
  assert not list(app.runtime.store.db.execute('PRAGMA foreign_key_check'))


def test_rate_limit_survives_restart_and_stops_without_pruning(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,storage_growth_grace_seconds=0,storage_growth_window_seconds=60,max_state_growth_mb_per_hour=1)
 clock=VirtualClock()
 with LifeApplication(home,clock=clock) as app:
  app.pause();g=StorageGuard(app);initial=g.observe(force=True);identity=app.runtime.identity_id
 with LifeApplication(home,clock=clock) as app:
  app.pause();g=StorageGuard(app);assert g.state.started_us==clock.utc_now_us()
  # An explicit synthetic audit artifact simulates observed state growth; it is
  # not Subject memory/evidence about the world and must not be silently pruned.
  with app.runtime.store.transaction('synthetic.storage.load') as tx:aid=tx.artifact(b'PUBLIC_SYNTHETIC_STORAGE_SAMPLE'*5000)
  for _ in range(3):
   clock.advance(20_000_000);app.runtime.lease.heartbeat(force=True)
  before=app.runtime.store.db.execute('SELECT count(*) FROM events').fetchone()[0]
  result=g.observe(force=True)
  assert result['status']=='STATE_GROWTH_LIMIT_STOP' and app.runtime.stop_requested
  assert app.runtime.identity_id==identity and app.runtime.store.db.execute('SELECT count(*) FROM events').fetchone()[0]==before
  assert app.runtime.store.db.execute('SELECT length(payload) FROM artifacts WHERE artifact_id=?',(aid,)).fetchone()[0]>0
 with LifeApplication(home,clock=clock) as app:
  assert StorageGuard(app).observe(force=True)['status']=='STATE_GROWTH_LIMIT_STOP'
  assert app.runtime.stop_requested


def test_corrupt_guard_fails_closed_and_hard_size_stops(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,max_state_mb=1)
 with LifeApplication(home) as app:
  with app.runtime.store.transaction('synthetic.storage.load') as tx:tx.artifact(b'PUBLIC_SYNTHETIC'*100000)
  assert StorageGuard(app).observe(force=True)['status']=='STATE_SIZE_LIMIT_STOP'
  assert app.runtime.stop_requested
 (home/'storage-monitor.json').write_text('{broken')
 with LifeApplication(home) as app:
  with pytest.raises(CoreError,match='STORAGE_MONITOR_INVALID'):StorageGuard(app)
