"""Verified G outcomes may refer to the same own thought after a C revision."""
import json,time
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import uid
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.autonomy.private_intent import candidates,growth_origin_target,review_target
from nana_core.continuity.subject.opportunities import PrivateIntentRef
from .conftest import initialize
from .test_private_tendency import form


def prepare(home):
    initialize(home)
    app=LifeApplication(home,clock=VirtualClock());app.pause()
    form(app,'origin','SYNTHETIC an own question before optional learning.',topic='same-interest',kind='private_question')
    rid,item=candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL'))[0]
    ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision)
    form(app,'revision','SYNTHETIC a refined own question while learning.',topic=item.topic,revision=rid,kind='private_question')
    current=next((r,v) for r,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.intent_id==item.intent_id)
    return app,ref,item,current


@pytest.mark.parametrize('legacy',[False,True])
def test_exact_own_intent_filter_precedes_64_candidate_cap_and_is_read_only(tmp_path,legacy):
    app,ref,origin,current=prepare(tmp_path/'home')
    with app:
        store=app.runtime.store;records=app.runtime.subject.records
        # Synthetic unrelated current headers on the same indexed owner/topic;
        # no extra decisions/models are needed to exercise lookup crowding.
        for i in range(70):
            payload=current[1].model_copy(update={'intent_id':uid(),'content_summary':'SYNTHETIC distractor '+str(i)})
            with store.transaction('SYNTHETIC_LOOKUP_DISTRACTOR',{'index':i}) as tx:
                records.create(tx,kind='INTENTION',scope='project-work',target_id='private-intent.v1',payload=payload.model_dump(mode='json'),memories=origin.source_memory_ids)
        assert all(v.intent_id!=ref.intent_id for _,v in candidates(store,'project-work',('PROJECT','PERSONAL'),topic=origin.topic,owner_identity_id=origin.owner_identity_id))
        if legacy:
            for name in ('private_intent_topic_lookup_v1','private_intent_payload_lookup','private_intent_tendency_topic_v4'):store.db.execute('DROP INDEX '+name)
        before=store.snapshot();writes=store.db.total_changes;started=time.perf_counter()
        found=growth_origin_target(store,ref,scope='project-work',privacy_classes=('PROJECT','PERSONAL'),topic=origin.topic)
        elapsed=time.perf_counter()-started
        assert found==current
        assert store.snapshot()==before and store.db.total_changes==writes
        with pytest.raises(CoreError,match='REVIEW_UNAVAILABLE'):review_target(store,ref,scope='project-work',privacy_classes=('PROJECT','PERSONAL'))
        print(json.dumps({'measurement':'synthetic_current_growth_origin_lookup','legacy_without_topic_indexes':legacy,'unrelated_current_same_topic':70,'elapsed_seconds':elapsed,'writes':store.db.total_changes-writes}))


@pytest.mark.parametrize('condition',['wrong-scope','too-private','wrong-revision','wrong-intent','wrong-owner','withdrawn','abandoned','ambiguous','wrong-lineage','same-revision'])
def test_current_growth_association_cannot_guess_across_invalid_origin_or_current_state(tmp_path,condition):
    app,ref,origin,current=prepare(tmp_path/'home')
    with app:
        store=app.runtime.store;records=app.runtime.subject.records
        scope='other' if condition=='wrong-scope' else 'project-work'
        privacy=('PUBLIC',) if condition=='too-private' else ('PROJECT','PERSONAL')
        if condition=='wrong-revision':ref=ref.model_copy(update={'revision':ref.revision+1})
        if condition=='wrong-intent':ref=ref.model_copy(update={'intent_id':uid()})
        if condition=='withdrawn':app.forget(origin.source_memory_ids[0])
        if condition in {'wrong-owner','abandoned','ambiguous','wrong-lineage','same-revision'}:
            payload=current[1].model_copy(update={'owner_identity_id':uid()} if condition=='wrong-owner' else {'activity_state':'ABANDONED'} if condition=='abandoned' else {'cycle_id':uid()} if condition=='wrong-lineage' else {'revision':origin.revision} if condition=='same-revision' else {})
            with store.transaction('SYNTHETIC_INVALID_CURRENT_VARIANT',{'case':condition}) as tx:
                alternate=records.create(tx,kind='INTENTION',scope='project-work',target_id='private-intent.v1',payload=payload.model_dump(mode='json'),memories=origin.source_memory_ids,supersedes=current[0] if condition!='ambiguous' else None)
                if condition=='wrong-owner':ref=ref.model_copy(update={'record_id':alternate,'revision':current[1].revision})
        assert growth_origin_target(store,ref,scope=scope,privacy_classes=privacy,topic=origin.topic) is None
