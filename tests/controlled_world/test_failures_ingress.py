import json,threading
from pathlib import Path
import pytest
from nana_core.continuity.controlled_world.lab import LabService
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.browser import OwnedBrowser
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from nana_core.life.config import update_config
from nana_core.life.surfaces import SurfaceBinding,SurfaceObservation
from nana_core.continuity.open_life.sources import WorldIntake,IntakeSource
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.presence.authority import VirtualClock
from nana_core.contracts import CoreError
from controlled_hands.conftest import initialize,until


def test_real_http_drop_plus_verifier_socket_unavailable_unknown_no_resend(owned_root,monkeypatch):
    tasks=(ApplicationTask(task_id='form',kind='FORM',wanted={'label':'blue'},fields=('label',)),)
    with OwnedApplication(owned_root/'app',tasks=tasks) as host,OwnedBrowser(host.profile,drop_ack_tasks=('form',)) as browser:
        home=owned_root/'life';cfg=initialize(home,host.profile,skills=False);update_config(home,cfg.model_copy(update={'revision':2,'owned_browser_endpoint':browser.endpoint}),expected_revision=1)
        query=Path(host.target.workspace)/'query.sock';parked=query.with_name('query.parked');posts=[]
        with LifeApplication(home,bootstrap_grant=True) as app:
            original=app.work.port._http
            def fault(path,body=None):
                try:return original(path,body)
                except CoreError:
                    if path=='/api/control':
                        posts.append(path)
                        assert len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])==1
                        query.rename(parked) # real independent verifier channel unavailable
                    raise
            monkeypatch.setattr(app.work.port,'_http',fault)
            try:
                until(app,lambda:bool(app.runtime.store.db.execute("SELECT 1 FROM actions WHERE capability='world.publish' AND state='UNKNOWN'").fetchone()))
                action=app.runtime.store.db.execute("SELECT * FROM actions WHERE capability='world.publish'").fetchone();aid=action['action_id'];identity=app.runtime.identity_id
                assert action['state']=='UNKNOWN' and posts==['/api/control']
            finally:parked.rename(query)
        with LifeApplication(home) as app:
            assert app.runtime.identity_id==identity
            k=app.runtime.work.agency.realization.kernel;k.recover()
            assert app.runtime.store.one('actions',aid)['state']=='SUCCEEDED'
            assert len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])==1 and posts==['/api/control']


def test_second_real_unknown_intake_timeout_and_restart_no_retry(owned_root):
    with LabService(owned_root/'api','api') as api:
        clock=VirtualClock();source=IntakeSource(source_id='slow',channel='OWNED_HTTP',location=api.url+'/fault/delay',privacy='PUBLIC')
        path=owned_root/'self.db'
        with open_runtime(path,clock) as r:
            intake=WorldIntake(r,owned_root,(source,),scope='world')
            with pytest.raises(CoreError,match='UNKNOWN'):intake.read('slow')
            assert r.store.db.execute("SELECT state FROM jobs WHERE work_kind='WORLD_INTAKE'").fetchone()[0]=='UNKNOWN'
        with open_runtime(path,clock) as r:
            with pytest.raises(CoreError,match='UNKNOWN_NO_RETRY'):WorldIntake(r,owned_root,(source,),scope='world').read('slow',observation_id='later-poll')
            state=json.loads((api.root/'environment.json').read_text());assert state['requests']==1
            assert not r.store.all('actions')


def test_concurrent_three_surfaces_owner_order_dedup_l1_and_preemption(owned_root):
    tasks=(ApplicationTask(task_id='form',kind='FORM',wanted={'label':'blue'},fields=('label',)),)
    with OwnedApplication(owned_root/'app',tasks=tasks) as host:
        home=owned_root/'life';cfg=initialize(home,host.profile,skills=False)
        bindings=tuple(SurfaceBinding(binding_id='surface.'+n,platform='platform.local',surface='surface.'+n,adapter='adapter.owned') for n in ('cli','web','social'))
        update_config(home,cfg.model_copy(update={'revision':2,'surface_bindings':bindings}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            identity=app.runtime.identity_id
            background=SurfaceObservation(binding_id='surface.social',event_id='background',topic='shared-project',text='Project status has changed',approved_summary='Synthetic owned maintenance project is ongoing.',summary_authorization='EXPLICIT_PROJECT_SUMMARY')
            app.ingress.offer(background,urgency='BACKGROUND')
            observations=[SurfaceObservation(binding_id='surface.'+n,event_id=n,topic='shared-project',text='现在项目进展怎样？') for n in ('cli','web')]
            threads=[threading.Thread(target=app.ingress.offer,args=(o,)) for o in observations]
            for t in threads:t.start()
            for t in threads:t.join()
            assert app.ingress.offer(observations[0])['state']=='ALREADY_QUEUED'
            with pytest.raises(CoreError,match='COLLISION'):app.ingress.offer(observations[0].model_copy(update={'text':'different'}))
            results=[app.tick()['surface_ingress'] for _ in range(3)]
            assert {x['binding_id'] for x in results[:2]}=={'surface.cli','surface.web'}
            assert results[-1]['binding_id']=='surface.social'
            assert not app.runtime.store.all('actions') # user priority before autonomous Hand
            assert app.ingress.pending()==0 and app.runtime.identity_id==identity
            before=len(app.runtime.store.all('subject_cycles'));app.ingress.offer(observations[0]);app.tick()
            assert len(app.runtime.store.all('subject_cycles'))==before
            from nana_core.life.surfaces import recent_sources
            assert recent_sources(app,'shared-project','PROJECT')


def test_user_input_during_actual_effect_waits_for_safe_point_then_preempts(owned_root,monkeypatch):
    tasks=(ApplicationTask(task_id='form',kind='FORM',wanted={'label':'blue'},fields=('label',)),)
    with OwnedApplication(owned_root/'app',tasks=tasks) as host,OwnedBrowser(host.profile) as browser:
        home=owned_root/'life';cfg=initialize(home,host.profile,skills=False)
        binding=SurfaceBinding(binding_id='surface.web',platform='platform.local',surface='surface.web',adapter='adapter.owned')
        update_config(home,cfg.model_copy(update={'revision':2,'owned_browser_endpoint':browser.endpoint,'surface_bindings':(binding,)}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            original=app.work.port.execute;observed=[]
            def execute(inv):
                receipt=original(inv)
                if inv.capability=='world.publish':
                    incoming=SurfaceObservation(binding_id='surface.web',event_id='during-effect',topic='project',text='这个话题不要深入了')
                    thread=threading.Thread(target=lambda:observed.append(app.ingress.offer(incoming)));thread.start();thread.join(1);assert not thread.is_alive()
                return receipt
            monkeypatch.setattr(app.work.port,'execute',execute)
            until(app,lambda:bool(observed))
            assert len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])==1
            before=len(app.runtime.store.all('actions'));reply=app.tick()['surface_ingress']
            assert reply['event_id']=='during-effect' and reply['result']['mode']=='RESPECT_BOUNDARY'
            assert len(app.runtime.store.all('actions'))==before
            assert app.runtime.store.db.execute("SELECT count(*) FROM actions WHERE capability='world.publish'").fetchone()[0]==1
