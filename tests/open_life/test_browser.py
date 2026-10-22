import json,os,subprocess,sys
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
