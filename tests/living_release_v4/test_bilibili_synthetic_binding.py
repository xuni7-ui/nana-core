"""Synthetic origin cannot silently acquire a real public-network opener."""
import pytest
from nana_core.contracts import CoreError
from nana_core.life.bilibili import BilibiliPublicTransport,BilibiliLoopbackOpener
from tests.living_release_v4.bilibili_loopback import counterpart


@pytest.mark.parametrize('replacement',['missing','foreign-opener','changed-endpoint'])
def test_synthetic_transport_rejects_unbound_or_changed_origin_before_request(replacement):
    called=[]
    class NoNetwork:
        def open(self,*args,**kwargs):
            called.append(True)
            raise OSError('SYNTHETIC_SENTINEL_NO_NETWORK_EVER')
    if replacement=='changed-endpoint':
        port=BilibiliPublicTransport(authorized=True,origin='SYNTHETIC_FIXTURE',loopback_endpoint='http://127.0.0.1:9')
        port.opener.endpoint='https://api.bilibili.com'
        port.opener.opener=NoNetwork()
    else:
        port=BilibiliPublicTransport(authorized=True,origin='SYNTHETIC_FIXTURE')
        if replacement=='foreign-opener':port.opener=NoNetwork()
    # Never allow this regression test to issue a real request on old source.
    if replacement=='missing':
        assert port.opener is None
        with pytest.raises(CoreError,match='BILIBILI_SYNTHETIC_LOOPBACK_REQUIRED'):
            port.read_video('BV1t55v6DE2v')
    else:
        with pytest.raises(CoreError,match='BILIBILI_.*LOOPBACK'):
            port.read_video('BV1t55v6DE2v')
    assert called==[] and port.calls==0


def test_explicit_or_late_bound_literal_loopback_still_reads_and_keeps_origin():
    with counterpart() as (opener,platform):
        explicit=BilibiliPublicTransport(authorized=True,origin='SYNTHETIC_FIXTURE',loopback_endpoint=opener.endpoint)
        late=BilibiliPublicTransport(authorized=True,origin='SYNTHETIC_FIXTURE');late.opener=BilibiliLoopbackOpener(opener.endpoint)
        for port in (explicit,late):
            reading=port.read_video('BV1t55v6DE2v')
            assert reading.origin=='SYNTHETIC_FIXTURE' and port.calls>0
        assert platform['requests'] and platform['posts']==0
