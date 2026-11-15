"""Unrelated checked failures do not settle or erase this concern's need."""
from nana_core.storage import digest
from nana_core.continuity.learning import ExperienceService,ExperienceInput
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.experience_need import project_need
from .test_settled_need_choice import settled


def test_same_domain_independent_failures_do_not_crowd_current_gap(settled):
    app,mid,cue=settled;r=app.runtime
    def need(bound=True):
        return project_need(r.store,'owned-document',scope='project-work',privacy_classes=r.config.privacy_classes,
            **({'source_memory_ids':(mid,)} if bound else {}))
    before=need();assert before.state=='SETTLED'
    service=ExperienceService(r.store,r.authority);unrelated=[]
    for i in range(40):
        result=capture(r,'unrelated-checked-gap-'+str(i),{'data':{'SYNTHETIC_actual':i}},kind='SYSTEM_VERIFICATION')
        verification=service.verify_structured_result(result,digest({'SYNTHETIC_expected':i}),r.authority)
        eid=service.record(ExperienceInput(context_memory_ids=(result,),scope='project-work',task_class='owned-document',
            decision='Synthetic independent result differs from its expected digest',result_memory_id=result,verification_memory_id=verification))
        assert r.store.one('experiences',eid)['outcome']=='FAILURE'
        unrelated.append(result)
    assert need(False).state=='UNKNOWN'  # original broad horizon is still32
    assert project_need(r.store,'owned-document',scope='project-work',privacy_classes=r.config.privacy_classes,
        source_memory_ids=tuple(unrelated)).state=='UNKNOWN'  # forty genuinely matching gaps still overflow
    count=r.store.db.execute('SELECT count(*) FROM events').fetchone()[0]
    after=need();assert after.state=='SETTLED' and after.source_record_ids==before.source_record_ids
    assert r.store.db.execute('SELECT count(*) FROM events').fetchone()[0]==count
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.causal-need-after-unrelated-failures',kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),task_class='owned-document')
    cycle=r.subject.run(event)
    assert cycle.experience_need.state=='SETTLED' and cycle.intention.behavior=='WATCH'
    assert not r.store.all('cognitive_requests')
    failure=r.store.db.execute('SELECT result_memory_id FROM experiences WHERE record_id=?',(before.source_record_ids[0],)).fetchone()[0]
    app.forget(failure)
    assert need().state=='UNKNOWN'


def test_other_same_domain_lesson_reviews_do_not_hide_checked_current_need(settled):
    from nana_core.continuity.subject.opportunities import ConcernCue
    from nana_core.continuity.world_loop.learning import EpisodeLearning
    app,mid,cue=settled;r=app.runtime
    def need():
        return project_need(r.store,'owned-document',scope='project-work',privacy_classes=r.config.privacy_classes,source_memory_ids=(mid,))
    before=need();assert before.state=='SETTLED'
    service=r.work.open_learning
    old=next(s for s in service.specs.values() if s.domain=='owned-document')
    key='learn.unrelated-document-research'
    spec=old.model_copy(update={'learning_key':key});service.specs[key]=spec
    independent=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CURIOSITY',topic_key='unrelated-document-study',program_id=key,possible_behaviors=('LEARN',))
    other=capture(r,'unrelated-document-study',independent.model_dump(mode='json'),predicate='concern.unrelated-document-study')
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.unrelated-document-study',kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(other,))
    cycle=r.subject.run(event);assert cycle.intention.behavior=='LEARN'
    r.work.after_cycle(cycle,event)
    job=r.store.db.execute("SELECT j.* FROM jobs j JOIN continuity_records c ON j.record_id=c.record_id WHERE c.target_id=?",(key,)).fetchone()
    assert job
    for _ in range(20):
        if r.store.one('jobs',job['job_id'])['state']=='DONE':break
        service.slice()
    completed=r.store.one('jobs',job['job_id']);assert completed['state']=='DONE'
    lesson=r.subject.records.read(completed['record_id'])['payload']['lesson_id']
    reviewer=EpisodeLearning(r.store,r.authority,scopes=r.config.scopes,privacy_classes=r.config.privacy_classes)
    # Repeated independently evaluated episodes are crowding, not a claim of
    # forty novel capabilities or additional learning qualification.
    for i in range(40):
        case=spec.transfer[0].model_copy(update={'case_id':'unrelated-review-'+str(i),'context':'unrelated-context-'+str(i)})
        source=capture(r,'unrelated-checked-review-'+str(i),{'strategy_episode':{'episode_key':'unrelated-review-'+str(i),
            'lesson_id':lesson,'case':case.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
        aid=reviewer.assess(lesson,source,authority=r.authority)
        assert r.store.one('strategy_assessments',aid)['verdict']=='SUCCESS'
    after=need();assert after.state=='SETTLED' and after.source_record_ids==before.source_record_ids

    own_lesson=r.store.db.execute('SELECT lesson_id FROM strategy_assessments WHERE record_id IN ('+
        ','.join('?' for _ in before.source_record_ids)+')',before.source_record_ids).fetchone()[0]
    contrary=spec.transfer[0].model_copy(update={'case_id':'current-counter','context':'changed-current-expectation','expected':{'different_required_workflow':True}})
    counter=capture(r,'current-checked-counter',{'strategy_episode':{'episode_key':'current-counter','lesson_id':own_lesson,
        'case':contrary.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
    checked=reviewer.assess(own_lesson,counter,authority=r.authority)
    assert r.store.one('strategy_assessments',checked)['verdict']=='COUNTEREXAMPLE'
    assert need().state=='OPEN'  # the unrelated successes cannot hide this actual counterexample
    parent=mid
    for i in range(130):
        parent=capture(r,'bounded-episode-ancestry-'+str(i),{'SYNTHETIC':'metadata link'},kind='MODEL_DERIVATION',parents=(parent,))
    ambiguous=capture(r,'ancestry-requires-review',{'strategy_episode':{'episode_key':'bounded-ancestry-review','lesson_id':lesson,
        'case':spec.transfer[0].model_dump(mode='json')}},kind='SYSTEM_VERIFICATION',parents=(parent,))
    reviewer.assess(lesson,ambiguous,authority=r.authority)
    assert need().state=='UNKNOWN'  # bounded metadata must not silently discard an ambiguous newer episode
    app.forget(ambiguous)
    assert need().state=='OPEN'
    for i in range(33):
        source=capture(r,'current-counter-series-'+str(i),{'strategy_episode':{'episode_key':'current-counter-'+str(i),
            'lesson_id':own_lesson,'case':contrary.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
        reviewer.assess(own_lesson,source,authority=r.authority)
    assert need().state=='UNKNOWN'  # thirty-three matching reviews still exceed the original horizon
