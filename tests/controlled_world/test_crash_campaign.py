import json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest
from nana_core.continuity.controlled_world.lab import ControlledWorld
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.life.application import LifeApplication
from nana_core.life.config import update_config
from controlled_hands.conftest import initialize

CUTS=('IDLE','IDLE_TERM','IDLE_GRACEFUL','RESEARCH','BEFORE_ACTION','AFTER_ACTION_BEFORE_VERIFY','DURING_VERIFY','AFTER_EXPERIENCE','LEARNING','SKILL_QUALIFICATION','AFTER_DELIVERY_CANDIDATE','BACKUP')
@pytest.mark.parametrize('cut',CUTS)
def test_actual_process_cut_same_subject_no_duplicate_effect_or_authority(owned_root,cut):
    with ControlledWorld(owned_root/'world',interval=120) as world:
        home=owned_root/'life';cfg=initialize(home,world.host.profile,skills=True)
        update_config(home,cfg.model_copy(update={'revision':2,'advanced_life':True,'shared_presence':True,'owned_browser_endpoint':world.browser.endpoint,'world_sources':tuple(IntakeSource(source_id=k,channel='OWNED_HTTP',location=world.services[k].url+'/source',semantic_format='SOURCED_CLAIM_JSON') for k in ('feed','api'))}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:identity=app.runtime.identity_id;grants=len(app.runtime.store.all('grants'))
        marker=owned_root/'cut.json'
        with (owned_root/'worker.log').open('w') as log:
            process=subprocess.Popen([sys.executable,'-m','tools.nana_controlled_world.crash_worker','--home',str(home),'--marker',str(marker),'--cut',cut],stdout=log,stderr=log)
            try:
                deadline=time.monotonic()+65
                while not marker.exists():
                    assert process.poll() is None,(cut,(owned_root/'worker.log').read_text()[-2000:])
                    assert time.monotonic()<deadline,(cut,'exact committed cut missing')
                    time.sleep(.02)
                if cut=='IDLE_GRACEFUL':process.wait(4);assert process.returncode==0
                elif cut=='IDLE_TERM':process.terminate();process.wait(4);assert process.returncode==0
                else:process.kill();process.wait(4);assert process.returncode==-signal.SIGKILL
            finally:
                if process.poll() is None:process.kill();process.wait(4)
        assert json.loads(marker.read_text())['identity_id']==identity
        before=json.loads((Path(world.host.target.workspace)/'application-state.json').read_text())['effects']
        with LifeApplication(home) as app:
            r=app.runtime;assert r.identity_id==identity and len(r.store.all('grants'))==grants
            # Recovery uses original Kernel independent Verify, never a fresh
            # dispatch of the old effect. New ordinary future work is allowed.
            kernel=r.work.agency.realization.kernel;kernel.recover()
            after=json.loads((Path(world.host.target.workspace)/'application-state.json').read_text())['effects'];assert before==after
            for _ in range(3):app.tick()
            effects=json.loads((Path(world.host.target.workspace)/'application-state.json').read_text())['effects']
            keys=[v['idempotency_key'] for v in effects.values()];assert len(keys)==len(set(keys))
            assert all(effects[k]==v for k,v in before.items())
            assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
            assert len(r.store.all('grants'))==grants
