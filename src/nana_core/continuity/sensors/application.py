"""Application-owned transitions. A frontend gets sanitized DTOs, never handles."""
from ...contracts import CoreError
from .contracts import SourceCommand
class PerceptionSettingsService:
    def __init__(self,coordinator,authority):
        self.__coordinator,self.__authority=coordinator,authority
        coordinator.configuration._check(authority)
    def projection(self,context):
        c=self.__coordinator.configuration.load();items=[]
        for p in c.sources:
            if p.scope not in context.allowed_scopes or p.privacy_class not in context.readable_privacy:continue
            d=p.model_dump(mode='json',exclude={'adapter_ref','resource_ref'})
            try:
                port=self.__coordinator.resolver.resolve(p)
                if callable(getattr(port,'backend_projection',None)):d['screen_backend']=port.backend_projection()
            except CoreError:d['screen_backend']={'health':'UNAVAILABLE','capture_authority':False}
            d['resource_label']=p.source_kind.lower()+' source';items.append(d)
        return {'schema_version':c.schema_version,'revision':c.revision,'sources':items,'policy':c.policy.model_dump(mode='json'),'storage':'HOST_LOCAL_NOT_SUBJECT_MEMORY','capture_authority':False}
    def command(self,command,context):
        if type(command) is not SourceCommand:raise CoreError('PERCEPTION_TYPED_COMMAND_REQUIRED')
        c=self.__coordinator.configuration.load();p=command.profile or next((p for p in c.sources if p.source_profile_id==command.target_id),None)
        if p and (p.scope not in context.allowed_scopes or p.privacy_class not in context.readable_privacy):raise CoreError('PERCEPTION_CONFIG_SCOPE_DENIED')
        self.__coordinator.configuration.update(command,self.__authority)
        return self.projection(context)
    def request_capture(self,*,source_id,request_id,expected_revision,context):
        c=self.__coordinator.configuration.load()
        if c.revision!=expected_revision:raise CoreError('PERCEPTION_CONFIG_REVISION_CONFLICT')
        p=self.__coordinator._source(source_id)
        if p.scope not in context.allowed_scopes or p.privacy_class not in context.readable_privacy:raise CoreError('PERCEPTION_PRIVACY_DENIED')
        req=self.__coordinator.request(source_id,request_id=request_id,foreground=True)
        self.__coordinator.enqueue(req)
        return {'request_id':request_id,'state':'REQUESTED','config_revision':c.revision}
    def status(self,context):return self.__coordinator.status(context)
