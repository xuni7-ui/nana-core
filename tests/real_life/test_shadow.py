from dataclasses import asdict
import pytest
from nana_core.contracts import CoreError
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.project_work.service import open_project_runtime
from nana_core.continuity.dialogue_shadow.bridge import ShadowBinding,NewExcerpt,NewMessageShadow,SemanticInterpretation


def binding(r,**kw):
    return ShadowBinding(subject_id=r.identity_id,entity_id='project-user',scope='project-work',host_binding_id='manual',accepted_after_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+60_000_000,**kw)

def item(r,key,text,topic='daily',**kw):
    return NewExcerpt(event_id=key,host_binding_id='manual',subject_id=r.identity_id,entity_id='project-user',scope='project-work',occurred_at_us=r.clock.utc_now_us(),topic=topic,text=text,**kw)


def test_default_denied_and_live_not_implicitly_authorized(tmp_path):
    with open_project_runtime(tmp_path/'subject/self.db',VirtualClock()) as r:
        with pytest.raises(CoreError,match='SHADOW_DISABLED'):NewMessageShadow(r,binding(r)).review(item(r,'new','请帮我看看'))
        with pytest.raises(CoreError,match='BLOCKED_BY_EXPLICIT'):NewMessageShadow(r,binding(r,enabled=True,source_mode='LIVE_HOST_NEW_ONLY')).review(item(r,'new','请帮我看看'))
        assert not r.store.all('subject_cycles')


def test_anonymous_language_causal_refusal_and_no_raw_or_send(tmp_path):
    with open_project_runtime(tmp_path/'subject/self.db',VirtualClock()) as r:
        bridge=NewMessageShadow(r,binding(r,enabled=True))
        vent=item(r,'vent','今天只想吐槽 UNIQUE_ANONYMOUS_CANARY')
        a=bridge.review(vent);assert a.applied=='VENT' and a.intention=='SOCIAL_INTERACTION' and a.draft
        assert bridge.review(vent)==a
        refusal=bridge.review(item(r,'refuse','别再研究这件事了','closed'))
        assert refusal.applied=='RESPECT_BOUNDARY' and not refusal.draft
        later=bridge.review(item(r,'help','请帮我看看','closed'));assert later.applied=='RESPECT_BOUNDARY' and later.intention=='NO_ACTION'
        help_=bridge.review(item(r,'other','请帮我排查错误','other'));assert help_.applied=='HELP'
        uncertain=bridge.review(item(r,'unclear','如果她说“不要研究”，怎么办？'));assert uncertain.applied=='UNCLEAR'
        assert not r.store.all('actions') and not r.store.all('goals') and not r.store.all('grants')
        assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'UNIQUE_ANONYMOUS_CANARY')>0").fetchone()
        assert not any(x.external_delivery for x in (a,later,help_))


def test_model_cannot_certify_own_interpretation_or_change_binding(tmp_path):
    class Untrusted:
        def interpret(self,text):return SemanticInterpretation(kind='HELP',basis='HUMAN_REVIEW',support_start=0,support_end=len(text),mechanism='unreviewed-fixture')
    with open_project_runtime(tmp_path/'subject/self.db',VirtualClock()) as r:
        bridge=NewMessageShadow(r,binding(r,enabled=True),Untrusted())
        result=bridge.review(item(r,'x','只是无确定含义的句子'))
        assert result.inferred=='HELP' and result.applied=='UNCLEAR'
        with pytest.raises(CoreError,match='SHADOW_BINDING_MISMATCH'):bridge.review(item(r,'wrong','请帮我看看').model_copy(update={'entity_id':'other'}))
        with pytest.raises(CoreError,match='SHADOW_NOT_FRESH'):bridge.review(item(r,'old','请帮我看看').model_copy(update={'occurred_at_us':0}))
        with pytest.raises(CoreError,match='SHADOW_PRIVACY_DENIED'):bridge.review(item(r,'secret','请帮我看看',privacy='SECRET'))


def test_reopen_does_not_replay_shadow_or_emit_after_restart(tmp_path):
    clock=VirtualClock();db=tmp_path/'subject/self.db'
    with open_project_runtime(db,clock) as r:
        b=binding(r,enabled=True);e=item(r,'once','和你分享今天的事')
        NewMessageShadow(r,b).review(e);identity=r.identity_id;before=len(r.store.all('subject_cycles'))
    with open_project_runtime(db,clock) as r:
        assert r.identity_id==identity
        with pytest.raises(CoreError,match='SHADOW_ALREADY_REVIEWED'):NewMessageShadow(r,b).review(e)
        assert len(r.store.all('subject_cycles'))==before
