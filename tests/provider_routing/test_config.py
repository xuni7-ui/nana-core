import json,os,signal,subprocess,sys
from pathlib import Path
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError
from .helpers import *

def test_host_document_cas_dependencies_and_secret_handle(tmp_path):
    s,a=config_service(tmp_path/'host/providers.json')
    update(s,a,'UPSERT_PROVIDER',provider=provider())
    stale=s.load().revision;update(s,a,'UPSERT_MODEL',model=model())
    with pytest.raises(CoreError,match='REVISION_CONFLICT'):s.update(ProviderCommand(operation='DISABLE_PROVIDER',expected_revision=stale,target_id='fixture.a'),a)
    update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='COGNITION',primary_model_profile_id='fixture.text'))
    with pytest.raises(CoreError,match='MODEL_PROFILE_IN_USE'):update(s,a,'REMOVE_MODEL',target_id='fixture.text')
    with pytest.raises(CoreError,match='PROVIDER_PROFILE_IN_USE'):update(s,a,'REMOVE_PROVIDER',target_id='fixture.a')
    with pytest.raises(CoreError,match='AUTHORITY_REQUIRED'):s.update(ProviderCommand(operation='DISABLE_PROVIDER',expected_revision=s.load().revision,target_id='fixture.a'),ProviderConfigurationAuthority())
    update(s,a,'DISABLE_PROVIDER',target_id='fixture.a');assert not s.load().providers[0].enabled
    update(s,a,'ENABLE_PROVIDER',target_id='fixture.a');assert s.load().providers[0].enabled
    update(s,a,'REMOVE_CAPABILITY_ROUTE',target_id='COGNITION');update(s,a,'REMOVE_MODEL',target_id='fixture.text');update(s,a,'REMOVE_PROVIDER',target_id='fixture.a')
    assert s.load().providers==() and s.load().revision==8
    assert (tmp_path/'host/providers.json').stat().st_mode&0o777==0o600
    secret=ResolvedSecret('TEST_ONLY_NOT_SECRET')
    assert 'TEST_ONLY_NOT_SECRET' not in str(secret)+repr(secret)
    import pickle
    with pytest.raises(TypeError,match='SERIALIZATION_DENIED'):pickle.dumps(secret)
    with pytest.raises(TypeError):json.dumps(secret)
    secret.clear();assert secret.reveal_for_header() is None

@pytest.mark.parametrize('url',['file:///tmp/x','ftp://public.example/v1','http://public.example/v1','https://user:pass@public.example/v1','https://public.example/v1#x','https://public.example/v1?key=x','https://127.0.0.1/v1','https://169.254.169.254/v1','https://localhost/v1','https://metadata.google.internal/v1','https://public.example/a/../v1','https://public.example//v1','https://bad_host.example/v1'])
def test_remote_endpoint_fail_closed(url):
    with pytest.raises(ValueError):ProviderProfile(provider_profile_id='relay.a',display_name='A',protocol='OPENAI_COMPATIBLE_CHAT',base_url=url,locality='REMOTE')

def test_typed_duplicate_unknown_remote_secret_and_version(tmp_path):
    p=provider();m=model()
    for body in [dict(providers=(p,p)),dict(providers=(p,),models=(m,m)),dict(models=(m,)),dict(routes=(CapabilityRoute(operation='VISION',primary_model_profile_id='fixture.missing'),)),dict(schema_version=2),dict(credential='TEST_ONLY_NOT_SECRET')]:
        with pytest.raises(ValidationError):ProviderConfiguration(**body)
    with pytest.raises(ValidationError):ProviderProfile(provider_profile_id='relay.a',display_name='A',protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://api.example/v1',locality='REMOTE',permitted_privacy=('SECRET',))

@pytest.mark.parametrize('bad',[b'{',b'{"schema_version":2}',b'{"revision":0,"revision":1}',b'{"unknown":true}',b'{"providers":[],"models":[],"routes":[{"operation":"VISION","primary_model_profile_id":"missing.model"}]}'])
def test_corruption_never_defaults(tmp_path,bad):
    s,a=config_service(tmp_path/'host/providers.json');(tmp_path/'host/providers.json').write_bytes(bad)
    with pytest.raises(CoreError,match='CONFIG_INVALID'):s.load()
    with pytest.raises(CoreError,match='CONFIG_INVALID'):s.initialize(a)

@pytest.mark.parametrize('stage',['TEMP_FSYNCED','REPLACED'])
def test_actual_sigkill_atomic_replace_and_reopen(tmp_path,stage):
    path=tmp_path/'host/providers.json';s,a=config_service(path)
    code='''import os,signal,sys
from nana_core.continuity.provider_config import *
a=ProviderConfigurationAuthority();s=ProviderConfigService(sys.argv[1],a)
def checkpoint(stage):
 if stage==sys.argv[2]:os.kill(os.getpid(),signal.SIGKILL)
s._checkpoint=checkpoint
p=ProviderProfile(provider_profile_id='fixture.a',display_name='A',protocol='LOCAL',locality='LOCAL_FIXTURE')
s.update(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=0,provider=p),a)
'''
    child=subprocess.run([sys.executable,'-c',code,str(path),stage],timeout=10)
    assert child.returncode==-signal.SIGKILL
    loaded=s.load();assert loaded.revision==(0 if stage=='TEMP_FSYNCED' else 1)
    assert len(loaded.providers)==loaded.revision
    # Temp files are untrusted crash residue, never read as config/defaults.
    assert ProviderConfigService(path,ProviderConfigurationAuthority()).load()==loaded

def test_symlink_config_never_resets_and_errors_do_not_echo_input(tmp_path):
    path=tmp_path/'host/providers.json';s,a=config_service(path);path.unlink();path.symlink_to(tmp_path/'missing')
    with pytest.raises(CoreError):s.initialize(a)
    assert path.is_symlink()
    with pytest.raises(ValidationError) as e:ProviderProfile(provider_profile_id='fixture.bad',display_name='x',protocol='LOCAL',locality='LOCAL_FIXTURE',api_key='TEST_ONLY_NOT_SECRET')
    assert 'TEST_ONLY_NOT_SECRET' not in str(e.value)
