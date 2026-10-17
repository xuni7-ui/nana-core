import json,os
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.sensors.contracts import *
from nana_core.continuity.sensors.config import *
from nana_core.continuity.sensors.adapters import *
from nana_core.presence.authority import VirtualClock

def profile(**kw):
    return PerceptionSourceProfile(**dict(dict(source_profile_id='screen.a',display_name='Screen',source_kind='SCREEN',modality='IMAGE',adapter_ref='fixture',resource_ref='sample',scope='world',entity_id='observer'),**kw))
def service(tmp_path):
    resolver=HostPerceptionResolver();port=SyntheticScreenAdapter(VirtualClock(),b'not opened');resolver.bind('fixture','sample',port)
    a=PerceptionConfigurationAuthority();s=PerceptionConfigService(tmp_path/'host/sources.json',a,resolver);s.initialize(a);return s,a,resolver,port

def test_config_cas_resolver_and_no_secret(tmp_path):
    s,a,resolver,port=service(tmp_path);p=profile()
    c=s.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=0,profile=p),a)
    assert c.revision==1 and s.load()==c and port.bytes_read==0
    with pytest.raises(CoreError,match='REVISION_CONFLICT'):s.update(SourceCommand(operation='REMOVE_PERCEPTION_SOURCE',expected_revision=0,target_id=p.source_profile_id),a)
    with pytest.raises(CoreError,match='SOURCE_UNAVAILABLE'):s.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=1,profile=profile(resource_ref='missing')),a)
    with pytest.raises(CoreError,match='AUTHORITY'):s.update(SourceCommand(operation='REMOVE_PERCEPTION_SOURCE',expected_revision=1,target_id=p.source_profile_id),PerceptionConfigurationAuthority())
    assert (s._path.stat().st_mode&0o777)==0o600
    s.update(SourceCommand(operation='DISABLE_PERCEPTION_SOURCE',expected_revision=1,target_id=p.source_profile_id),a)
    assert not s.load().sources[0].enabled

@pytest.mark.parametrize('body',[b'{',b'{"schema_version":9}',b'{"revision":1,"revision":2}',b'{"unknown":true}'])
def test_corrupt_fail_closed(tmp_path,body):
    s,a,_,_=service(tmp_path);s._path.write_bytes(body)
    with pytest.raises(CoreError):s.load()
    with pytest.raises(CoreError):s.initialize(a)

@pytest.mark.parametrize('change',[dict(min_interval_ms=40000),dict(semantic_operations=('AUDIO_UNDERSTAND',)),dict(source_kind='MICROPHONE'),dict(adapter_ref='../device'),dict(retention_policy='PERSIST')])
def test_invalid_profile(change):
    with pytest.raises(ValueError):profile(**change)

def test_duplicate_source():
    with pytest.raises(ValueError):PerceptionConfiguration(sources=(profile(),profile()))

def test_removed_recreated_source_never_reuses_revision(tmp_path):
    s,a,_,_=service(tmp_path);p=profile()
    s.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=0,profile=p),a)
    s.update(SourceCommand(operation='REMOVE_PERCEPTION_SOURCE',expected_revision=1,target_id=p.source_profile_id),a)
    c=s.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=2,profile=p),a)
    assert c.sources[0].revision==3
