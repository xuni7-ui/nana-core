"""Entry wiring is offline; only the original foreground Runtime may run."""
import json
from types import SimpleNamespace

import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
from tests.h1_live_semantics.test_wire import Opener, Response
from tests.live_response.test_response_contract import make_request, envelope
from tests.world_loop.helpers import fresh
from tools.nana_first_life_live_response import entry


def prepare(monkeypatch, tmp_path):
    home = tmp_path / 'home'
    output = tmp_path / 'metadata.json'
    resolver = object()
    router = object()
    monkeypatch.setattr(entry, 'HOME', home)
    monkeypatch.setattr(entry, 'preflight', lambda *a, **k: {'state': 'PREFLIGHT_PASS', 'identity_id': entry.IDENTITY})
    monkeypatch.setattr(entry, 'load_config', lambda *a: SimpleNamespace(provider_timeout_ms=15000, remote_privacy=('PUBLIC', 'PROJECT')))
    def factory(*a, **k):
        assert k['resolver'] is resolver and k['authorized']
        return router
    monkeypatch.setattr(entry, 'configured_router', factory)
    monkeypatch.setattr(entry, 'scan_and_save', lambda h, p, report, r: p.write_text(json.dumps(report)))
    return home, output, resolver, router


def test_entry_uses_existing_runtime_and_keeps_only_operational_metadata(tmp_path, monkeypatch):
    home, output, resolver, router = prepare(monkeypatch, tmp_path)
    original = OpenAIJSONTransport.exchange
    with fresh(tmp_path / 'synthetic/self.db') as runtime:
        port, session, request = make_request(runtime)
        port.opener = Opener(Response(json.dumps(envelope()).encode()))
        def run(path, seconds, **kwargs):
            assert path == home and seconds == 30
            assert kwargs == {'headless': True, 'router': router, 'control_enabled': True}
            assert session.execute(request.request_id)['state'] == 'PROPOSED'
        monkeypatch.setattr('nana_core.life.__main__.run', run)
        report = entry.start(home, 30, output, resolver)
    assert OpenAIJSONTransport.exchange is original
    assert len(report['calls']) == 1 and report['calls'][0]['parser']['stage'] == 'COMPLETE'
    assert report['human_review'] == 'NOT_RUN' and not report['transcript_saved']
    assert 'A synthetic sourced proposal' not in output.read_text()
    assert 'TEST_ONLY_NOT_SECRET' not in output.read_text()


@pytest.mark.parametrize('failure', ['unknown', 'host', 'privacy'])
def test_entry_fails_closed_without_retry_and_restores_observer(tmp_path, monkeypatch, failure):
    home, output, resolver, router = prepare(monkeypatch, tmp_path)
    original = OpenAIJSONTransport.exchange
    if failure == 'unknown':
        monkeypatch.setattr(entry, 'preflight', lambda *a, **k: {'state': 'FIRST_LIFE_START_BLOCKED', 'identity_id': entry.IDENTITY})
    elif failure == 'privacy':
        monkeypatch.setattr(entry, 'load_config', lambda *a: SimpleNamespace(provider_timeout_ms=15000, remote_privacy=('SECRET',)))
    else:
        with fresh(tmp_path / 'synthetic/self.db') as runtime:
            port, session, request = make_request(runtime)
            port.endpoint = 'https://unexpected.example/chat/completions'
            port.opener = Opener(Response(json.dumps(envelope()).encode()))
            def run(*a, **k):
                result = session.execute(request.request_id)
                assert result['state'] == 'FAILED'
                assert not port.opener.requests
            monkeypatch.setattr('nana_core.life.__main__.run', run)
            assert not entry.start(home, 30, output, resolver)['calls']
        assert OpenAIJSONTransport.exchange is original
        return
    with pytest.raises(CoreError):
        entry.start(home, 30, output, resolver)
    assert OpenAIJSONTransport.exchange is original and not output.exists()
