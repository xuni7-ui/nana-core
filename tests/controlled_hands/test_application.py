import json,os
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject.growth_life import opportunities
from .conftest import initialize,until

def test_real_subject_outcome_learning_transfer_and_bounded_extension(tmp_path):
    with OwnedApplication(tmp_path/'target') as host:
        home=tmp_path/'life';initialize(home,host.profile)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime;identity=r.identity_id;initial_grants=len(r.store.all('grants'))
            until(app,lambda:len(r.store.all('goals'))==8 and all(g['state'] in {'COMPLETED','FAILED'} for g in r.store.all('goals')))
            until(app,lambda:len(r.store.all('strategy_assessments'))>=4)
            events=[json.loads(x[0])['data'] for x in r.store.db.execute("SELECT data_json FROM events WHERE kind='living.goal_step_completed' AND json_extract(data_json,'$.data.operator_id')='apply' ORDER BY seq")]
            assert sum(x['quality'] for x in events)>=6 and sum(not x['quality'] for x in events)>=4
            assert any(e['outcome']=='FAILURE' for e in r.store.all('experiences'))
            assert all(x['state']=='DONE' for x in r.store.db.execute("SELECT state FROM jobs WHERE work_kind='LEARNING'"))
            assert len(r.store.db.execute("SELECT * FROM actions WHERE capability='world.skill' AND state='SUCCEEDED'").fetchall())==2
            assert all(x['state']=='SUSPENDED' for x in r.store.all('lessons'))
            assert (Path(host.target.workspace)/'document-baseline.txt').read_text()=='A verified note'
            assert (Path(host.target.workspace)/'document-transfer.txt').read_text()=='Meeting agenda'
            for key in ['form-baseline','form-transfer','form-batch-gap','form-batch-transfer']:
                state=app.work.port.peek(key)['state'];t=app.work.port.tasks[key]
                assert state['submitted'] and all(state['values'][k]==v for k,v in t.wanted.items())
            assert len(r.store.all('grants'))==initial_grants and r.identity_id==identity
            assert not r.store.all('cognitive_requests') and not list(r.store.db.execute('PRAGMA foreign_key_check'))
            board=app.board();assert board['derived'] and board['external_outcomes'] and board['skills']
            assert board['target_scope']['kind']=='OWNED_DEV_APPLICATION_PROCESS'
            assert len({a['idempotency_key'] for a in r.store.all('actions')})==len(r.store.all('actions'))
            # Withdrawal is causal; neither a projection nor source profile restores support.
            skill=app.work.skills.active_skill();parents=RecordService(r.store).support(skill)
            count=len(r.store.all('actions'));app.forget(parents[0]);assert app.work.skills.active_skill() is None
            import time
            for _ in range(30):app.tick();time.sleep(.02)
            assert len(r.store.all('actions'))==count
            assert not opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)
        with LifeApplication(home) as reopened:
            assert reopened.runtime.identity_id==identity and len(reopened.runtime.store.all('grants'))==initial_grants
            assert reopened.work.skills.active_skill() is None
            import time
            for _ in range(30):reopened.tick();time.sleep(.02)
            assert len(reopened.runtime.store.all('actions'))==count


def test_pause_revoke_and_target_identity_are_real_fences(tmp_path):
    task=ApplicationTask(task_id='only',kind='DOCUMENT',wanted='approved')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            app.pause();before=app.work.port.peek('only')['state'];[app.tick() for _ in range(3)]
            assert app.work.port.peek('only')['state']==before and not app.runtime.store.all('actions')
            app.pause(False);app.revoke()
            until(app,lambda:bool(app.runtime.store.db.execute("SELECT 1 FROM actions WHERE state='BLOCKED'").fetchone()))
            assert app.work.port.peek('only')['state']==before
            assert any(i['state']=='PENDING' for i in app.runtime.store.all('subject_intentions'))
            with pytest.raises(CoreError):
                app.work.port.target=app.work.port.target.model_copy(update={'process_start':'invalid'})
                app.work.port.assert_owned()


def test_overlapping_task_names_keep_opportunity_source_bound_to_exact_task(tmp_path):
    tasks=(ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='first'),
           ApplicationTask(task_id='doc-next',kind='DOCUMENT',wanted='second'))
    with OwnedApplication(tmp_path/'target',tasks=tasks) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home) as app:
            offered=app.work.offer(app.work.objects['doc-next'])
            source=RecordService(app.runtime.store).memory.read(offered['source_memory_id'])
            assert json.loads(source['text'])['task']['task_id']=='doc-next'
            assert not app.runtime.store.all('actions')


def test_target_rejects_reserved_derived_objective_name_collision(tmp_path):
    task=ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='finite')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        from nana_core.continuity.hands.contracts import OwnedTarget
        data=host.target.model_dump(mode='json')
        data['tasks'].append(ApplicationTask(task_id='doc-batch',kind='DOCUMENT',wanted='other').model_dump(mode='json'))
        with pytest.raises(ValueError,match='derived objective collision'):
            OwnedTarget.model_validate_json(json.dumps(data))
