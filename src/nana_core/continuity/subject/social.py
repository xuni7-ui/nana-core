"""Semantic social proposals inside C. No utterance renderer or sender."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO


class SocialInteractionProposal(DTO):
    act: Literal['START_CONVERSATION','SHARE_THOUGHT','TEASE','ASK','CHECK_IN','INVITE_TO_PLAY','REPORT_DISCOVERY','EXPRESS_OPINION','STAY_SILENT']
    topic_key: str
    approach: Literal['CHECK_RECEPTION','CONTEXT_SUPPORTED_VARIATION','RESPECT_DISTANCE','NO_INTERRUPTION']
    source_memory_ids: tuple[str,...]
    lesson_ids: tuple[str,...] = ()
    utterance: Literal[None] = None
    delivery_authority: Literal[False] = False


class InteractionRule(DTO):
    kind: Literal['CONTEXTUAL_PLAY_VARIATION'] = 'CONTEXTUAL_PLAY_VARIATION'
    scope: Literal['interaction.shared_discovery'] = 'interaction.shared_discovery'
    vary_expression: Literal[True] = True
    require_receptive_context: Literal[True] = True


def propose_social(*,topic,style,available,source_ids,lesson_ids=(),last_act=None):
    if not available:
        return SocialInteractionProposal(act='STAY_SILENT',topic_key=topic,approach='NO_INTERRUPTION',source_memory_ids=source_ids)
    if style=='WARM_PLAYFUL':
        # Learned variation changes proposal, not a fixed joke/utterance.
        learned=bool(lesson_ids)
        return SocialInteractionProposal(act='SHARE_THOUGHT' if learned and last_act=='TEASE' else 'TEASE',
            topic_key=topic,approach='CONTEXT_SUPPORTED_VARIATION' if learned else 'CHECK_RECEPTION',
            source_memory_ids=source_ids,lesson_ids=lesson_ids)
    return SocialInteractionProposal(act='ASK',topic_key=topic,approach='RESPECT_DISTANCE',source_memory_ids=source_ids)
