"""Regression boundaries of reuse: current bytes, file trust and runtime state."""
import os

import pytest
from pydantic import ValidationError

from nana_core.contracts import CoreError
from nana_core.continuity.provider_config import (
    ProviderConfigService, ProviderConfiguration, ProviderConfigurationAuthority,
    ProviderProfile, _validated_configuration,
)
from nana_core.continuity.provider_routing import ProviderSettingsService, RuntimeProviderFactory, RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from .helpers import config_service, update, Resolver


def test_same_metadata_edit_atomic_replace_and_other_instance_are_immediately_visible(tmp_path):
    path=tmp_path/'one/providers.json';service,authority=config_service(path)
    update(service,authority,'UPSERT_PROVIDER',provider=ProviderProfile(
        provider_profile_id='fixture.a',display_name='Name A',protocol='LOCAL',locality='LOCAL_FIXTURE'))
    original=service.load();before=path.stat();raw=path.read_bytes()
    other,_=config_service(tmp_path/'two/providers.json')
    other._atomic(original);assert other.load()==original
    # Exact bytes rather than stat metadata are the source of invalidation.
    path.write_bytes(raw.replace(b'Name A',b'Name B'));os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
    assert path.stat().st_size==before.st_size and path.stat().st_mtime_ns==before.st_mtime_ns
    assert service.load().providers[0].display_name=='Name B'
    assert other.load().providers[0].display_name=='Name A'
    update(service,authority,'DISABLE_PROVIDER',target_id='fixture.a')
    assert service.load().revision==2 and not service.load().providers[0].enabled
    assert other.load().revision==1 and other.load().providers[0].enabled
    with pytest.raises(ValidationError):original.providers[0].display_name='mutated'
    # A replacement file containing a previous document is not a stale revision.
    service._atomic(original);assert service.load()==original


@pytest.mark.parametrize('change,code',[
    ('permission','PROVIDER_CONFIG_FILE_UNSAFE'),('hardlink','PROVIDER_CONFIG_FILE_UNSAFE'),
    ('symlink','PROVIDER_CONFIG_INVALID'),('missing','PROVIDER_CONFIG_UNAVAILABLE'),
    ('duplicate','PROVIDER_CONFIG_INVALID'),('oversize','PROVIDER_CONFIG_INVALID'),
])
def test_warm_parse_does_not_bypass_file_checks_or_accept_corruption(tmp_path,change,code):
    path=tmp_path/'host/providers.json';service,_=config_service(path);service.load()
    if change=='permission':path.chmod(0o644)
    elif change=='hardlink':os.link(path,path.with_name('other.json'))
    elif change=='symlink':
        path.rename(path.with_name('target.json'));path.symlink_to(path.with_name('target.json'))
    elif change=='missing':path.unlink()
    elif change=='duplicate':path.write_bytes(b'{"revision":0,"revision":1}')
    else:path.write_bytes(b' '*262145)
    with pytest.raises(CoreError,match=code):service.load()


def test_reused_document_does_not_cache_credential_availability_or_custom_validation(tmp_path):
    path=tmp_path/'host/providers.json';service,authority=config_service(path)
    update(service,authority,'UPSERT_PROVIDER',provider=ProviderProfile(provider_profile_id='remote.a',
        display_name='Remote',protocol='OPENAI_COMPATIBLE_CHAT',locality='REMOTE',
        base_url='https://provider.example/v1',secret_ref='remote.a'))
    resolver=Resolver(('remote.a',))
    projection=ProviderSettingsService(service,authority,RuntimeProviderFactory(ProviderRegistry(),resolver,RoutingPolicy()))
    assert projection.projection()['providers'][0]['secret_state']=='AVAILABLE'
    resolver.refs.clear()
    assert projection.projection()['providers'][0]['secret_state']=='MISSING'
    assert resolver.resolved==0
    original=service.load()
    class CustomDocument:
        count=0
        @classmethod
        def model_validate_json(cls,raw):
            cls.count+=1
            return ProviderConfiguration.model_validate_json(raw)
    service.document_type=CustomDocument
    assert service.load()==service.load()==original
    assert CustomDocument.count==2
    # Finite churn retains at most four immutable parse results.
    _validated_configuration.cache_clear()
    for revision in range(7):
        _validated_configuration(original.model_copy(update={'revision':revision}).model_dump_json().encode())
    assert _validated_configuration.cache_info().currsize==4
