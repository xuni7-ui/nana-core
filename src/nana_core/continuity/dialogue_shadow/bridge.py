"""Minimal shadow application, using the original C context-fit and D queue.

V1 admits manually authorized/anonymized development excerpts only. A production
host must first obtain new-message consent AND qualify its binding; neither task
text nor an input boolean enables live QQ. No shadow installation is performed.
"""
import re
import time
from dataclasses import dataclass
from typing import Literal, Protocol
from pydantic import Field
from ...contracts import DTO, CoreError
from ...storage import digest
from ..subject import SubjectInput
from ..subject.context_fit import InteractionSignal
from ...presence.contracts import RuntimeEvent, Cause


class ShadowBinding(DTO):
    enabled: bool = False
    subject_id: str
    entity_id: str
    scope: str
    host_binding_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    accepted_after_us: int = Field(ge=0)
    expires_at_us: int = Field(ge=0)
    max_age_us: int = Field(default=30_000_000,ge=1,le=60_000_000)
    source_mode: Literal['ANONYMOUS_MANUAL','LIVE_HOST_NEW_ONLY'] = 'ANONYMOUS_MANUAL'


class NewExcerpt(DTO):
    event_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    host_binding_id: str
    subject_id: str
    entity_id: str
    scope: str
    occurred_at_us: int = Field(ge=0)
    topic: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    privacy: Literal['PUBLIC','PROJECT','PERSONAL','SECRET'] = 'PROJECT'
    text: str = Field(min_length=1,max_length=1024)
    manually_authorized_nonprivate: Literal[True] = True


class SemanticInterpretation(DTO):
    kind: Literal['VENT','HELP','SHARE','DECLINE_DEPTH','REOPEN','FOCUS','UNCLEAR','IMPORTANT','PROJECT_STATUS']
    basis: Literal['LITERAL_SPAN','HUMAN_REVIEW','UNREVIEWED_PROPOSAL']
    support_start: int = Field(ge=0)
    support_end: int = Field(ge=0)
    mechanism: str = Field(min_length=1,max_length=64)
    # This is an interpretation. It contains no entity binding/goal/permissions.


class SemanticInterpreter(Protocol):
    def interpret(self, text: str) -> SemanticInterpretation: ...


LITERALS=(('DECLINE_DEPTH',('不要研究','别再研究','别分析','不要再提','不要深入')),('REOPEN',('可以再讨论','重新谈谈')),('FOCUS',('先专注这件事','现在先帮我')),('VENT',('只是吐槽','只想吐槽')),('HELP',('请帮我','帮我排查')),('SHARE',('和你分享','分享一下')))


class LiteralSpanInterpreter:
    """Small deterministic baseline, not a real-model/human language qualification."""
    def interpret(self,text):
        # Conflicting explicit cues, quotation and hypothetical language are
        # deliberately uncertain. Never pick refusal out of an adversarial quote.
        if any(x in text for x in ('“','”','"','如果','假如','不是','并非')):
            return SemanticInterpretation(kind='UNCLEAR',basis='UNREVIEWED_PROPOSAL',support_start=0,support_end=0,mechanism='literal-baseline')
        # Narrow explicit status questions; no subject names/personality branches.
        # Refusal/reopen spans retain precedence. Quoted/hypothetical text above
        # is not promoted to a current request by keyword matching.
        status_spans=('做到哪','当前阶段','目前阶段','现在这个阶段','现在进展','目前进展','当前进度','现在进度','目前状态','current project status','project progress')
        lower=text.lower();spans=[p for p in status_spans if p in lower]
        unrelated=any(p in text for p in ('身体','心情','情绪','我们的关系','关系目前状态','饭做到哪','菜做到哪'))
        refusal=any(p in text for k,ps in LITERALS if k in {'DECLINE_DEPTH','REOPEN'} for p in ps)
        questioning=any(p in lower for p in ('?','？','吗','么','哪','怎么看','如何','怎样','汇报','报告','告诉我','说说','说下','what','how')) or lower.strip() in status_spans
        if spans and questioning and not unrelated and not refusal:
            phrase=spans[0];start=lower.index(phrase)
            return SemanticInterpretation(kind='PROJECT_STATUS',basis='LITERAL_SPAN',support_start=start,support_end=start+len(phrase),mechanism='explicit-project-status-span')
        matches=[(kind, phrase,text.index(phrase)) for kind,phrases in LITERALS for phrase in phrases if phrase in text]
        if len({k for k,_,_ in matches})!=1:
            return SemanticInterpretation(kind='UNCLEAR',basis='UNREVIEWED_PROPOSAL',support_start=0,support_end=0,mechanism='literal-baseline')
        kind,phrase,start=matches[0]
        return SemanticInterpretation(kind=kind,basis='LITERAL_SPAN',support_start=start,support_end=start+len(phrase),mechanism='literal-baseline')


@dataclass(frozen=True)
class ShadowReview:
    event_id: str
    inferred: str
    applied: str
    judgment: str
    intention: str
    social_proposal: str | None
    draft: str | None
    reason: str
    latency_ms: float
    raw_persisted: bool = False
    external_delivery: bool = False
    language_quality: str = 'LOCAL_BASELINE_NOT_REAL_MODEL_OR_HUMAN_QUALIFIED'


class NewMessageShadow:
    def __init__(self,runtime,binding:ShadowBinding,interpreter:SemanticInterpreter|None=None):
        self.runtime=runtime;self.binding=binding.model_copy();self.interpreter=interpreter or LiteralSpanInterpreter()
        self._reviews={}

    def review(self,item:NewExcerpt):
        start=time.monotonic();b=self.binding;r=self.runtime;now=r.clock.utc_now_us()
        if not b.enabled:raise CoreError('SHADOW_DISABLED')
        if b.source_mode!='ANONYMOUS_MANUAL':raise CoreError('BLOCKED_BY_EXPLICIT_AUTHORIZATION_AND_HOST_QUALIFICATION')
        if (item.subject_id,item.entity_id,item.scope,item.host_binding_id)!=(b.subject_id,b.entity_id,b.scope,b.host_binding_id) or b.subject_id!=r.identity_id:
            raise CoreError('SHADOW_BINDING_MISMATCH')
        if not b.accepted_after_us<=item.occurred_at_us<=now<b.expires_at_us or now-item.occurred_at_us>b.max_age_us:raise CoreError('SHADOW_NOT_FRESH')
        if item.privacy not in r.config.privacy_classes or item.privacy not in {'PUBLIC','PROJECT'}:raise CoreError('SHADOW_PRIVACY_DENIED')
        key=digest([b.host_binding_id,item.event_id])
        if key in self._reviews:return self._reviews[key]
        source='synthetic.shadow.'+key
        # Header dedupe survives restart. No body/hash of message persisted here.
        if r.store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',(source,)).fetchone():raise CoreError('SHADOW_ALREADY_REVIEWED_NO_REPLAY')
        if len(self._reviews)>=32:raise CoreError('SHADOW_REVIEW_BOUND')
        interpretation=SemanticInterpretation.model_validate(self.interpreter.interpret(item.text))
        if not 0<=interpretation.support_start<=interpretation.support_end<=len(item.text):raise CoreError('SHADOW_SPAN_INVALID')
        trusted=False  # Interpreter proposals cannot self-certify human review.
        if interpretation.basis=='LITERAL_SPAN':
            span=item.text[interpretation.support_start:interpretation.support_end]
            trusted=any(kind==interpretation.kind and span in phrases for kind,phrases in LITERALS)
            if interpretation.kind=='PROJECT_STATUS':
                checked=LiteralSpanInterpreter().interpret(item.text)
                trusted=checked.kind=='PROJECT_STATUS' and (checked.support_start,checked.support_end)==(interpretation.support_start,interpretation.support_end)
        kind=interpretation.kind if trusted else 'UNCLEAR'
        # Raw excerpt is used only by the interpreter in memory. C receives a
        # minimal reviewed semantic occurrence, never private raw conversation.
        # In this V1 these are manual anonymous examples (synthetic domain).
        inp=SubjectInput(source_key=source,kind='INTERACTION',origin='USER',entity_id=item.entity_id,scope=item.scope,
            occurred_at_us=item.occurred_at_us,observed_at_us=now,privacy_class=item.privacy,
            text='Anonymous development excerpt; reviewed semantic cue: '+kind,
            interaction_signal=InteractionSignal(kind=kind,topic_key=item.topic,basis='EXPLICIT' if trusted else 'INTERPRETED'))
        # Use original D reactive opportunity; do not create an expression loop.
        qid=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=now,priority=3))
        value=r.step()
        row=r.store.one('runtime_queue',qid)
        if not row or row['state']!='DONE' or not value or not value.get('cycle'):raise CoreError('SHADOW_QUEUED_REVIEW_PENDING')
        cycle=value['cycle'];mode=cycle.context_fit.mode
        # Deterministic draft contract only. No claim of completed work/delivery,
        # no generated facts or claim about the user's hidden emotions.
        draft={'VENT':'我在听。你想继续说的话，我陪着。','SHARE':'想听你接着说。','HELP':'可以，我们先确认一下你希望解决的具体问题。',
               'UNCLEAR':'你想让我听你说，还是一起想想办法？','FOCUS':'好，先看你现在需要的这件事。'}.get(mode)
        review=ShadowReview(item.event_id,interpretation.kind,mode,cycle.judgment.stance,cycle.intention.kind,
            cycle.social_proposal.act if cycle.social_proposal else None,draft,cycle.judgment.reason,(time.monotonic()-start)*1000)
        self._reviews[key]=review
        return review
