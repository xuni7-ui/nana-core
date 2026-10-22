import json
import pytest
from nana_core.life.control import dispatch
from nana_core.life.inspector import inspect
from nana_core.continuity.identity import IdentityService
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity.contracts import EvidenceInput,Provenance
from .test_continuity import propose


def test_profile_is_explicit_authority_generic_and_identity_survives(app):
    r=app.runtime;old=r.identity_id;charter=r.store.identity['body_json']
    service=IdentityService(r.store,r.authority)
    with pytest.raises(CoreError,match='UNAUTHENTICATED_OPERATOR'):
        service.revise_profile(expected_revision=1,name='Another Subject',aliases=(),reason='test',authority=OperatorAuthority())
    value=dispatch(app,{'operation':'self-profile','name':'Different Subject','aliases':['Reference Subject'],'expected_revision':1,'reason':'Explicit synthetic instance profile'})
    assert value['identity_id']==old and value['name']=='Different Subject'
    assert json.loads(charter)['charter']==json.loads(r.store.identity['body_json'])['charter']
    assert not r.store.all('grants')
    with pytest.raises(CoreError,match='STALE_IDENTITY_REVISION'):
        dispatch(app,{'operation':'self-profile','name':'bad','aliases':[],'expected_revision':1,'reason':'stale'})
    with pytest.raises(CoreError,match='CLOUD_OPERATION_DENIED'):
        dispatch(app,{'operation':'self-profile','authority':'fake'})


def test_inspector_self_is_read_only_and_no_false_forgetting(app):
    c,mid,e=propose(app)
    before=app.runtime.store.db.execute('SELECT max(seq) FROM events').fetchone()[0]
    view=inspect(app.home,scope='project-work',entity_id='project-user')
    assert view.read_only and view.self_view['model_is_resource_not_self']
    assert view.self_view['adopted_conventions'][0]['value']=='sibling'
    assert app.runtime.store.db.execute('SELECT max(seq) FROM events').fetchone()[0]==before
    app.forget(mid)
    later=inspect(app.home,scope='project-work',entity_id='project-user')
    assert later.self_view['recall_status']['RELATIONSHIP_ROLE']=='SOURCE_WITHDRAWN'
    assert 'sibling' not in json.dumps(later.self_view)


def test_conversation_retention_requires_consent_and_never_allows_secret(app):
    base=dict(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.input',source_reference='sample',source_kind='USER_STATEMENT'),text='synthetic',privacy_class='PERSONAL',observed_time_us=app.clock.utc_now_us())
    from nana_core.continuity.memory import MemoryService
    with pytest.raises(CoreError,match='EXPLICIT_CONVERSATION_RETENTION_REQUIRED'):
        MemoryService(app.runtime.store).capture(EvidenceInput(**base))
    with pytest.raises(CoreError,match='EXPLICIT_CONVERSATION_RETENTION_REQUIRED'):
        MemoryService(app.runtime.store).capture(EvidenceInput(**{**base,'privacy_class':'SECRET'},retention_consent_ref='sample'))
