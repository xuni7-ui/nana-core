from uuid import uuid4
from nana_core.continuity import ContinuityStore
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority,verify_package
from nana_core.continuity.person_self import adopted
from nana_core.continuity.lived_language import expression_policy
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from .test_continuity import propose
from .test_learning import record,activate
from .conftest import initialize
from tests.independent_life.test_dialogue import relay


def test_official_package_carries_self_roles_lessons_not_provider_or_new_grants(app,tmp_path):
    propose(app);record(app,1);_,eid=record(app,2);activate(app,eid)
    home=app.home;identity=app.runtime.identity_id;clock=app.clock;app.close()
    target=str(uuid4());authority=PortableTransferAuthority()
    with ContinuityStore(home/'subject/self.db',clock,schema_target=13) as source:
        package=SubjectPackageService(source,authority).export(tmp_path/'person.zip',destination_id=target,source_commit='ae3cb34d478caa62861d2a6b85ddf4ed2cc8f11e',authority=authority)
    manifest,files=verify_package(package['path'],expected_sha256=package['sha256'])
    assert set(files)=={'subject.sqlite','privacy.json','manifest.json'}
    root=tmp_path/'fresh-host';controller=PortableTransferAuthority(destination_id=target,destination_root=root)
    destination=SubjectPackageService.import_quarantined(package['path'],root,expected_sha256=package['sha256'],destination_id=target,authority=controller)
    with ContinuityStore(destination,clock,schema_target=13) as restored:
        SubjectPackageService(restored,controller).activate(transfer_id=manifest.transfer_id,destination_id=target,authority=controller)
        assert restored.identity['identity_id']==identity
        assert adopted(restored,'project-work','project-user',('PROJECT',))
        assert expression_policy(restored,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule']
        assert not restored.all('grants')
        assert not restored.db.execute('PRAGMA foreign_key_check').fetchall()


def test_two_cognition_configurations_preserve_same_self(app,tmp_path):
    propose(app);record(app,1);_,eid=record(app,2);activate(app,eid);home=app.home;clock=app.clock;identity=app.runtime.identity_id;app.close()
    other=tmp_path/'host-config-b';other.mkdir()
    with relay(home,'CHAT',profile_id='fixture.a',remote_model_id='model-a') as (a,req_a),relay(other,'CHAT',profile_id='fixture.b',remote_model_id='model-b') as (b,req_b):
        for i,router in enumerate((a,b)):
            with LifeApplication(home,clock=clock,router=router) as current:
                result=current.chat('Describe your current self',privacy='PROJECT',message_id='swap-'+str(i))
                assert result['render_state']=='UNVERIFIED_MODEL_WORDING',result
                assert current.runtime.identity_id==identity
                assert adopted(current.runtime.store,'project-work','project-user',('PROJECT',))
                assert expression_policy(current.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule']
        assert len(req_a)==len(req_b)==2
        assert req_a[0]['route_snapshot']['remote_model_id']!=req_b[0]['route_snapshot']['remote_model_id']
