"""Context paths skip projections that their output contract cannot retain."""
from unittest.mock import patch

from nana_core.continuity.context import ContextAssembler, ContextPolicy, ContextRequest
from nana_core.continuity.world_loop.world import WorldModel


def test_pinned_and_source_only_skip_discarded_world_and_lesson_projections(app):
    request=ContextRequest(entity_id='project-user',scopes=('project-work',),
        task_class='world.social',task='SYNTHETIC context selection',task_privacy_class='PROJECT')
    policy=ContextPolicy(policy_id='synthetic.context.selection',allowed_scopes=('project-work',),
        readable_privacy=('PROJECT',))
    assembler=ContextAssembler(app.runtime.store,app.runtime.authority)
    with patch.object(WorldModel,'snapshot',return_value=()) as world, \
         patch.object(ContextAssembler,'_lessons',return_value=[]) as lessons:
        pinned=assembler.assemble(request,policy,pinned_only=True,conversation_topic='daily')
        assembler.validate(pinned,request,policy)
        source=assembler.assemble(request,policy,source_only=True)
        assembler.validate(source,request,policy)
        assert world.call_count==0 and lessons.call_count==0
        ordinary=assembler.assemble(request,policy)
        assembler.validate(ordinary,request,policy)
        assert world.call_count==1 and lessons.call_count==1
