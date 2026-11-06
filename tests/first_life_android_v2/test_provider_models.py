"""Actual authenticated BFF routing; outbound provider catalog is a fixture."""
import io
import json
from email.message import Message

import pytest

from nana_core.life.config import load_config, update_config
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.life.live_api.contracts import ApiError
from nana_core.life.live_api import provider_models
from nana_core.continuity.provider_config import ProviderProfile
from tests.provider_routing.helpers import config_service, update
from .test_http_integration import running, http, login


def profile(**changes):
    return ProviderProfile(provider_profile_id='catalog.main', display_name='Catalog',
        protocol='OPENAI_COMPATIBLE_CHAT', locality='REMOTE', base_url='https://catalog.example/v1',
        secret_ref='catalog.main', **changes)


def test_authenticated_catalog_from_existing_vault_does_not_change_routes(running, monkeypatch):
    server, service = running
    headers = login(server, service)
    service.allow_provider_configuration = True
    service.credential_resolver = MemorySecretResolver()
    service.credential_resolver.bind('catalog.main', 'TEST_ONLY_NOT_SECRET_CATALOG')
    cfg, authority = config_service(service.supervisor.home/'providers.json')
    update(cfg, authority, 'UPSERT_PROVIDER', provider=profile())
    life = load_config(service.supervisor.home)
    update_config(service.supervisor.home, life.model_copy(update={
        'revision':life.revision+1, 'provider_hosts':('catalog.example',)}), expected_revision=life.revision)
    before = (service.supervisor.home/'providers.json').read_bytes()
    calls = []
    def read(p, value):
        calls.append(p.provider_profile_id)
        assert value=='TEST_ONLY_NOT_SECRET_CATALOG'
        return {'models':['catalog.model'], 'truncated':False}
    monkeypatch.setattr(provider_models, 'read_catalog', read)
    path = 'providers/models?provider_profile_id=catalog.main&profile_revision=1'
    assert http(server, path)[0]==401
    status, result, _ = http(server, path, headers=headers)
    assert status==200 and result['data']['models']==['catalog.model']
    assert result['data']['qualification']=='NOT_ESTABLISHED'
    assert result['data']['inference_calls']==0 and len(calls)==1
    assert 'TEST_ONLY_NOT_SECRET_CATALOG' not in json.dumps(result)
    assert (service.supervisor.home/'providers.json').read_bytes()==before
    assert http(server, path, headers=headers)[0]==429 and len(calls)==1
    service.provider_catalog_after = 0
    assert http(server, path.replace('revision=1','revision=2'), headers=headers)[0]==409
    life = load_config(service.supervisor.home)
    update_config(service.supervisor.home, life.model_copy(update={
        'revision':life.revision+1, 'provider_hosts':()}), expected_revision=life.revision)
    assert http(server, path, headers=headers)[0]==403 and len(calls)==1
    assert http(server, path+'&profile_revision=1', headers=headers)[0]==400


@pytest.mark.parametrize('rows,code', [
    ([{'id':'model.good'},{'id':'model.good'}], None),
    ([{'id':'<script>bad</script>'}], 'PROVIDER_CATALOG_MODEL_INVALID'),
    ([{'id':'TEST_ONLY_NOT_SECRET_CATALOG'}], 'PROVIDER_CATALOG_MODEL_INVALID'),
    ([{'id':'normal'}, {'id':42}], 'PROVIDER_CATALOG_MODEL_INVALID'),
])
def test_catalog_wire_is_bounded_and_no_redirect_or_inference(monkeypatch, rows, code):
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            assert request.full_url=='https://catalog.example/v1/models'
            assert request.get_method()=='GET' and timeout==10
            assert request.data is None
            return Response(json.dumps({'data':rows}).encode())
    def build(handler):
        assert isinstance(handler, provider_models._NoRedirect)
        return Opener()
    monkeypatch.setattr(provider_models.urllib.request, 'build_opener', build)
    if code:
        with pytest.raises(ApiError, match=code):
            provider_models.read_catalog(profile(), 'TEST_ONLY_NOT_SECRET_CATALOG')
    else:
        assert provider_models.read_catalog(profile(), 'TEST_ONLY_NOT_SECRET_CATALOG')['models']==['model.good']
    assert len(calls)==1
