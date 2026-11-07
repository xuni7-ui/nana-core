"""Fresh product defaults, not permission to spend or mutate an existing home."""
import json
from types import SimpleNamespace

import pytest

from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.config import DAILY_PROVIDER_DEFAULTS, daily_configuration, load_config
from nana_core.life.readiness import budget, budget_report, provider_readiness
from tests.cloud_life.conftest import config, initialize
from tests.provider_routing.helpers import fixture_router, model, update
from nana_core.continuity.provider_config import ProviderProfile
from nana_core.continuity.provider_routing import RoutingPolicy
from tests.world_loop.helpers import policy


def test_fresh_daily_defaults_preserve_zero_paid_authority_and_explicit_ceilings():
    legacy = config()
    fields = legacy.model_dump(exclude=set(DAILY_PROVIDER_DEFAULTS))
    fresh = daily_configuration(**fields)
    assert fresh.provider_calls_per_day == 128 and fresh.provider_calls_per_hour == 64
    assert fresh.per_provider_calls_per_day == 128
    assert fresh.provider_cost_ceiling_micro == 0
    assert fresh.provider_hosts == () and fresh.remote_privacy == ()
    limited = daily_configuration(**{**fields, 'provider_calls_per_day': 20,
        'provider_total_calls_limit': 8, 'provider_total_reserved_cost_micro': 400000})
    assert limited.provider_calls_per_day == 20 and limited.provider_total_calls_limit == 8
    assert limited.provider_total_reserved_cost_micro == 400000


def test_legacy_missing_or_explicit_fields_are_not_silently_raised(tmp_path):
    home = tmp_path/'home';initialize(home)
    path = home/'life.json'
    raw = json.loads(path.read_text())
    for field in DAILY_PROVIDER_DEFAULTS:raw.pop(field)
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    legacy = load_config(home)
    assert (legacy.provider_calls_per_day,legacy.provider_calls_per_hour,legacy.per_provider_calls_per_day)==(12,24,24)
    assert path.read_bytes() == before
    raw.update(provider_calls_per_day=3, provider_calls_per_hour=2, per_provider_calls_per_day=1)
    path.write_text(json.dumps(raw))
    explicit = load_config(home)
    assert (explicit.provider_calls_per_day,explicit.provider_calls_per_hour,explicit.per_provider_calls_per_day)==(3,2,1)


def test_blocked_budget_retains_readonly_counts_and_exact_limit_reason(tmp_path):
    home=tmp_path/'home';initialize(home,provider_calls_per_day=1)
    with LifeApplication(home) as app:
        snapshot=SimpleNamespace(provider_profile_id='fixture.a')
        before=len(app.runtime.store.all('events'))
        report=budget_report(app,snapshot,calls=2)
        assert report['block_reason']=='PROVIDER_DAILY_BUDGET'
        assert '过去24小时' in report['block_message'] and 'PROVIDER_' not in report['block_message']
        assert report['calls_last_day']==0 and report['limits']['calls_per_day']==1
        assert report['minimum_calls_for_dialogue']==2 and report['unknown_reservations_refunded'] is False
        assert 'TRAILING' in report['window']
        with pytest.raises(CoreError,match='PROVIDER_DAILY_BUDGET'):budget(app,snapshot,calls=2)
        assert len(app.runtime.store.all('events'))==before and not app.runtime.store.all('cognitive_requests')


def test_remote_zero_cost_readiness_is_not_reported_ready_and_never_resolves_key(tmp_path):
    router, service, authority, _, ports=fixture_router(tmp_path)
    remote=ProviderProfile(provider_profile_id='remote.main',display_name='Remote',protocol='OPENAI_COMPATIBLE_CHAT',
        base_url='https://example.test/v1',secret_ref='remote.default',locality='REMOTE')
    update(service,authority,'UPSERT_PROVIDER',provider=remote)
    update(service,authority,'UPSERT_MODEL',model=model('model.remote','remote.main'))
    from nana_core.continuity.provider_config import CapabilityRoute
    update(service,authority,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='COGNITION',primary_model_profile_id='model.remote'))
    resolver=router.factory._RuntimeProviderFactory__resolver;resolver.refs.add('remote.default')
    router.factory.policy=RoutingPolicy(allow_remote=True,allowed_remote_hosts=('example.test',))
    home=tmp_path/'life';initialize(home)
    with LifeApplication(home) as life:
        app=SimpleNamespace(config=life.config,runtime=life.runtime,home=tmp_path/'host',router=router,session=None,policy=policy())
        result=provider_readiness(app,privacy='PUBLIC')
        assert result['state']=='BUDGET_DENIED',result
        assert result['budget_limits']['per_call_reserved_cost_micro']==0
        assert resolver.resolved==0 and all(port.calls==0 for port in ports)
        assert not life.runtime.store.all('cognitive_requests')


def test_portable_new_home_uses_daily_profile_without_creating_an_identity(tmp_path):
    from nana_core.life.portable_runtime import configuration
    materials=tmp_path/'materials';materials.mkdir()
    for name in ('sample.py','practice.py','heldout.py','transfer.py'):
        (materials/name).write_text('def synthetic_material():\n    return 1\n')
    cfg=configuration(tmp_path)
    assert cfg.provider_calls_per_day==128 and cfg.provider_calls_per_hour==64
    assert cfg.provider_cost_ceiling_micro==0 and cfg.remote_privacy==()
    assert not (tmp_path/'life.json').exists() and not list(tmp_path.rglob('*.db'))
