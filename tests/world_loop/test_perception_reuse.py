"""One Store's confirmed observation, with byte, scope and erasure bindings."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.world_loop.perception import MediaDecoder,PerceptionService,PublicMediaSource
from nana_core.continuity.world_loop.samples import media_samples
from nana_core.presence.runtime import NanaRuntime
from .helpers import fresh,providers,policy


def descriptor(r,key,modality='IMAGE'):
    return PublicMediaSource(source_id=key,modality=modality,origin='SYNTHETIC',
        event_time_us=r.clock.utc_now_us(),observed_time_us=r.clock.utc_now_us())


class NoRepeatedDecode:
    def decode(self,*args,**kwargs):
        raise AssertionError('an existing observation must not need another decoder')


def counts(store):
    return {table:len(store.all(table)) for table in ('continuity_evidence','memories','continuity_records','world_beliefs')}


def test_confirmed_video_observation_survives_restart_without_decoder_or_new_writes(tmp_path):
    path=tmp_path/'s'/'self.db';data=media_samples()['VIDEO']
    with fresh(path) as r:
        source=descriptor(r,'same-video','VIDEO');service=PerceptionService(r.store,providers(),policy())
        ids=service.ingest(data,source,entity_id='observer',scope='world')
        prior=RecordService(r.store).read(ids[1]);config,clock,identity=r.config,r.clock,r.identity_id
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity
        service=PerceptionService(r.store,providers(),policy(),decoder=NoRepeatedDecode())
        before=counts(r.store);writes=r.store.db.total_changes
        assert service.ingest(data,source,entity_id='observer',scope='world')==ids
        assert counts(r.store)==before and r.store.db.total_changes==writes
        assert RecordService(r.store).read(ids[1])==prior
        MemoryService(r.store,r.authority).forget(ids[0],r.authority)
        before=counts(r.store);writes=r.store.db.total_changes
        with pytest.raises(CoreError,match='SOURCE_DELETED'):
            service.ingest(data,source,entity_id='observer',scope='world')
        assert counts(r.store)==before and r.store.db.total_changes==writes
        assert not RecordService(r.store).current_support(ids[1])


@pytest.mark.parametrize('binding',['entity','scope'])
def test_same_public_evidence_never_returns_a_memory_owned_by_another_binding(tmp_path,binding):
    with fresh(tmp_path/'s'/'self.db') as r:
        MemoryService(r.store).entity('other-observer','PERSON')
        readable=policy().model_copy(update={'allowed_scopes':('world','other')})
        service=PerceptionService(r.store,providers(),readable);data=media_samples()['IMAGE'];source=descriptor(r,'public-shared-evidence')
        first=service.ingest(data,source,entity_id='observer',scope='world')
        entity='other-observer' if binding=='entity' else 'observer';scope='other' if binding=='scope' else 'world'
        second=service.ingest(data,source,entity_id=entity,scope=scope)
        row=MemoryService(r.store).read(second[0])
        assert (row['entity_id'],row['scope'])==(entity,scope)
        assert second!=first and row['source_evidence_id']==MemoryService(r.store).read(first[0])['source_evidence_id']
        assert RecordService(r.store).read(second[1])['scope']==scope
        assert RecordService(r.store).current_support(second[1])
        assert len(r.store.all('identities'))==1


def test_saved_observation_requires_the_same_bytes_descriptor_and_current_memory(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        data=media_samples()['IMAGE'];source=descriptor(r,'same-image')
        ids=PerceptionService(r.store,providers(),policy()).ingest(data,source,entity_id='observer',scope='world')
        cached=PerceptionService(r.store,providers(),policy(),decoder=NoRepeatedDecode())
        before=counts(r.store);writes=r.store.db.total_changes
        for other,changed in ((data+b'extra',source),(data,source.model_copy(update={'modality':'VIDEO'}))):
            with pytest.raises(CoreError,match='SOURCE_KEY_COLLISION'):
                cached.ingest(other,changed,entity_id='observer',scope='world')
        assert counts(r.store)==before and r.store.db.total_changes==writes
        MemoryService(r.store,r.authority).set_lifecycle(ids[0],'SUPPRESSED',r.authority)
        with pytest.raises(CoreError,match='MEMORY_NOT_CURRENT'):
            cached.ingest(data,source,entity_id='observer',scope='world')


def test_incomplete_technical_ingress_resumes_from_its_original_evidence(tmp_path):
    from nana_core.continuity.providers import ProviderRegistry
    with fresh(tmp_path/'s'/'self.db') as r:
        data=media_samples()['IMAGE'];source=descriptor(r,'partial-image')
        unavailable=PerceptionService(r.store,ProviderRegistry(),policy())
        with pytest.raises(CoreError):unavailable.ingest(data,source,entity_id='observer',scope='world')
        raw=r.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='synthetic.public-media' AND e.source_reference=?",(source.source_id,)).fetchone()[0]
        restored=PerceptionService(r.store,providers(),policy(),decoder=NoRepeatedDecode())
        mid,rid=restored.ingest(data,source,entity_id='observer',scope='world')
        assert mid==raw and RecordService(r.store).current_support(rid)
        assert r.store.db.execute("SELECT count(*) FROM continuity_evidence WHERE source_namespace='synthetic.public-media' AND source_reference=?",(source.source_id,)).fetchone()[0]==1


def test_private_pcm_reuse_keeps_privacy_and_does_not_reclassify_from_a_descriptor(tmp_path):
    from nana_core.continuity.providers import ProviderRegistry,ProviderDescriptor
    from nana_core.continuity.world_loop.perception import MediaSourceDescriptor,DecodedMediaProcessor
    with fresh(tmp_path/'s'/'self.db') as r:
        data=media_samples()['AUDIO'];now=r.clock.utc_now_us()
        source=MediaSourceDescriptor(source_id='private-pcm',modality='AUDIO',origin='SYNTHETIC',
            event_time_us=now,observed_time_us=now,privacy='PERSONAL',source_profile_id='synthetic-private',
            source_revision=1,source_kind='SYNTHETIC_PCM',capture_id='owned-private-capture',
            adapter_identity='synthetic-generator',byte_length=len(data),capture_coverage='FULL_BOUNDED_PCM',sequence=0)
        registry=ProviderRegistry();registry.register(ProviderDescriptor(provider_id='private.codec',model_id='local.codec-v1',
            model_version='1',operations=('AUDIO_UNDERSTAND',),input_modalities=('AUDIO',),output_modalities=('TEXT',),
            context_limit=65536,output_limit=16384,locality='LOCAL',permitted_privacy=('PUBLIC','PERSONAL')),DecodedMediaProcessor())
        ids=PerceptionService(r.store,registry,policy()).ingest(data,source,entity_id='observer',scope='world')
        saved=PerceptionService(r.store,registry,policy(),decoder=NoRepeatedDecode())
        assert saved.ingest(data,source,entity_id='observer',scope='world')==ids
        assert MemoryService(r.store).read(ids[0])['privacy_class']=='PERSONAL'
        public=PerceptionService(r.store,registry,policy().model_copy(update={'readable_privacy':('PUBLIC',)}),decoder=NoRepeatedDecode())
        with pytest.raises(CoreError,match='PERCEPTION_INGRESS_DENIED'):
            public.ingest(data,source,entity_id='observer',scope='world')
        with pytest.raises(CoreError,match='SOURCE_KEY_COLLISION'):
            public.ingest(data,source.model_copy(update={'privacy':'PUBLIC'}),entity_id='observer',scope='world')
