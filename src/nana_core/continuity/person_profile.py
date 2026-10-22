"""Explicit trusted instance profile revisions, separate from learned self facts."""
import json
from ..contracts import CoreError
from ..storage import canonical,uid
from .identity import IdentityProvenance

def revise_profile(service, *, expected_revision, name, aliases, reason, authority):
    if authority is not service._authority:
        raise CoreError('UNAUTHENTICATED_OPERATOR')
    if type(expected_revision) is not int or type(name) is not str or not 1<=len(name)<=96 or type(aliases) is not tuple or len(aliases)>8 or any(type(a) is not str or not 1<=len(a)<=96 for a in aliases) or len(set(aliases))!=len(aliases) or type(reason) is not str or not 1<=len(reason)<=512:
        raise CoreError('INVALID_IDENTITY_PROFILE')
    with service.store.transaction('self.profile_revised') as tx:
        old=service.store.all('identity_revisions')[-1]
        if old['revision']!=expected_revision:raise CoreError('STALE_IDENTITY_REVISION')
        body=json.loads(old['body_json']);body['name']=name;body['aliases']=aliases
        tx.put('identity_revisions',{**old,'revision_id':uid(),'revision':old['revision']+1,
            'supersedes':old['revision_id'],'body_json':canonical(body),
            'provenance_json':IdentityProvenance(source='OPERATOR_REVIEW',reference_id=old['revision_id']).model_dump_json(),
            'authority':'OPERATOR_REVIEW','reason_artifact_id':tx.artifact(reason.encode()),
            'created_at_us':service.store.clock.utc_now_us(),'event_id':tx.event_id})
        tx.update('identities',old['identity_id'],revision=old['revision']+1,body_json=canonical(body))
    return service.current()

