import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.open_agency.code_skills import CodeSkillService,CodeSpec,FixtureCodeProposer,static_check
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.records import RecordService
from .helpers import *

def skill_need(r):
    c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',topic_key='decimal-transform',possible_behaviors=('SEEK_CAPABILITY',))
    mid=capture(r,'skill-need',c.model_dump_json(),predicate='concern.skill-need')
    send(r,'skill-need',(mid,));cycle=r.step()['cycle']
    return mid,cycle

def test_generated_python_fails_repairs_sandbox_tests_reviews_packages_and_retires(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        mid,cycle=skill_need(r);svc=CodeSkillService(r.store,r.authority);spec=CodeSpec(name='decimal-total',revision=1,purpose='Preserve fractional precision in a local data transform',task='FRACTIONAL_TOTAL')
        case=LearningCase(case_id='new-case',context='independent-test',data=[.25,.5],expected=.75)
        generated=svc.propose(cycle,spec,FixtureCodeProposer());failed=svc.test(generated,(case,))
        assert RecordService(r.store).read(failed)['payload']['state']=='REJECTED'
        fixed=svc.propose(cycle,spec.model_copy(update={'revision':2}),FixtureCodeProposer(),diagnostic='Fractional precision was lost')
        tested=svc.test(fixed,(case,LearningCase(case_id='transfer',context='different',data=[1.5,3],expected=4.5)))
        digest_source=RecordService(r.store).read(tested)['payload']['source_digest']
        active=svc.review(tested,authority=r.authority,expected_digest=digest_source)
        assert svc.invoke(active,[2.25,4])==6.25
        assert svc.package(active,tmp_path/'candidate')['source_digest']==digest_source
        assert not r.store.all('grants')
        retired=svc.retire(active,authority=r.authority)
        with pytest.raises(CoreError):svc.invoke(active,[1,2])
        assert RecordService(r.store).read(retired)['payload']['state']=='RETIRED'
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError):RecordService(r.store).read(retired)

def test_untrusted_import_or_reflection_cannot_become_a_skill():
    for code in ('import os\ndef transform(data): return os.environ', 'def transform(data):\n return data.__class__', 'def transform(data):\n return open("/etc/passwd").read()'):
        with pytest.raises(CoreError):static_check(code)

def test_copied_active_skill_record_does_not_recreate_local_execution_authority(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        _,cycle=skill_need(r);svc=CodeSkillService(r.store,r.authority);spec=CodeSpec(name='total',revision=1,purpose='A local precision task',task='FRACTIONAL_TOTAL')
        generated=svc.propose(cycle,spec,FixtureCodeProposer(),diagnostic='preserve fractions')
        tested=svc.test(generated,(LearningCase(case_id='check',context='test',data=[.25,.5],expected=.75),))
        sha=RecordService(r.store).read(tested)['payload']['source_digest'];active=svc.review(tested,authority=r.authority,expected_digest=sha)
        other=CodeSkillService(r.store,r.authority)
        with pytest.raises(CoreError,match='CURRENT_REALM_REVIEW_REQUIRED'):other.invoke(active,[1,2])
