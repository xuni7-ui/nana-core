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
            assert request.full_url=='https://catalog.example/v1/models' and request.get_method()=='GET'
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
            assert request.full_url==('https://catalog.example/v1/models' if not calls else 'https://catalog.example/v1/models?after_id=native.beta')
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


def test_native_catalog_exposes_safe_continuation_and_resumes_after_its_page_bound(monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    class Opener:
        def open(self,request,timeout):
            url=urlsplit(request.full_url);query=parse_qs(url.query)
            assert url.hostname=='catalog.example' and url.path=='/v1/models'
            assert set(query)<= {'after_id'} and 0<timeout<=10
            assert request.get_header('X-api-key')=='TEST_ONLY_NOT_SECRET_CATALOG'
            assert request.get_header('Authorization') is None and request.data is None
            index=int(query['after_id'][0].rsplit('-',1)[1])+1 if query else 1
            calls.append(index);last='native.page-'+str(index)
            return Response(json.dumps({'data':[{'id':last}],'has_more':index<10,'last_id':last}).encode())
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda handler:Opener())
    first=provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG')
    assert first['truncated'] and first.get('next_after_id')=='native.page-8'
    assert calls==list(range(1,9))
    second=provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG',after_id=first['next_after_id'])
    assert second=={'models':['native.page-10','native.page-9'],'truncated':False}
    assert calls==list(range(1,11))


@pytest.mark.parametrize('cursor',['', 'invalid?query', 'TEST_ONLY_NOT_SECRET_CATALOG'])
def test_native_resume_rejects_invalid_or_credential_cursor_before_network(monkeypatch,cursor):
    def forbidden(*args,**kwargs):raise AssertionError('invalid cursor must not reach a network opener')
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',forbidden)
    with pytest.raises(ApiError,match='PROVIDER_CATALOG_CURSOR_INVALID'):
        provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG',after_id=cursor)


def test_authenticated_native_continuation_keeps_revision_throttle_and_config(running,monkeypatch):
    server,service=running;headers=login(server,service)
    service.allow_provider_configuration=True;service.credential_resolver=MemorySecretResolver()
    service.credential_resolver.bind('catalog.main','TEST_ONLY_NOT_SECRET_CATALOG')
    cfg,authority=config_service(service.supervisor.home/'providers.json')
    update(cfg,authority,'UPSERT_PROVIDER',provider=profile(protocol='ANTHROPIC'))
    life=load_config(service.supervisor.home)
    update_config(service.supervisor.home,life.model_copy(update={'revision':life.revision+1,'provider_hosts':('catalog.example',)}),expected_revision=life.revision)
    before=(service.supervisor.home/'providers.json').read_bytes();calls=[]
    def read(p,key,*,after_id=None):
        assert p.provider_profile_id=='catalog.main' and key=='TEST_ONLY_NOT_SECRET_CATALOG'
        calls.append(after_id)
        return {'models':['native.next' if after_id else 'native.first'],'truncated':after_id is None,**({'next_after_id':'native.first'} if after_id is None else {})}
    monkeypatch.setattr(provider_models,'read_catalog',read)
    path='providers/models?provider_profile_id=catalog.main&profile_revision=1'
    assert http(server,path+'&after_id=native.first')[0]==401 and not calls
    status,first,_=http(server,path,headers=headers)
    assert status==200 and first['data']['next_after_id']=='native.first'
    assert 0<=first['data']['retry_after_ms']<=10000
    assert http(server,path+'&after_id=native.first',headers=headers)[0]==429 and calls==[None]
    service.provider_catalog_after=0
    status,last,_=http(server,path+'&after_id=native.first',headers=headers)
    assert status==200 and last['data']['models']==['native.next'] and 'next_after_id' not in last['data']
    assert last['data']['continued_after_id']=='native.first' and 'continued_after_id' not in first['data']
    assert last['data']['inference_calls']==0 and calls==[None,'native.first']
    for suffix in ('&after_id=','&after_id=bad%3Fquery','&after_id=native.first&after_id=native.other'):
        assert http(server,path+suffix,headers=headers)[0]==400
    assert http(server,path.replace('revision=1','revision=2')+'&after_id=native.first',headers=headers)[0]==409
    assert len(calls)==2 and (service.supervisor.home/'providers.json').read_bytes()==before
    assert 'TEST_ONLY_NOT_SECRET_CATALOG' not in json.dumps([first,last])


def test_catalog_does_not_send_native_cursor_to_compatible_protocol(monkeypatch):
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda *args:pytest.fail('no network for incompatible cursor'))
    with pytest.raises(ApiError,match='PROVIDER_CATALOG_CURSOR_UNSUPPORTED'):
        provider_models.read_catalog(profile(),'TEST_ONLY_NOT_SECRET_CATALOG',after_id='native.first')


def test_oversized_native_page_never_skips_hidden_models_with_a_resume_cursor(monkeypatch):
    class Response(io.BytesIO):
        status=200
        headers=Message()
    Response.headers['Content-Type']='application/json'
    class Opener:
        def open(self,request,timeout):
            return Response(json.dumps({'data':[{'id':'native.model-'+str(i)} for i in range(300)],'has_more':True,'last_id':'native.model-299'}).encode())
    monkeypatch.setattr(provider_models.urllib.request,'build_opener',lambda handler:Opener())
    result=provider_models.read_catalog(profile(protocol='ANTHROPIC'),'TEST_ONLY_NOT_SECRET_CATALOG')
    assert len(result['models'])==256 and result['truncated'] and 'next_after_id' not in result
