"""Opted-in speech survives a cut at the original volatile-history boundary."""
import json
import pytest

from nana_core.continuity.records import RecordService
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from .conftest import initialize


class CompactionInterrupted(Exception):
    pass


class CutAtCompaction(list):
    def __iter__(self):
        # Normal INTERPRET/RENDER read history in reverse. This cut is precisely
        # the forward pass that rewrites excerpts after the generated candidate.
        raise CompactionInterrupted('synthetic cut before volatile excerpts')


@pytest.mark.parametrize('retain', [True, False])
def test_opted_in_exchange_commits_before_volatile_compaction_and_recovers_without_replay(tmp_path, retain):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    user='SYNTHETIC_IMPORTANT_INPUT '+('detail ' * 180)
    utterance='SYNTHETIC_GENERATED_NOT_DELIVERED '+('candidate ' * 180)
    with relay(home,'CHAT',renderer=lambda request:utterance) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            app._recent=CutAtCompaction()
            with pytest.raises(CompactionInterrupted):
                app.chat(user,topic='durability',privacy='PROJECT',message_id='cut',retain_shared_life=retain)
            assert len(requests)==2  # Existing INTERPRET and SOCIAL, no retry.
            record_ids=[r['record_id'] for r in app.runtime.store.db.execute(
                "SELECT record_id FROM continuity_records WHERE record_kind='RELATIONSHIP_EVENT' AND target_id='durability'")]
            assert len(record_ids)==int(retain)
            if retain:
                record=RecordService(app.runtime.store).read(record_ids[0])
                payload=record['payload']
                assert payload['person_kind']=='CONVERSATION_EXCHANGE'
                assert payload['user_statement']==user
                assert payload['assistant_utterance']==utterance
                assert payload['epistemic_status']=='REPORTED_SPEECH_NOT_WORLD_TRUTH'
                mid=payload['user_memory_id']
            else:
                assert not app.runtime.store.db.execute(
                    "SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0 OR instr(CAST(payload AS TEXT),?)>0",
                    ('SYNTHETIC_IMPORTANT_INPUT','SYNTHETIC_GENERATED_NOT_DELIVERED')).fetchone()
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity and app._recent==[]
            assert app.chat(user,topic='durability',privacy='PROJECT',message_id='cut',retain_shared_life=retain)[
                'state']=='ALREADY_REVIEWED_NO_REPLAY'
            assert len(requests)==2
            result=app.chat('SYNTHETIC continue',topic='durability',privacy='PROJECT',message_id='next')
            assert result['render_state']=='UNVERIFIED_MODEL_WORDING'
            context=requests[-1]['context_json']
            assert ('SYNTHETIC_IMPORTANT_INPUT' in context)==retain
            assert ('SYNTHETIC_GENERATED_NOT_DELIVERED' in context)==retain
            if retain:
                # Durable records keep full wording; prompts deliberately use
                # bounded, source-identified excerpts, never the whole history.
                recovered=RecordService(app.runtime.store).read(record_ids[0])['payload']
                assert recovered['user_statement']==user and recovered['assistant_utterance']==utterance
                person=next(json.loads(b['data_json']) for b in json.loads(context)['blocks'] if b['kind']=='PERSON_SELF')
                excerpt=next(e for e in person['recent_exchanges'] if e['user_memory_id']==mid)
                for field,original in [('user_statement',user),('assistant_utterance',utterance)]:
                    assert excerpt[field]==original[:384]
                    assert excerpt['excerpt_ranges'][field]=={'start':0,'end':384,'full_characters':len(original)}
                assert user not in context and utterance not in context
            assert len(app._recent)<=6
            if retain:
                app.forget(mid)
                app.chat('SYNTHETIC after withdrawal',topic='durability',privacy='PROJECT',message_id='withdrawn')
                assert 'SYNTHETIC_IMPORTANT_INPUT' not in requests[-1]['context_json']
                assert 'SYNTHETIC_GENERATED_NOT_DELIVERED' not in requests[-1]['context_json']
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
            print(json.dumps({'retained':retain,'same_subject_after_restart':True,
                'duplicate_calls':0,'recovery_calls':len(requests)-2,'real_provider_calls':0,
                'request_json_bytes':[len(json.dumps(q).encode()) for q in requests],
                'budgets':[q['budget'] for q in requests]}))
