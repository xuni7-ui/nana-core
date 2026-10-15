"""Synthetic perception ONLY. File/screen ports never touch host/device data."""
from ..contracts import CoreError
from ..storage import digest
from ..continuity.subject.contracts import SubjectInput,StandingDelegation
from .contracts import RuntimeEvent,Cause


class SyntheticPerceptionPort:
    event_type='WORLD_EVENT'
    trigger='ENVIRONMENT_CHANGE'
    name='world'

    def __init__(self,identity_id,entity_id,scope):
        self.identity_id,self.entity_id,self.scope=identity_id,entity_id,scope

    def observe(self,clock,source_key,text,*,significance='RELEVANT',novelty='LOW',source_memory_ids=(),result_for_intention_id=None,observed_availability=None):
        now=clock.utc_now_us()
        inp=SubjectInput(source_key='synthetic.perception.'+self.name+'.'+source_key,kind='OUTCOME',origin='ENVIRONMENT',
            entity_id=self.entity_id,scope=self.scope,text=text,observed_at_us=now,occurred_at_us=now,
            significance=significance,novelty=novelty,source_memory_ids=source_memory_ids,
            result_for_intention_id=result_for_intention_id,observed_availability=observed_availability)
        return RuntimeEvent(event_type=self.event_type,trigger=self.trigger,input=inp,
            causes=(Cause(kind='CANONICAL_SELF',reference_id=self.identity_id),),due_at_us=now)


class ScreenPerceptionPort(SyntheticPerceptionPort):
    event_type='DEVICE_EVENT';trigger='DEVICE_TRIGGER';name='screen-fixture'


class PresencePerceptionPort(SyntheticPerceptionPort):
    event_type='DEVICE_EVENT';trigger='DEVICE_TRIGGER';name='presence-fixture'


class PlatformEventPort(SyntheticPerceptionPort):
    event_type='PLATFORM_EVENT';trigger='INCOMING_EVENT';name='platform-fixture'


class FilePerceptionPort(SyntheticPerceptionPort):
    name='resource-fixture'

    def __init__(self,identity_id,entity_id,scope,resources=None):
        super().__init__(identity_id,entity_id,scope)
        # Caller supplies explicit synthetic observations, never OS paths.
        self.resources=resources or {}

    def simulate_read(self,proposal,delegation:StandingDelegation,clock,*,intention_id,novelty='LOW',observed_availability=None):
        now=clock.utc_now_us()
        resource=self.resources.get(proposal.resource_ref)
        if (delegation.subject!=self.identity_id or delegation.capability!='synthetic.resource.read'
            or delegation.revoked or not delegation.issued_at_us<=now<delegation.expires_at_us
            or proposal.resource_ref not in delegation.resource_scope or 'READ' not in delegation.operations
            or delegation.risk_ceiling!='READ_ONLY' or 'PERSONAL' not in delegation.privacy_scope
            or proposal.resource_class!='ORDINARY' or not resource or resource[0]!='ORDINARY'):
            raise CoreError('SYNTHETIC_DELEGATION_SCOPE_BLOCKED')
        # This is a supplied fixture outcome, not an executed Core Action,
        # receipt, actual filesystem read or real standing delegation registry.
        return self.observe(clock,digest([intention_id,proposal.resource_ref]),resource[1],
            source_memory_ids=proposal.source_memory_ids,result_for_intention_id=intention_id,novelty=novelty,observed_availability=observed_availability)
