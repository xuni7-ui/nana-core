import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.provider import provider_command,provider_status
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.provider_config import ProviderConfigService,ProviderConfigurationAuthority
from nana_core.continuity.records import RecordService
from .test_work import initialize,advance
from tests.independent_life.test_dialogue import relay


def test_board_erasure_source_and_skill_support_close_together(tmp_path):
    home=tmp_path/'life';initialize(home)
    with LifeApplication(home,clock=VirtualClock(),bootstrap_grant=True) as app:
        advance(app,240);board=app.board()
        assert len(board['materials'])==4 and len(board['learning'])==2 and len(board['skills'])==1
        assert len(board['shared_context'])==2
        rid=app.work.port.skill_bindings['MD_OUTLINE_2']
        root=RecordService(app.runtime.store).support(rid)[0]
        app.forget(root)
        with pytest.raises(CoreError):app.work.port.code_skills.require_current(rid)
        assert not app.board()['skills']
        assert len(app.board()['learning'])<2
        assert not app.runtime.store.db.execute('pragma foreign_key_check').fetchall()


def test_volatile_multi_turn_uses_same_context_and_disappears_on_delete(tmp_path):
    home=tmp_path/'life';initialize(home,skills=False)
    with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();first=app.chat('V2_TRANSIENT_TURN_1',topic='casual')
        app.chat('V2_TRANSIENT_TURN_2',topic='casual')
        history=requests[-1]['role_input']['dialogue']['recent_turns']
        assert history[0]['text']=='V2_TRANSIENT_TURN_1'
        app.chat('lower privacy',topic='casual',privacy='PROJECT')
        assert not requests[-1]['role_input']['dialogue']['recent_turns']
        app.forget(first['message_memory_id']);app.chat('after delete',topic='casual')
        assert all(t['text']!='V2_TRANSIENT_TURN_1' for t in requests[-1]['role_input']['dialogue']['recent_turns'])
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'V2_TRANSIENT_TURN')>0").fetchone()


def test_provider_tool_is_offline_cas_no_authorization_no_secret_projection(tmp_path):
    home=tmp_path/'life';initialize(home,skills=False)
    authority=ProviderConfigurationAuthority();ProviderConfigService(home/'providers.json',authority).initialize(authority)
    path=tmp_path/'command.json'
    p={'provider_profile_id':'test.provider','display_name':'operator configured','protocol':'OPENAI_COMPATIBLE_CHAT','locality':'REMOTE','base_url':'https://provider.example/v1','secret_ref':'operator.ref'}
    path.write_text(json.dumps({'operation':'UPSERT_PROVIDER','expected_revision':0,'provider':p}))
    assert provider_command(home,path)['network_calls']==0
    assert 'operator.ref' not in json.dumps(provider_status(home))
    with pytest.raises(CoreError,match='REVISION_CONFLICT'):provider_command(home,path)
    with LifeApplication(home,clock=VirtualClock()) as app:
        assert not app.runtime.store.all('grants')
        assert app.chat('offline')['provider_state']=='LIVE_PROVIDER_NOT_RUN_OFFLINE_MODE'
        assert app.status()['view']['resources']['calls']==0


def test_missing_grant_and_pause_do_not_become_motivation_erasure(tmp_path):
    home=tmp_path/'life';initialize(home,skills=False)
    with LifeApplication(home,clock=VirtualClock()) as app:
        advance(app,60)
        assert any(g['state']=='BLOCKED' for g in app.runtime.store.all('goals'))
        assert not list((home/'reports').glob('*.md'))
        assert app.runtime.store.db.execute("SELECT 1 FROM actions WHERE state='BLOCKED'").fetchone()
        before=app.runtime.store.all('jobs');app.pause();advance(app,10)
        assert before==app.runtime.store.all('jobs')
        assert app.runtime.store.db.execute("SELECT 1 FROM subject_cycles").fetchone()
