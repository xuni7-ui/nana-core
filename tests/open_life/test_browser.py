import json,os,subprocess,sys
from pathlib import Path
from contextlib import contextmanager
import pytest
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.continuity.hands.browser import BrowserEndpoint
from nana_core.life.application import LifeApplication
from nana_core.life.config import update_config
from controlled_hands.conftest import initialize,until
from nana_core.contracts import CoreError

@contextmanager
def browser(host):
    process=subprocess.Popen([sys.executable,'-m','nana_core.continuity.hands.browser','--profile',str(host.profile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':os.defpath,'PYTHONPATH':os.path.abspath('src')})
    try:
        line=process.stdout.readline()
        assert line,process.stderr.read().decode()[:200]
        yield BrowserEndpoint.model_validate_json(line)
    finally:
        process.terminate();process.wait(timeout=5)


def test_owned_browser_form_kernel_verify_and_no_grant(tmp_path):
    tasks=(ApplicationTask(task_id='form',kind='FORM',wanted={'label':'blue'},fields=('label',)),)
    with OwnedApplication(tmp_path/'owned',tasks=tasks) as host,browser(host) as endpoint:
        home=tmp_path/'life';cfg=initialize(home,host.profile,skills=False)
        update_config(home,cfg.model_copy(update={'revision':2,'owned_browser_endpoint':endpoint}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            assert '/tasks/form' in app.work.port.open()
            assert 'name="label"' in app.work.port.navigate('form')
            with pytest.raises(CoreError):app.work.port.navigate('../outside')
            until(app,lambda:app.work.goal_for('form') and app.work.goal_for('form')['state']=='COMPLETED')
            state=app.work.port.peek('form')['state']
            assert state['submitted'] and state['values']=={'label':'blue'}
            effects=[a for a in app.runtime.store.all('actions') if a['capability']=='world.publish']
            assert len(effects)==1 and effects[0]['state']=='SUCCEEDED'
            assert app.runtime.store.all('experiences')[0]['outcome']=='SUCCESS'
            assert not app.runtime.store.db.execute('PRAGMA foreign_key_check').fetchall()
        # Restart does not resubmit the form and old history is preserved.
        with LifeApplication(home) as reopened:
            before=len(reopened.runtime.store.all('actions'))
            for _ in range(4):reopened.tick()
            assert len(reopened.runtime.store.all('actions'))==before


def test_http_effect_ack_loss_unknown_reconciles_without_resend(tmp_path,monkeypatch):
    from nana_core.contracts import Verification
    tasks=(ApplicationTask(task_id='form',kind='FORM',wanted={'label':'blue'},fields=('label',)),)
    with OwnedApplication(tmp_path/'owned',tasks=tasks) as host,browser(host) as endpoint:
        home=tmp_path/'life';cfg=initialize(home,host.profile,skills=False)
        update_config(home,cfg.model_copy(update={'revision':2,'owned_browser_endpoint':endpoint}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            port=app.work.port;original=port._http;original_verify=port.verify;calls=[]
            def lost_ack(path,body=None):
                raw=original(path,body)
                if path=='/api/control':calls.append(path);raise CoreError('BROWSER_COMPLETION_UNKNOWN')
                return raw
            monkeypatch.setattr(port,'_http',lost_ack)
            monkeypatch.setattr(port,'verify',lambda invocation:Verification(verdict='INCONCLUSIVE',evidence={'reason':'VERIFIER_TEMPORARILY_UNAVAILABLE'}) if invocation.capability=='world.publish' else original_verify(invocation))
            until(app,lambda:bool(app.runtime.store.db.execute("SELECT 1 FROM actions WHERE capability='world.publish' AND state='UNKNOWN'").fetchone()))
            assert calls==['/api/control'] and port.peek('form')['state']['submitted']
        with LifeApplication(home) as reopened:
            k=reopened.runtime.work.agency.realization.kernel;k.recover()
            actions=reopened.runtime.store.db.execute("SELECT * FROM actions WHERE capability='world.publish'").fetchall()
            assert len(actions)==1 and actions[0]['state']=='SUCCEEDED'
            state=json.loads((Path(host.target.workspace)/'application-state.json').read_text())
            assert len(state['effects'])==1
            assert calls==['/api/control']
