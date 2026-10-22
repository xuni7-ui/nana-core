import os,signal,subprocess,sys
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.person_self import adopted
from nana_core.continuity.lived_language import expression_policy
from .conftest import initialize,REPO
from .test_continuity import propose


def test_actual_sigkill_after_committed_adoption_and_learning_no_replay(tmp_path):
    home=tmp_path/'home';initialize(home)
    script='''
import sys,os,signal
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.person_self.test_continuity import propose
from tests.person_self.test_learning import record,activate
with LifeApplication(Path(sys.argv[1]),clock=VirtualClock()) as app:
 app.pause();propose(app);record(app,1);_,eid=record(app,2);activate(app,eid)
 os.kill(os.getpid(),signal.SIGKILL)
'''
    result=subprocess.run([sys.executable,'-c',script,str(home)],cwd=REPO,capture_output=True,timeout=20)
    assert result.returncode==-signal.SIGKILL,result.stderr.decode()[-500:]
    with LifeApplication(home,clock=VirtualClock()) as app:
        assert adopted(app.runtime.store,'project-work','project-user',('PROJECT',))
        assert expression_policy(app.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule']
        c,_,_=propose(app)
        assert c.replayed
        assert len(app.runtime.store.all('experiences'))==2
        assert not app.runtime.store.all('actions')
        assert not app.runtime.store.db.execute('PRAGMA foreign_key_check').fetchall()
