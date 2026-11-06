"""Stopped-owner host metadata migration; never rewrite life.json or Store."""
import os
from pathlib import Path

import pytest

from tools.nana_living_release_v4.config_permissions import prepare
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config
from tests.first_life_android_v2.test_supervisor import owned


def test_permission_plan_apply_and_idempotence_preserve_original_subject(tmp_path):
    home, binding, release = owned(tmp_path)
    config = home/'life.json'; original = config.read_bytes(); config.chmod(0o644)
    db = home/'subject/self.db'; before = db.read_bytes()
    plan = prepare(home)
    assert plan['state']=='PERMISSION_PLAN_OWNER_STOPPED' and plan['persistent_changes']==0
    assert config.stat().st_mode & 0o777==0o644 and config.read_bytes()==original
    with pytest.raises(ValueError, match='DIGEST_CHANGED'):
        prepare(home, apply=True, expected_sha256='0'*64)
    applied = prepare(home, apply=True, expected_sha256=plan['sha256'])
    assert applied['state']=='PERMISSIONS_TIGHTENED' and applied['persistent_changes']==1
    assert config.read_bytes()==original and db.read_bytes()==before
    assert load_config(home).revision>=1
    assert prepare(home, apply=True, expected_sha256=plan['sha256'])['state']=='NO_CHANGE'


def test_active_original_store_blocks_apply_without_rewriting_config(tmp_path):
    home, _, _ = owned(tmp_path)
    config = home/'life.json'; original = config.read_bytes()
    with LifeApplication(home):
        config.chmod(0o644)
        plan = prepare(home)
        assert plan['state']=='OWNER_ACTIVE_APPLY_BLOCKED'
        with pytest.raises(ValueError, match='STOPPED_OWNER_REQUIRED'):
            prepare(home, apply=True, expected_sha256=plan['sha256'])
        assert config.stat().st_mode & 0o777==0o644 and config.read_bytes()==original


@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_alias_config_cannot_redirect_permission_changes(tmp_path, kind):
    home, _, _ = owned(tmp_path)
    config = home/'life.json'; other = tmp_path/'other.json'
    config.rename(other)
    if kind=='symlink': config.symlink_to(other)
    else: os.link(other, config)
    with pytest.raises((ValueError, OSError)):
        prepare(home)
    assert other.stat().st_mode & 0o777==0o600
