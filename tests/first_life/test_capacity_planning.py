"""Disk-aware planning does not delete history or resume a latched writer."""
from types import SimpleNamespace
import pytest
from nana_core.life.config import daily_configuration,LifeConfig
from nana_core.life.durability import capacity_plan,StorageGuard,MB
from nana_core.life.application import LifeApplication
from tests.cloud_life.conftest import config,initialize


def test_missing_old_policy_and_explicit_limits_stay_fixed():
    old=config();assert old.state_capacity_policy=='FIXED'
    assert capacity_plan(old,{'family_bytes':MB},'/not-a-path')['limit_bytes']==256*MB
    values=old.model_dump();values.pop('state_capacity_policy');values.pop('state_capacity_ceiling_mb')
    values.pop('state_disk_reserve_mb');values.pop('state_backup_headroom_copies')
    assert LifeConfig.model_validate(values).state_capacity_policy=='FIXED'
    new=daily_configuration(**{k:v for k,v in values.items() if k!='max_state_mb'})
    assert new.state_capacity_policy=='DISK_AWARE'
    assert daily_configuration(**values).state_capacity_policy=='FIXED'


def test_capacity_uses_actual_free_space_and_backup_headroom_not_a_256mb_ceiling(tmp_path,monkeypatch):
    selected=config(state_capacity_policy='DISK_AWARE')
    monkeypatch.setattr('nana_core.life.durability.os.statvfs',lambda path:SimpleNamespace(f_bavail=19*1024,f_frsize=MB))
    plan=capacity_plan(selected,{'family_bytes':300*MB},tmp_path)
    assert plan['limit_bytes']>256*MB
    assert plan['limit_bytes']*3-300*MB<=19*1024*MB-plan['reserve_bytes']
    assert plan['backup_status']=='HEADROOM_ONLY_NOT_BACKUP_OR_DR_QUALIFICATION'
    monkeypatch.setattr('nana_core.life.durability.os.statvfs',lambda path:SimpleNamespace(f_bavail=100,f_frsize=MB))
    assert capacity_plan(selected,{'family_bytes':300*MB},tmp_path)['limit_bytes']<300*MB


def test_disk_aware_capacity_keeps_rate_guard_and_latched_stop(tmp_path,monkeypatch):
    home=tmp_path/'home';initialize(home,max_autonomous_materials=0,state_capacity_policy='DISK_AWARE')
    monkeypatch.setattr('nana_core.life.durability.os.statvfs',lambda path:SimpleNamespace(f_bavail=19*1024,f_frsize=MB))
    with LifeApplication(home) as app:
        app.pause();guard=StorageGuard(app);before=list(app.runtime.store.db.execute('SELECT event_id,data_json FROM events'))
        assert guard.observe(force=True)['status']=='OBSERVING'
        assert list(app.runtime.store.db.execute('SELECT event_id,data_json FROM events'))==before
        monkeypatch.setattr('nana_core.life.durability.os.statvfs',lambda path:SimpleNamespace(f_bavail=0,f_frsize=MB))
        assert guard.observe(force=True)['status']=='STATE_SIZE_LIMIT_STOP'
        assert app.runtime.stop_requested
    monkeypatch.setattr('nana_core.life.durability.os.statvfs',lambda path:SimpleNamespace(f_bavail=19*1024,f_frsize=MB))
    with LifeApplication(home) as app:
        assert StorageGuard(app).observe(force=True)['status']=='STATE_SIZE_LIMIT_STOP'
        assert app.runtime.stop_requested


def test_capacity_error_is_explicit_not_an_unlimited_fallback(tmp_path,monkeypatch):
    from nana_core.contracts import CoreError
    monkeypatch.setattr('nana_core.life.durability.os.statvfs',lambda path:(_ for _ in ()).throw(OSError()))
    with pytest.raises(CoreError,match='STORAGE_CAPACITY_UNAVAILABLE'):
        capacity_plan(config(state_capacity_policy='DISK_AWARE'),{'family_bytes':1},tmp_path)
