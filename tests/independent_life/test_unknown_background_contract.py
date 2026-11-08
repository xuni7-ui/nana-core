"""Existing-host UNKNOWN budget contract; only loopback fixtures are used."""
import pytest
import json
import subprocess
import sys
from pathlib import Path

from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig
from nana_core.life.live_api.supervisor import existing_identity, identity_request_state, Supervisor, Release
from nana_core.life.live_api.contracts import Binding
from nana_core.presence.resources import allocation_reason, resource_state
from nana_core.presence.contracts import DAY
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
from tests.independent_life.conftest import initialize
from tests.independent_life.test_dialogue import relay
from nana_core.presence.authority import VirtualClock


def test_old_configuration_field_is_preserved_and_bounded(app):
    raw = app.config.model_dump(mode='json')
    raw['provider_unknown_calls_per_day'] = 7
    restored = LifeConfig.model_validate_json(json.dumps(raw))
    assert restored.provider_unknown_calls_per_day == 7
    assert restored.model_dump(mode='json')['provider_unknown_calls_per_day'] == 7
    for invalid in (-1, 129):
        with pytest.raises(ValueError):
            LifeConfig.model_validate_json(json.dumps({**raw, 'provider_unknown_calls_per_day': invalid}))


def test_unknown_reservation_allows_new_foreground_but_paces_background(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    initialize(home, active=0)
    clock = VirtualClock()
    calls = []
    def timeout(self, request):
        calls.append(request.request_id)
        raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport, 'exchange', timeout)
    with relay(home) as (router, _), LifeApplication(home, clock=clock, router=router) as app:
        app.pause()
        app.chat('SYNTHETIC initial timeout', message_id='unknown-first')
        row = app.runtime.store.all('cognitive_requests')[0]
        assert row['state'] == 'UNKNOWN' and len(calls) == 1
        state = resource_state(app.runtime.store, app.runtime.config)
        assert state.unresolved_terminal_calls == 1 and state.unresolved_live_calls == 0
        living = app.runtime.config.living.model_copy(update={'max_estimated_cost_micro_per_day': 100000})
        cap = app.runtime.config.model_copy(update={'provider_unknown_calls_per_day': 1, 'living': living})
        assert allocation_reason(app.runtime.store, cap, {'event_type': 'SELF_EVENT'}) == 'UNKNOWN_BILLING_BACKGROUND_PAUSED'
        assert allocation_reason(app.runtime.store, cap, {'event_type': 'USER_EVENT'}) is None
        disabled = cap.model_copy(update={'provider_unknown_calls_per_day': 0})
        assert allocation_reason(app.runtime.store, disabled, {'event_type': 'SELF_EVENT'}) is None
        app.chat('SYNTHETIC initial timeout', message_id='unknown-first')
        assert len(calls) == 1
        app.chat('SYNTHETIC independent turn', message_id='unknown-second')
        assert len(calls) == 2 and len(set(calls)) == 2
        assert app.runtime.store.one('cognitive_requests', row['request_id'])['reserved_cost_micro'] == row['reserved_cost_micro']
        clock.advance(DAY)
        assert resource_state(app.runtime.store, cap).unresolved_terminal_calls == 0
    assert existing_identity(home)[2] == 0
    assert identity_request_state(home)[3] == 2


def test_active_call_blocks_identity_gate_even_across_day(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    initialize(home, active=0)
    clock = VirtualClock()
    monkeypatch.setattr(OpenAIJSONTransport, 'exchange', lambda *args: (_ for _ in ()).throw(TimeoutError()))
    with relay(home) as (router, _), LifeApplication(home, clock=clock, router=router) as app:
        app.pause()
        app.chat('SYNTHETIC timed out', message_id='active-check')
        row = app.runtime.store.all('cognitive_requests')[0]
        # Fixture-only mutation emulates a still-running dispatched attempt.
        with app.runtime.store.transaction('synthetic.active_check') as tx:
            tx.update('cognitive_requests', row['request_id'], state='CALLING')
        clock.advance(DAY)
        config = app.runtime.config
        assert resource_state(app.runtime.store, config).unresolved_live_calls == 1
        assert allocation_reason(app.runtime.store, config, {'event_type': 'USER_EVENT'}) == 'UNRESOLVED_PROVIDER_CALL'
        assert existing_identity(home)[2] == 1


def test_terminal_unknown_survives_actual_dev_release_change(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    home = tmp_path / 'home'
    initialize(home, active=0)
    clock = VirtualClock()
    monkeypatch.setattr(OpenAIJSONTransport, 'exchange', lambda *args: (_ for _ in ()).throw(TimeoutError()))
    with relay(home) as (router, _), LifeApplication(home, clock=clock, router=router) as app:
        app.pause()
        app.chat('SYNTHETIC timeout before release', message_id='release-unknown')
        row = app.runtime.store.all('cognitive_requests')[0]
        assert row['state'] == 'UNKNOWN'
    identity,lineage,active,terminal = identity_request_state(home)
    assert active == 0 and terminal == 1
    revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
    release = Release(release_id='before', root=str(root), python=sys.executable, source_commit=revision)
    candidate = release.model_copy(update={'release_id': 'after'})
    supervisor = Supervisor(home, tmp_path/'host', Binding(subject_id=identity,lineage_binding=lineage),
                            [release,candidate], active_release='before')
    try:
        first = supervisor.start()
        result = supervisor.change_release('after')
        assert result['subject_id'] == first['subject_id'] == identity
        assert result['unknown_requests'] == 1
        assert identity_request_state(home)[2:] == (0,1)
    finally:
        try: supervisor.stop()
        finally: supervisor.close()
