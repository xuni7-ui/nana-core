import ast
from pathlib import Path
from uuid import uuid4
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority
from nana_core.continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority,primary_user_view
from nana_core.continuity.relational.contracts import SubjectPersonalitySeed,RelationalAnchorSpec
from nana_core.continuity.relational.projections import personality_tendencies
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig
from .test_package import BASE

@pytest.mark.parametrize('version',[7,8,9])
def test_opt_in_v10_migration_preserves_existing_identity_and_defaults(tmp_path,version):
    path=tmp_path/str(version)/'self.db';authority=OperatorAuthority()
    with ContinuityStore(path,VirtualClock(),schema_target=version) as s:
        original=IdentityService(s,authority).current()
        MemoryService(s).entity('existing-person','PERSON')
    with ContinuityStore(path,VirtualClock(),schema_target=10) as s:
        assert IdentityService(s,authority).current()==original
        assert s.one('entities','existing-person')
        assert s.db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert s.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]==39
    with ContinuityStore(tmp_path/'default'/'self.db',VirtualClock()) as s:assert s.schema_target==7
    assert RuntimeConfig(scopes=('lab',),entity_id='existing-person').schema_target==8


def test_two_packages_keep_distinct_source_personality_and_no_identity_specific_branches(tmp_path):
    views=[]
    for index,trait in enumerate(('LOW','HIGH')):
        with ContinuityStore(tmp_path/('source'+str(index))/'self.db',VirtualClock(),schema_target=10) as store:
            IdentityService(store,OperatorAuthority());MemoryService(store).entity('person-a','PERSON')
            boot=SubjectBootstrapAuthority();service=SubjectBootstrapService(store,boot)
            service.install(SubjectPersonalitySeed(identity_id=store.identity['identity_id'],scope='lab',revision=1,relational_accommodation=trait),boot)
            if index:
                service.install(RelationalAnchorSpec(identity_id=store.identity['identity_id'],anchor_id='primary',entity_id='person-a',role_kind='PRIMARY_USER',role_label='companion',scope='lab',revision=1,effective_from_us=store.clock.utc_now_us()),boot)
            authority=PortableTransferAuthority();target=str(uuid4());root=tmp_path/('destination'+str(index))
            package=SubjectPackageService(store,authority).export(tmp_path/(str(index)+'.zip'),destination_id=target,source_commit=BASE,authority=authority)
            dest=PortableTransferAuthority(destination_id=target,destination_root=root)
            path=SubjectPackageService.import_quarantined(package['path'],root,expected_sha256=package['sha256'],destination_id=target,authority=dest)
        with ContinuityStore(path,VirtualClock(),schema_target=10) as restored:
            view=personality_tendencies(restored,scope='lab',privacy_classes=('PERSONAL',))
            views.append(next(f.assessment for f in view.facets if f.name=='relational_accommodation'))
            assert bool(primary_user_view(restored,scope='lab',privacy_classes=('PERSONAL',)))==bool(index)
            assert not restored.all('grants') and not restored.all('actions')
    assert views==['LOW','HIGH']
    root=Path(__file__).resolve().parents[2]/'src'/'nana_core'
    paths=[*root.joinpath('continuity','relational').glob('*.py'),*(root/'continuity'/x for x in ('extensions.py','surfaces.py','portable.py','providers.py','application.py'))]
    forbidden={'nana','sister','姐姐','妹妹','owner','master'}
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Compare):
                assert not any(isinstance(x,ast.Constant) and isinstance(x.value,str) and x.value.lower() in forbidden for x in ast.walk(node)),path
