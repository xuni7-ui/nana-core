from nana_core.life.application import LifeApplication
from nana_core.life.surfaces import SurfaceBinding
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from tests.cloud_life.conftest import initialize, until


def test_real_owned_outcome_original_c_candidate_projection_and_withdrawal(tmp_path):
    task = ApplicationTask(task_id='note', kind='DOCUMENT', wanted='finite')
    with OwnedApplication(tmp_path/'app', tasks=(task,)) as target:
        home=tmp_path/'life'
        initialize(home, owned_application_profile=str(target.profile),
            quiet_start_local_hour=0, quiet_end_local_hour=0,
            surface_bindings=(SurfaceBinding(binding_id='cloud.cli', platform='cloud.local',
                surface='chat.direct', adapter='shadow.local'),))
        with LifeApplication(home, bootstrap_grant=True) as app:
            until(app, lambda: bool(app.shared.candidates()))
            app.pause()
            candidate=app.shared.candidates()[0]
            app.presence('AVAILABLE', privacy_classes=('PUBLIC','PROJECT'))
            offered=app.shared.opportunity()
            app.pause(False)
            until(app, lambda: app.runtime.store.one('runtime_queue',offered['queue_id'])['state']=='DONE')
            app.pause()
            app.shared.reconcile()
            view=app.shared.inbox(privacy=('PUBLIC','PROJECT'))
            assert view['coverage']=='ORIGINAL_C_APPROVED_CANDIDATES_ONLY'
            assert not view['external_delivery'] and len(view['items'])==1
            assert view['items'][0]['delivery']=='NONE' and view['items'][0]['source_memory_ids']
            assert app.shared.inbox(privacy=('PUBLIC',))['items']==[]
            assert app.shared.notification_inbox(privacy=('PUBLIC','PROJECT'))['items']==[]  # paused
            app.pause(False)
            hints=app.shared.notification_inbox(privacy=('PUBLIC','PROJECT'))
            assert hints['items']==[{'event_id':view['items'][0]['candidate_record_id'],'page':'home','kind':'SHARED_CANDIDATE_AVAILABLE'}]
            assert not hints['private_body_in_notification']
            assert app.shared.notification_inbox(privacy=('PUBLIC',))['items']==[]
            assert app.shared.notification_inbox(privacy=('PUBLIC','PROJECT'),scope='other')['items']==[]
            app.presence('BUSY', privacy_classes=('PUBLIC','PROJECT'))
            assert app.shared.notification_inbox(privacy=('PUBLIC','PROJECT'))['items']==[]
            app.presence('AVAILABLE', privacy_classes=('PUBLIC','PROJECT'))
            app.forget(candidate['source_memory_ids'][0])
            assert app.shared.inbox(privacy=('PUBLIC','PROJECT'))['items']==[]
            assert app.shared.notification_inbox(privacy=('PUBLIC','PROJECT'))['items']==[]
