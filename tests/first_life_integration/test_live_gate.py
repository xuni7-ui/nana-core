"""No API/key/network; validate new explicit authorization's budget envelope."""
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config
from nana_core.continuity.provider_config import ResolvedSecret
from tools.nana_first_life_integration.dev import initialize,preflight
from tools.nana_first_life_integration.journey import setup
from tools.nana_first_life_integration.live_review import configure,REF


def test_eight_call_envelope_requires_known_fixture_baseline_no_dispatch(tmp_path):
    home=tmp_path/'life';initialize(home)
    with pytest.raises(CoreError,match='BUDGET_BASE_MISMATCH'):configure(home)
    with LifeApplication(home) as app:
        outcome=setup(app,tmp_path)
        assert outcome['semantic']['fixture_calls']==1
    cfg=configure(home)
    assert cfg.provider_total_calls_limit==9 and cfg.provider_total_reserved_cost_micro==400000
    assert cfg.provider_timeout_ms==15000 and cfg.remote_privacy==('PUBLIC','PROJECT')
    class ExplicitSyntheticResolver:
        def available(self,reference):return reference==REF
        def resolve(self,reference):return ResolvedSecret('TEST_ONLY_NOT_SECRET')
    assert preflight(home,live=True,resolver=ExplicitSyntheticResolver())['state']=='PREFLIGHT_PASS'
    assert preflight(home,live=True)['state']=='FIRST_LIFE_START_BLOCKED'
    before=load_config(home)
    with pytest.raises(CoreError,match='NO_OVERWRITE'):configure(home)
    assert load_config(home)==before


@pytest.mark.parametrize('mode',['ok','malformed'])
def test_live_source_function_loopback_proves_chain_and_no_retry_without_live_claim(tmp_path,mode):
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.life.config import update_config
    from tools.nana_first_life_integration.live_review import semantic
    home=tmp_path/'life';initialize(home)
    cfg=load_config(home);update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'provider_cost_ceiling_micro':50000}),expected_revision=cfg.revision)
    with provider_harness(mode=mode) as (transport,metrics),LifeApplication(home) as app:
        session=CognitionSession(app.runtime,transport,app.policy)
        app._session=lambda privacy:session
        result=semantic(app)
        assert metrics['calls']==1 and result['execution']=='SYNTHETIC_LOOPBACK'
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert result.get('qualification')!='LIVE_CURRENT_SUBJECT_SEMANTIC_INTEGRATION_PASS'
        if mode=='ok':
            assert result['qualification']=='SYNTHETIC_SEMANTIC_INTEGRATION_PASS'
            assert result['world_conflict']=='CONFLICT' and result['world_corrected']=='SUPPORTED_BELIEF'
            assert result['world_withdrawn']=='UNKNOWN' and result['after_choice']=='NO_ACTION'
        else:assert result['state']!='PROPOSED'


def test_private_terminal_binding_never_echoes_synthetic_credential():
    import os,pty,select,subprocess,sys,time
    master,slave=pty.openpty()
    code="from tools.nana_first_life_integration.live_review import secret_from_terminal,REF; r=secret_from_terminal(); print('BOUND',r.available(REF),repr(r),flush=True); r.clear(); print('CLEARED',r.available(REF),flush=True)"
    child=subprocess.Popen([sys.executable,'-c',code],stdin=slave,stdout=slave,stderr=slave,close_fds=True);os.close(slave)
    received=b'';deadline=time.monotonic()+5
    try:
        while b'CREDENTIAL_INPUT_READY_ECHO_DISABLED' not in received:
            assert time.monotonic()<deadline and child.poll() is None
            if select.select([master],[],[],.1)[0]:received+=os.read(master,4096)
        os.write(master,b'TEST_ONLY_NOT_SECRET_TERMINAL_CANARY\n')
        while child.poll() is None:
            assert time.monotonic()<deadline
            if select.select([master],[],[],.1)[0]:
                try:received+=os.read(master,4096)
                except OSError:break
        child.wait(timeout=2)
        assert child.returncode==0 and b'TEST_ONLY_NOT_SECRET_TERMINAL_CANARY' not in received
        assert b'BOUND True' in received and b'CLEARED False' in received
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=2)
        os.close(master)


def test_source_pinning_excludes_unrelated_dispute_without_bypassing_required_dispute(tmp_path):
    from nana_core.continuity.project_work.service import capture
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.world_loop.cognition import CognitionSession
    home=tmp_path/'life';initialize(home)
    with provider_harness() as (transport,metrics),LifeApplication(home) as app:
        r=app.runtime
        a=capture(r,'unrelated.a',{'claim':'A'},predicate='unrelated.claim')
        b=capture(r,'unrelated.b',{'claim':'B'},predicate='unrelated.claim')
        assert r.store.one('memories',a)['assessment']=='DISPUTED'
        mid=capture(r,'focused.note',{'resource_state':'Project note to inspect'})
        session=CognitionSession(r,transport,app.policy)
        with pytest.raises(CoreError,match='MEMORY_NOT_CURRENT'):
            session.prepare('ambient-conflict','INTERPRET',(mid,))
        request=session.prepare('focused','INTERPRET',(mid,),pinned_only=True)
        saved=session.records.read(r.store.one('cognitive_requests',request)['record_id'])['payload']['request']
        assert a not in saved['source_context_refs'] and b not in saved['source_context_refs']
        assert session.execute(request)['state']=='PROPOSED' and metrics['calls']==1
        with pytest.raises(CoreError,match='MEMORY_NOT_CURRENT'):
            session.prepare('conflict-is-required','INTERPRET',(a,),pinned_only=True)
        app.forget(mid)
        assert session.execute(request)['replayed'] and metrics['calls']==1


def test_exact_secret_audit_blocks_leak_and_writes_only_sanitized_summary(tmp_path):
    import json
    from uuid import uuid4
    from tools.nana_first_life_integration.live_review import scan_and_save
    marker='TEST_ONLY_NOT_SECRET_'+uuid4().hex
    class ExplicitTestResolver:
        def resolve(self,ref):return ResolvedSecret(marker)
    home=tmp_path/'home';home.mkdir(mode=0o700)
    leak=home/'synthetic.json';leak.write_text(json.dumps({'test_value':marker}))
    output=tmp_path/'result.json'
    with pytest.raises(CoreError,match='SECRET_LEAK_BLOCK'):
        scan_and_save(home,output,{'provider_calls':0},ExplicitTestResolver())
    assert not output.exists()
    leak.write_text('{}')
    scan_and_save(home,output,{'provider_calls':0},ExplicitTestResolver())
    result=json.loads(output.read_text())
    assert result['secret_audit']['exact_matches']==0 and not result['secret_audit']['persisted']
    assert marker not in output.read_text() and output.stat().st_mode&0o077==0
