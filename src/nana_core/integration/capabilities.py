"""Host capability catalogue: specifications, never production backends."""
from typing import Literal
from ..contracts import DTO,CoreError

class HostCapabilitySpec(DTO):
    capability_id:str
    version:int=1
    effect:Literal['read','write']
    resource_scope:str
    required_grant:str
    idempotency_support:str
    verification_method:str
    failure_ambiguity:str
    unknown_recovery:str
    maturity:Literal['DESIGN_ONLY','ENGINEERING_TESTED','LEGACY_PARTIAL']
    production_enabled:Literal[False]=False

CATALOGUE=(
 HostCapabilitySpec(capability_id='bilibili.comment.send',effect='write',resource_scope='explicit video/root/account',required_grant='per-capability+exact-resource',
 idempotency_support='no proven upstream idempotency; local effect-slot is not server guarantee',verification_method='independent account/content/root/rpid list reconciliation, not send response',
 failure_ambiguity='timeout/partial response/existing comment ambiguity UNKNOWN',unknown_recovery='read-only reconcile; never resend UNKNOWN',maturity='LEGACY_PARTIAL'),
 HostCapabilitySpec(capability_id='astrbot.message.send',effect='write',resource_scope='exact platform/account/conversation',required_grant='per-capability+exact-conversation',
 idempotency_support='host/platform dependent UNKNOWN',verification_method='independent message history/delivery acknowledgement when available; otherwise INCONCLUSIVE',
 failure_ambiguity='send-return is not delivery proof',unknown_recovery='query platform history; no blind retry',maturity='DESIGN_ONLY'),
 HostCapabilitySpec(capability_id='host.file.read',effect='read',resource_scope='operator fixed nonsecret regular-file allowlist',required_grant='read+verify exact file',
 idempotency_support='read-id/hash snapshot; no write',verification_method='independent byte/hash/metadata equality against bound snapshot',
 failure_ambiguity='file changed/read missing UNKNOWN',unknown_recovery='verify snapshot, never pretend original full evidence',maturity='ENGINEERING_TESTED'),
 HostCapabilitySpec(capability_id='qq.napcat.send',effect='write',resource_scope='exact account/conversation',required_grant='per-capability+exact-conversation',
 idempotency_support='not established',verification_method='native message id + independent retrieval if supported',
 failure_ambiguity='delivery and dedup UNKNOWN',unknown_recovery='read-only platform reconciliation before any new action',maturity='DESIGN_ONLY'))

class DisabledHostCapabilityAdapter:
    def execute(self,invocation):raise CoreError('PRODUCTION_CAPABILITY_NOT_ENABLED')
    def verify(self,invocation):raise CoreError('NO_PRODUCTION_VERIFICATION_EVIDENCE')
