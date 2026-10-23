import json
import pytest
from nana_core.continuity.open_agency.learning import LearningSpec,LearningCase,LearningService
from nana_core.continuity.open_agency.code_skills import CodeSkillService,CodeSpec,CodeCandidate
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.contracts import CoreError
from tests.open_autonomy.helpers import fresh,capture,send
from tests.open_autonomy.test_learning import start_learning


def test_actual_noisy_heldout_failure_revised_problem_transfer_and_counterexample(owned_root):
    def case(key,data,expected,context='project'):
        return LearningCase(case_id=key,context=context,data=data,expected=expected)
    a=LearningSpec(learning_key='learn.noisy-a',domain='controlled-text',baseline_method='IDENTITY',hypotheses=('SPLIT_SPACE',),practice=(case('a-practice','one two',['one','two']),),evaluation=(case('a-heldout','three\tfour',['three','four']),case('a-noise','five six',['five','six'])),transfer=(case('a-transfer','new\nline',['new','line'],'transcript'),))
    b=LearningSpec(learning_key='learn.noisy-b',domain='controlled-text',baseline_method='SPLIT_SPACE',hypotheses=('UNICODE_WORDS',),practice=(case('b-practice','seven\teight',['seven','eight']),),evaluation=(case('b-heldout','nine\nten',['nine','ten']),),transfer=(case('b-transfer','Ａ\u3000Ｂ',['A','B'],'unicode-report'),))
    with fresh(owned_root/'s.db') as r:
        service=LearningService(r.store,r.authority,(a,b),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=service
        start_learning(r,a,'noisy-a')
        first=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();body=RecordService(r.store).read(first['record_id'])['payload']
        assert first['state']=='BLOCKED' and body['results']['PRACTICE']['all_passed']
        assert body['results']['EVALUATE']['passed']==1 and not body['results']['TRANSFER']['all_passed']
        assert not r.store.all('lessons')
        start_learning(r,b,'noisy-b')
        lesson=r.store.all('lessons')[0];assert lesson['state']=='ACTIVE' and service.strategy('controlled-text','lab')[1]=='UNICODE_WORDS'
        counter=(case('literal-counterexample','KEEP  SPACES',['KEEP','','SPACES'],'literal-tokenizer'),)
        assert not service.monitor(lesson['lesson_id'],counter,authority=r.authority)['all_passed']
        assert service.strategy('controlled-text','lab') is None
        assert r.store.one('lessons',lesson['lesson_id'])['state']=='SUSPENDED'
        assert len(r.store.all('lessons'))==1 and not r.store.all('actions')


def test_skill_created_qualified_used_reused_counterexample_suspended_retired(owned_root):
    class Proposer:
        def implement(self,spec,diagnostic=None):return CodeCandidate(source='def transform(data):\n    return data.strip().casefold()\n')
    with fresh(owned_root/'s.db') as r:
        mid=capture(r,'normalizer-gap',ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',topic_key='normalize.gap',possible_behaviors=('SEEK_CAPABILITY',)).model_dump_json(),predicate='concern.normalize.gap')
        send(r,'normalize-gap',(mid,));r.step();cycle=r.subject.result(r.store.all('subject_cycles')[-1]);assert cycle.intention.behavior=='SEEK_CAPABILITY'
        codes=CodeSkillService(r.store,r.authority);spec=CodeSpec(name='controlled-normalizer',revision=1,purpose='Normalize explicit project labels; not literal quotations',task='CONTROLLED_NORMALIZE')
        rid=codes.propose(cycle,spec,Proposer());cases=(LearningCase(case_id='practice',context='labels',data=' One ',expected='one'),LearningCase(case_id='heldout',context='labels',data='\tTwo\n',expected='two'),LearningCase(case_id='transfer',context='feed',data='THREE ',expected='three'))
        tested=codes.test(rid,cases);body=RecordService(r.store).read(tested)['payload'];active=codes.review(tested,authority=r.authority,expected_digest=body['source_digest'])
        assert codes.invoke(active,' Four ' )=='four' and codes.invoke(active,'Five')=='five'
        suspended=codes.monitor(active,(LearningCase(case_id='literal',context='literal-doc',data=' Preserve ',expected=' Preserve '),),authority=r.authority)
        assert RecordService(r.store).read(suspended)['payload']['state']=='SUSPENDED'
        with pytest.raises(CoreError):codes.invoke(active,'Six')
        with pytest.raises(CoreError):codes.invoke(suspended,'Six')
        retired=codes.retire(suspended,authority=r.authority);assert RecordService(r.store).read(retired)['payload']['state']=='RETIRED'
        with pytest.raises(CoreError):codes.revalidate(active,cases,authority=r.authority)
