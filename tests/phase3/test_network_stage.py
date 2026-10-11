from nana_core.contracts import CoreError
from nana_core.development.public_http import PublicHTTPTransport,WebSpec
import pytest


def test_dns_failure_stage_is_distinct_from_proxy_or_http(tmp_path,monkeypatch):
    policy=tmp_path/'policy.json';policy.write_text('{"version":1,"http_proxy":"http://fixture.invalid:8080","http_network_policy":{"type":"unrestricted"}}')
    monkeypatch.setenv('HTTPS_PROXY','http://fixture.invalid:8080')
    def fail(*args,**kwargs):raise OSError('synthetic resolver unavailable')
    transport=PublicHTTPTransport(resolver=fail,policy_path=policy)
    with pytest.raises(CoreError,match='WEB_DNS_FAILED'):transport.fetch(WebSpec(url='https://example.com/'))
    assert transport.last_stage=='DNS_FIRST'
    assert transport.http_requests==transport.proxy_connections==0


def test_public_probe_never_accepts_arbitrary_operator_url_or_creates_workspace(tmp_path):
    from nana_core.phase3.public_probe import run
    root=tmp_path/'must-not-exist'
    with pytest.raises(ValueError,match='operator-approved'):
        run(root,'https://arbitrary.example.invalid/private')
    assert not root.exists()
