"""Reuse the original private JSON atomic/CAS primitives, not another Store."""
import os
from ...contracts import CoreError
from ..provider_config import ProviderConfigService,ProviderConfigurationAuthority
from .contracts import *
PerceptionConfigurationAuthority=ProviderConfigurationAuthority
class PerceptionConfigService(ProviderConfigService):
    document_type=PerceptionConfiguration
    def __init__(self,path,authority,resolver):
        super().__init__(path,authority);self.__resolver=resolver
    def load(self):
        c=super().load()
        for p in c.sources:self.__resolver.resolve(p)
        return c
    def update(self,command,authority):
        self._check(authority)
        if type(command) is not SourceCommand:raise CoreError('PERCEPTION_TYPED_COMMAND_REQUIRED')
        command=SourceCommand.model_validate_json(command.model_dump_json());fd=self._lock()
        try:
            c=self._load()
            if c.revision!=command.expected_revision:raise CoreError('PERCEPTION_CONFIG_REVISION_CONFLICT')
            ps={p.source_profile_id:p for p in c.sources};op=command.operation;target=command.target_id;policy=c.policy
            if op=='UPSERT_PERCEPTION_SOURCE':
                p=command.profile;self.__resolver.resolve(p);ps[p.source_profile_id]=p.model_copy(update={'revision':ps[p.source_profile_id].revision+1 if p.source_profile_id in ps else 1})
            elif op=='SET_CAPTURE_POLICY':policy=command.policy
            else:
                if target not in ps:raise CoreError('SOURCE_UNAVAILABLE')
                if op=='REMOVE_PERCEPTION_SOURCE':del ps[target]
                else:ps[target]=ps[target].model_copy(update={'enabled':op=='ENABLE_PERCEPTION_SOURCE','revision':ps[target].revision+1})
            updated=PerceptionConfiguration(revision=c.revision+1,sources=tuple(ps.values()),policy=policy)
            self._atomic(updated);return updated
        finally:os.close(fd)
