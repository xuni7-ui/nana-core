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
        protocol=changes.pop('protocol','OPENAI_COMPATIBLE_CHAT'), locality='REMOTE', base_url='https://catalog.example/v1',
        secret_ref='catalog.main', **changes)


@pytest.mark.parametrize('protocol',['OPENAI_COMPATIBLE_CHAT','ANTHROPIC'])
def test_authenticated_catalog_from_existing_vault_does_not_change_routes(running, monkeypatch,protocol):
    server, service = running
    headers = login(server, service)
    service.allow_provider_configuration = True
    service.credential_resolver = MemorySecretResolver()
    service.credential_resolver.bind('catalog.main', 'TEST_ONLY_NOT_SECRET_CATALOG')
    cfg, authority = config_service(service.supervisor.home/'providers.json')
    update(cfg, authority, 'UPSERT_PROVIDER', provider=profile(protocol=protocol))
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


def test_native_catalog_uses_native_headers_and_reports_remaining_pages(monkeypatch):
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    class Opener:
        def open(self,request,timeout):
            calls.append(request)
            assert request.full_url=='https://catalog.example/v1/models?limit=256' and request.get_method()=='GET'
            assert request.get_header('X-api-key')=='TEST_ONLY_NOT_SECRET_CATALOG'
            assert request.get_header('Anthropic-version')=='2026-10-21'
            assert request.get_header('Authorization') is None and request.data is None
            return Response(json.dumps({'data':[{'type':'model','id':'native.synthetic'}],'has_more':True}).encode())
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda handler:Opener())
    result=provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG')
    assert result=={'models':['native.synthetic'],'truncated':True} and len(calls)==1


def test_native_catalog_follows_returned_cursor_with_native_headers_and_no_inference(monkeypatch):
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    pages=[{'data':[{'id':'native.alpha'},{'id':'native.beta'}],'has_more':True,'last_id':'native.beta'},
           {'data':[{'id':'native.beta'},{'id':'native.gamma'}],'has_more':False,'last_id':'native.gamma'}]
    class Opener:
        def open(self,request,timeout):
            assert request.full_url==('https://catalog.example/v1/models?limit=256' if not calls else 'https://catalog.example/v1/models?limit=254&after_id=native.beta')
            assert request.get_method()=='GET' and request.data is None and 0<timeout<=10
            assert request.get_header('X-api-key')=='TEST_ONLY_NOT_SECRET_CATALOG'
            assert request.get_header('Authorization') is None
            calls.append(request.full_url)
            return Response(json.dumps(pages[len(calls)-1]).encode())
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda handler:Opener())
    result=provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG')
    assert result=={'models':['native.alpha','native.beta','native.gamma'],'truncated':False}
    assert len(calls)==2


@pytest.mark.parametrize('stop',['cycle','deadline','pages','hostile-cursor'])
def test_native_pagination_stops_honestly_without_retrying_or_leaking_cursor(monkeypatch,stop):
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    class Opener:
        def open(self,request,timeout):
            assert request.full_url.startswith('https://catalog.example/v1/models')
            assert 'TEST_ONLY_NOT_SECRET_CATALOG' not in request.full_url
            calls.append(request.full_url)
            model='native.page-'+str(len(calls)) if stop=='pages' else 'native.same'
            cursor='https://untrusted.invalid/TEST_ONLY_NOT_SECRET_CATALOG' if stop=='hostile-cursor' else model
            return Response(json.dumps({'data':[{'id':model}],'has_more':True,'last_id':cursor}).encode())
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda handler:Opener())
    if stop=='deadline':
        clock=iter((0.,11.,12.,13.));monkeypatch.setattr(provider_models.time,'monotonic',lambda:next(clock))
    result=provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG')
    assert result['truncated'] is True and result['models']
    assert len(calls)==({'cycle':2,'deadline':1,'pages':8,'hostile-cursor':1}[stop])


@pytest.mark.parametrize('failure,code',[('auth','PROVIDER_CATALOG_AUTH'),('bytes','PROVIDER_CATALOG_BOUND')])
def test_native_later_page_failures_do_not_hide_partial_read_or_expand_byte_budget(monkeypatch,failure,code):
    import urllib.error
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    class Opener:
        def open(self,request,timeout):
            calls.append(request.full_url)
            if len(calls)==2 and failure=='auth':
                raise urllib.error.HTTPError(request.full_url,403,'Untrusted reason',{},io.BytesIO(b'TEST_ONLY_NOT_SECRET_CATALOG'))
            page={'data':[{'id':'native.page-'+str(len(calls))}],'has_more':True,'last_id':'native.page-'+str(len(calls))}
            if failure=='bytes':page['untrusted_padding']='x'*180000
            return Response(json.dumps(page).encode())
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda handler:Opener())
    with pytest.raises(ApiError,match=code) as error:
        provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG')
    assert len(calls)==2 and 'TEST_ONLY_NOT_SECRET_CATALOG' not in str(error.value)

def test_native_explicit_continuation_keeps_upstream_order_inside_bounded_batch(monkeypatch):
    calls = []
    class Response(io.BytesIO):
        status = 200
        headers = Message()
    Response.headers['Content-Type'] = 'application/json'
    pages = [{'data': [{'id': 'z-model'}, {'id': 'a/model:1'}], 'has_more': True, 'last_id': 'a/model:1'},
             {'data': [{'id': 'b-final'}], 'has_more': False}]
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            assert request.get_header('X-api-key') == 'TEST_ONLY_NOT_SECRET_CATALOG'
            assert request.data is None
            return Response(json.dumps(pages[len(calls)-1]).encode())
    monkeypatch.setattr(provider_models.urllib.request, 'build_opener', lambda handler: Opener())
    result = provider_models.read_catalog(profile(protocol='ANTHROPIC'), 'TEST_ONLY_NOT_SECRET_CATALOG', after_id='previous/model:1')
    assert calls == ['https://catalog.example/v1/models?limit=256&after_id=previous%2Fmodel%3A1',
                     'https://catalog.example/v1/models?limit=254&after_id=a%2Fmodel%3A1']
    assert result == {'models': ['a/model:1', 'b-final', 'z-model'], 'truncated': False}


@pytest.mark.parametrize('rows,has_more,last_id,after_id', [
    ([], True, 'empty', None),
    ([{'id': 'one'}], True, 'not-in-page', None),
    ([{'id': 'one'}], True, None, None),
    ([{'id': 'one'}], True, 'one', 'one'),
    ([{'id': 'one'}], 'yes', 'one', None),
    ([{'id': f'model-{n}'} for n in range(257)], True, 'model-256', None),
])
def test_native_invalid_pagination_keeps_partial_truth_without_a_cursor(monkeypatch, rows, has_more, last_id, after_id):
    class Response(io.BytesIO):
        status = 200
        headers = Message()
    Response.headers['Content-Type'] = 'application/json'
    class Opener:
        def open(self, request, timeout):
            return Response(json.dumps({'data': rows, 'has_more': has_more, 'last_id': last_id}).encode())
    monkeypatch.setattr(provider_models.urllib.request, 'build_opener', lambda handler: Opener())
    if type(has_more) is not bool:
        with pytest.raises(ApiError, match='PROVIDER_CATALOG_FORMAT'):
            provider_models.read_catalog(profile(protocol='ANTHROPIC'), 'TEST_ONLY_NOT_SECRET_CATALOG', after_id=after_id)
    else:
        result = provider_models.read_catalog(profile(protocol='ANTHROPIC'), 'TEST_ONLY_NOT_SECRET_CATALOG', after_id=after_id)
        assert result['truncated'] is True and result.get('next_after_id') is None
        assert len(result['models']) <= 256


def test_authenticated_catalog_page_keeps_host_revision_and_authority_checks(running, monkeypatch):
    server, service = running
    headers = login(server, service)
    service.allow_provider_configuration = True
    service.credential_resolver = MemorySecretResolver()
    service.credential_resolver.bind('catalog.main', 'TEST_ONLY_NOT_SECRET_CATALOG')
    cfg, authority = config_service(service.supervisor.home/'providers.json')
    update(cfg, authority, 'UPSERT_PROVIDER', provider=profile(protocol='ANTHROPIC'))
    life = load_config(service.supervisor.home)
    update_config(service.supervisor.home, life.model_copy(update={
        'revision': life.revision+1, 'provider_hosts': ('catalog.example',)}), expected_revision=life.revision)
    before = (service.supervisor.home/'providers.json').read_bytes()
    calls = []
    def read(p, value, *, after_id=None):
        calls.append(after_id)
        return {'models': ['page-two'], 'truncated': False, 'next_after_id': None}
    monkeypatch.setattr(provider_models, 'read_catalog', read)
    path = 'providers/models?provider_profile_id=catalog.main&profile_revision=1&after_id=page%2Fone%3A1'
    assert http(server, path)[0] == 401 and not calls
    status, value, _ = http(server, path, headers=headers)
    assert status == 200 and calls == ['page/one:1']
    assert value['data']['models'] == ['page-two'] and value['data']['next_after_id'] is None
    assert value['data']['configuration_changed'] is False and value['data']['inference_calls'] == 0
    assert (service.supervisor.home/'providers.json').read_bytes() == before
    assert 'TEST_ONLY_NOT_SECRET_CATALOG' not in json.dumps(value)
    assert http(server, path, headers=headers)[0] == 429 and len(calls) == 1
    service.provider_catalog_after = 0
    assert http(server, path.replace('revision=1', 'revision=2'), headers=headers)[0] == 409
    for suffix in ['&after_id=duplicate', '&extra=1']:
        assert http(server, path+suffix, headers=headers)[0] == 400
    for cursor in ['', 'bad%26injection', 'a'*97]:
        assert http(server, path.rsplit('=', 1)[0]+'='+cursor, headers=headers)[0] == 400
    update(cfg, authority, 'UPSERT_PROVIDER', provider=profile())
    assert http(server, path.replace('revision=1', 'revision=2'), headers=headers)[0] == 409
    assert len(calls) == 1


def test_compatible_partial_catalog_does_not_invent_a_pagination_protocol(monkeypatch):
    calls = []
    class Response(io.BytesIO):
        status = 200
        headers = Message()
    Response.headers['Content-Type'] = 'application/json'
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            return Response(json.dumps({'data': [{'id': f'model-{n:03d}'} for n in range(300)],
                'has_more': True, 'last_id': 'unqualified-cursor'}).encode())
    monkeypatch.setattr(provider_models.urllib.request, 'build_opener', lambda handler: Opener())
    result = provider_models.read_catalog(profile(), 'TEST_ONLY_NOT_SECRET_CATALOG')
    assert len(result['models']) == 256 and result['truncated'] is True and result.get('next_after_id') is None
    assert calls == ['https://catalog.example/v1/models']
    with pytest.raises(ApiError, match='PROVIDER_CATALOG_QUERY_REQUIRED'):
        provider_models.read_catalog(profile(), 'TEST_ONLY_NOT_SECRET_CATALOG', after_id='unqualified-cursor')
    assert len(calls) == 1


def test_native_visible_limit_returns_exact_cursor_and_explicit_read_loses_no_ids(monkeypatch):
    calls = []
    first_ids = [f'model-{n:03d}' for n in reversed(range(256))]
    class Response(io.BytesIO):
        status = 200
        headers = Message()
    Response.headers['Content-Type'] = 'application/json'
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            value = ({'data': [{'id': mid} for mid in first_ids], 'has_more': True, 'last_id': first_ids[-1]}
                if len(calls) == 1 else {'data': [{'id': 'model-tail'}], 'has_more': False})
            return Response(json.dumps(value).encode())
    monkeypatch.setattr(provider_models.urllib.request, 'build_opener', lambda handler: Opener())
    first = provider_models.read_catalog(profile(protocol='ANTHROPIC'), 'TEST_ONLY_NOT_SECRET_CATALOG')
    assert first['truncated'] and first['next_after_id'] == 'model-000'
    assert first['models'][-1] == 'model-255' and len(calls) == 1
    last = provider_models.read_catalog(profile(protocol='ANTHROPIC'), 'TEST_ONLY_NOT_SECRET_CATALOG', after_id=first['next_after_id'])
    assert last == {'models': ['model-tail'], 'truncated': False}
    assert calls == ['https://catalog.example/v1/models?limit=256',
        'https://catalog.example/v1/models?limit=256&after_id=model-000']
    assert set(first['models']+last['models']) == set(first_ids+['model-tail'])
