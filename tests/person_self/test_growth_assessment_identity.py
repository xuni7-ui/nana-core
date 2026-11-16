"""Original G replay keys bind to a current in-scope episode, not just a label."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.presence.authority import VirtualClock
from .test_growth_inner_choice import grown


@pytest.mark.parametrize('condition',['same','changed','scope','withdrawn','privacy'])
def test_episode_replay_cannot_relabel_old_success_or_cross_its_source_scope(tmp_path,condition,monkeypatch):
    with grown(tmp_path/'life',VirtualClock()) as (r,view,origin,reuse,lesson):
        records=RecordService(r.store);memory=MemoryService(r.store)
        original=records.read(r.store.one('strategy_assessments',view.assessment_id)['record_id'])['payload']['episode']
        review=EpisodeLearning(r.store,r.authority,scopes=('world','other-scope'),privacy_classes=('PUBLIC',))
        def source(key,episode,scope='world',privacy='PUBLIC'):
            text=json.dumps({'strategy_episode':episode})
            eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.episode-replay-binding',
                source_reference=key,source_kind='SYSTEM_VERIFICATION'),text=text,privacy_class=privacy,observed_time_us=r.clock.utc_now_us()))
            return memory.add(MemoryCandidate(entity_id=r.config.entity_id,scope=scope,memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text))
        if condition=='same':
            changes=r.store.db.total_changes
            assert review.assess(lesson,reuse,authority=r.authority)==view.assessment_id
            assert r.store.db.total_changes==changes
        else:
            if condition=='changed':
                # A real deterministic precision counterexample, explicitly a
                # synthetic evaluation case, without the old Kernel action ID.
                bad=LearningCase(case_id='different-precision-case',context='different-precision-context',data=[.1,.2],expected=.3)
                episode={'episode_key':original['episode_key'],'lesson_id':lesson,'case':bad.model_dump(mode='json')}
                other=source('changed',episode)
                expected='STRATEGY_EPISODE_KEY_COLLISION'
            elif condition=='scope':
                episode=original;other=source('other-scope',episode,'other-scope')
                expected='STRATEGY_SOURCE_RETIRED'
            elif condition=='privacy':
                episode={**original,'episode_key':'private-checked-use'}
                personal=source('private-original',episode,privacy='PERSONAL')
                private_review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC','PERSONAL'))
                aid=private_review.assess(lesson,personal,authority=r.authority)
                private_head=r.store.one('continuity_records',r.store.one('strategy_assessments',aid)['record_id'])
                assert private_head['privacy_class']=='PERSONAL'
                other=source('public-replacement',episode)
                artifact=r.store.artifact
                def guarded(artifact_id,*args,**kwargs):
                    assert artifact_id!=private_head['payload_artifact_id'], 'private cached result must be rejected before payload read'
                    return artifact(artifact_id,*args,**kwargs)
                monkeypatch.setattr(r.store,'artifact',guarded)
                expected='STRATEGY_SOURCE_RETIRED'
            else:
                other=source('replacement-after-withdrawal',original)
                MemoryService(r.store,r.authority).forget(reuse,r.authority)
                expected='STRATEGY_SOURCE_RETIRED'
            changes=r.store.db.total_changes;count=len(r.store.all('strategy_assessments'))
            with pytest.raises(CoreError,match=expected):review.assess(lesson,other,authority=r.authority)
            assert r.store.db.total_changes==changes and len(r.store.all('strategy_assessments'))==count
            assert r.store.one('lessons',lesson)['state']=='ACTIVE'
            assert r.store.one('strategy_assessments',view.assessment_id)['verdict']=='SUCCESS'
            if condition=='changed':
                # New independent occurrence receives its own stable key and
                # follows the original evaluator's counterexample fence.
                fresh=source('new-occurrence',{**episode,'episode_key':'different-precision-case'})
                aid=review.assess(lesson,fresh,authority=r.authority)
                assert aid!=view.assessment_id and r.store.one('strategy_assessments',aid)['verdict']=='COUNTEREXAMPLE'
                assert r.store.one('lessons',lesson)['state']=='SUSPENDED'
                changes=r.store.db.total_changes
                assert review.assess(lesson,fresh,authority=r.authority)==aid
                assert r.store.db.total_changes==changes
