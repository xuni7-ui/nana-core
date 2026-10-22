import json
from nana_core.continuity.agency_contracts import GoalReviewRef
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from tests.open_autonomy.helpers import fresh,configure,objective,capture,cue,send

def test_one_ongoing_goal_c_pause_restart_resume_abandon_without_plan_replay(tmp_path):
    path=tmp_path/'s.db';world=tmp_path/'world.fixture.json';obj=objective().model_copy(update={'horizon':'ONGOING','review_after_us':1})
    def review(r,goal,kind,key):
        c=ConcernCue(cue_kind='LOAD_STATE' if kind=='REST' else 'OPEN_LOOP',topic_key='ongoing.review',motivation_source='LONG_TERM_GOAL',possible_behaviors=('WITHDRAW',) if kind=='WITHDRAW' else ('CONTINUE_PROJECT','REST'),cognitive_load='HIGH' if kind=='REST' else 'LOW')
        mid=capture(r,key,c.model_dump_json(),predicate='concern.ongoing.'+key)
        event=SubjectInput(source_key='synthetic.ongoing.'+key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='lab',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=mid,purpose='LIFECYCLE'))
        cycle=r.subject.run(event);r.work.after_cycle(cycle,event);return cycle
    with fresh(path) as r:
        port=configure(r,world,(obj,));port.seed_observation(obj.operators[0].resource,[1.2,2.3]);mid=cue(r,obj);send(r,'ongoing',(mid,));r.step()
        g=r.store.all('goals')[0];identity=r.identity_id;plan=json.loads(g['body_json'])['plan_record_id']
        c=review(r,g,'REST','pause');assert c.intention.behavior=='REST'
        assert r.store.one('goals',g['goal_id'])['state']=='SUSPENDED'
        assert not r.store.all('actions')
    with fresh(path) as r:
        configure(r,world,(obj,));assert r.identity_id==identity
        g=r.store.all('goals')[0];assert g['state']=='SUSPENDED'
        review(r,g,'CONTINUE','resume');g=r.store.one('goals',g['goal_id']);assert g['state']=='ACTIVE' and json.loads(g['body_json'])['plan_record_id']==plan
        review(r,g,'WITHDRAW','abandon');assert r.store.one('goals',g['goal_id'])['state']=='ABANDONED'
        assert len(r.store.all('goals'))==1 and not r.store.all('actions')
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
