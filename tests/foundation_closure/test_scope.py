import pytest
from nana_core.continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
from nana_core.continuity.subject.context_fit import depth_boundary
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.subject.opportunities import ConcernCue
from tests.vision_first.test_context_fit import interaction,wake
from tools.nana_vision_first.demo import source,cue,post,advance
from nana_core.continuity.open_agency.fixtures import numeric_learning

@pytest.mark.parametrize('text',['先不聊这个了','别分析了','这个话题停一下','这个先不要深入'])
def test_delivery_decline_preserves_same_topic_internal_need(tmp_path,text):
    clock=VirtualClock();path=tmp_path/'self.db'
    with open_runtime(path,clock) as r:
        r.work.configure_open_learning((numeric_learning(),))
        root=source(r,'gap',{'measurement':'a public precision gap'})
        mid=cue(r,'interest',ConcernCue(cue_kind='OPEN_LOOP',topic_key='numbers',motivation_source='CAPABILITY_GAP',possible_behaviors=('LEARN',),program_id='learn.numbers'),parents=(root,))
        meaning=LiteralSpanInterpreter().interpret(text)
        assert meaning.kind=='DECLINE_DELIVERY'
        r.subject.run(interaction(r,'silence',meaning.kind,'numbers'))
        assert depth_boundary(r.store,'observer','world','numbers',('PUBLIC',))[0]
        assert not depth_boundary(r.store,'observer','world','numbers',('PUBLIC',),purpose='COGNITION')[0]
        identity=r.identity_id
    with open_runtime(path,clock) as r:
        r.work.configure_open_learning((numeric_learning(),))
        cycle=r.subject.run(wake(r,'independent',mid))
        assert cycle.intention.behavior=='LEARN' and cycle.goal_candidate_id and r.identity_id==identity
        assert not r.store.all('actions') and not r.store.all('grants')
        # A running learning slice also honors the separate processing boundary.
        r.work.open_learning.after_cycle(r,cycle,wake(r,'independent',mid))
        advance(r,clock,20)
        assert r.work.open_learning.strategy('numbers','world')

@pytest.mark.parametrize('text',['不要研究这件事','别再研究了','不许处理这个数据','禁止读取这份材料'])
def test_explicit_processing_boundary_remains_hard(tmp_path,text):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        meaning=LiteralSpanInterpreter().interpret(text)
        assert meaning.kind=='DECLINE_DEPTH'
        r.subject.run(interaction(r,'hard',meaning.kind,'numbers'))
        assert depth_boundary(r.store,'observer','world','numbers',('PUBLIC',),purpose='COGNITION')[0]


def test_subject_pause_reconsidered_without_removing_interest(tmp_path):
    clock=VirtualClock();path=tmp_path/'self.db'
    with open_runtime(path,clock) as r:
        root=source(r,'own-project',{'project':'a public creative opportunity'})
        for i in range(6):
            pending=cue(r,'pending-'+str(i),ConcernCue(cue_kind='OPEN_LOOP',topic_key='project-'+str(i),motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE',)),parents=(root,))
            r.subject.run(wake(r,'pending-'+str(i),pending))
        interest=cue(r,'interest',ConcernCue(cue_kind='OPEN_LOOP',topic_key='art',motivation_source='CREATIVE_INTEREST',possible_behaviors=('LEARN',)),parents=(root,))
        # C derives load from its own pending intentions, not a user pause command.
        paused=r.subject.run(wake(r,'self-pause',interest))
        assert paused.intention.behavior=='REST' and any(m.source=='CREATIVE_INTEREST' for m in paused.motivations)
        identity=r.identity_id
    with open_runtime(path,clock) as r:
        old=r.subject.pending('world')[0]
        r.subject.transition_intention(old['intention_id'],expected_revision=old['revision'],state='DROPPED')
        resume=r.subject.run(wake(r,'self-review',interest))
        assert resume.intention.behavior=='LEARN' and r.identity_id==identity
        assert r.subject.result(r.store.one('subject_cycles',paused.cycle_id)).intention.behavior=='REST'


def test_delivery_silence_cannot_remove_older_hard_processing_boundary(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        r.subject.run(interaction(r,'hard','DECLINE_DEPTH','numbers'))
        r.subject.run(interaction(r,'delivery','DECLINE_DELIVERY','numbers'))
        assert depth_boundary(r.store,'observer','world','numbers',('PUBLIC',),purpose='COGNITION')[0]
        assert LiteralSpanInterpreter().interpret('先不聊，也不要研究了').kind=='DECLINE_DEPTH'


def test_delivery_refusal_preserves_social_desire_but_withholds_expression(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        root=source(r,'shared-interest',{'project':'a public conversation opportunity'})
        mid=cue(r,'social',ConcernCue(cue_kind='DISCOVERY',topic_key='shared-project',motivation_source='RELATIONSHIP',possible_behaviors=('SOCIALIZE','WATCH'),availability='AVAILABLE'),parents=(root,))
        r.subject.run(interaction(r,'quiet','DECLINE_DELIVERY','shared-project'))
        c=r.subject.run(wake(r,'own-social-desire',mid))
        assert c.intention.kind=='SOCIAL_INTERACTION' and c.intention.behavior=='SOCIALIZE'
        assert not c.context_fit.allow_delivery and c.social_proposal.act=='STAY_SILENT'
        assert not r.store.all('actions')


def test_repeated_delivery_records_cannot_crowd_out_processing_scope(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        for i in range(34):r.subject.run(interaction(r,'quiet-'+str(i),'DECLINE_DELIVERY','numbers'))
        assert not depth_boundary(r.store,'observer','world','numbers',('PUBLIC',),purpose='COGNITION')[0]


def test_conversation_reopen_cannot_lift_explicit_processing_prohibition(tmp_path):
    with open_runtime(tmp_path/'self.db',VirtualClock()) as r:
        r.subject.run(interaction(r,'hard','DECLINE_DEPTH','numbers'))
        meaning=LiteralSpanInterpreter().interpret('可以再讨论了')
        r.subject.run(interaction(r,'talk-again',meaning.kind,'numbers'))
        assert depth_boundary(r.store,'observer','world','numbers',('PUBLIC',),purpose='COGNITION')[0]
