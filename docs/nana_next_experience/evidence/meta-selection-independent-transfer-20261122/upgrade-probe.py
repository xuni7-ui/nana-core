import json
import sys
from pathlib import Path

from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.open_agency.learning import LearningCase, LearningProblem, LearningService, LearningSpec
from nana_core.continuity.open_life.meta_learning import LearningStrategyLesson, checks, propose, select
from nana_core.continuity.records import RecordService
from nana_core.presence.contracts import RuntimeConfig
from nana_core.presence.runtime import NanaRuntime
from tests.open_autonomy.helpers import fresh
from tests.open_autonomy.test_learning import start_learning

phase, root = sys.argv[1], Path(sys.argv[2])
db, before = root / 'subject/self.db', root / 'old.json'

def spec(domain, key, methods, samples):
    return LearningSpec(learning_key=key, domain=domain, baseline_method='IDENTITY', hypotheses=methods,
        practice=(LearningCase(case_id='practice',context='labels',data=samples[0],expected=samples[0].lower()),),
        evaluation=(LearningCase(case_id='heldout',context='labels',data=samples[1],expected=samples[1].lower()),),
        transfer=(LearningCase(case_id='transfer',context='catalog',data=samples[2],expected=samples[3]),))

class OriginalProposer:
    def __init__(self):
        self.calls = []
    def propose_method(self, problem):
        assert not hasattr(problem, 'evaluation') and not hasattr(problem, 'transfer')
        self.calls.append(problem.learning_key)
        return 'NFKC_CASEFOLD'

source_specs = [
    spec('labels','learn.old-invalid',('CASEFOLD','NFKC_CASEFOLD'),('ALPHA','BETA','ＧＡＭＭＡ','gamma')),
    spec('catalog','learn.old-valid',('NFKC_CASEFOLD','CASEFOLD'),('EPSILON','ZETA','ＥＴＡ','eta')),
]
selected = tuple(LearningProblem.from_spec(value) for value in source_specs)
if phase == 'old':
    with fresh(db) as runtime:
        learner = LearningService(runtime.store,runtime.authority,source_specs,privacy_classes=('PERSONAL',),scopes=('lab',),
            proposer=OriginalProposer())
        runtime.work.open_learning=learner
        experience=ExperienceService(runtime.store,runtime.authority)
        ids=[]
        for value in source_specs:
            start_learning(runtime,value,value.domain)
            row=runtime.store.db.execute('SELECT lesson_id FROM lessons WHERE task_class=?',(value.domain,)).fetchone()
            meta=propose(runtime.store,row[0],authority=runtime.authority)
            assert all(experience.test_lesson(meta).values())
            experience.activate(meta,runtime.authority)
            ids.append(meta)
        methods=[select(runtime.store,value,scope='lab',privacy=('PERSONAL',))[0] for value in selected]
        assert methods==['CASEFOLD','NFKC_CASEFOLD']
        before.write_text(json.dumps({'identity':runtime.identity_id, 'config':runtime.config.model_dump(mode='json'),
            'strategies':ids,'clock_us':runtime.clock.utc_now_us()}))
        print(json.dumps({'old_meta_choices':methods,'old_active_meta_count':len(ids)}))
else:
    old=json.loads(before.read_text())
    config=RuntimeConfig.model_validate_json(json.dumps(old['config']))
    from nana_core.presence.authority import VirtualClock
    clock=VirtualClock(now_us=old['clock_us'])
    with NanaRuntime(db,config,clock=clock) as runtime:
        assert runtime.identity_id==old['identity']
        experience=ExperienceService(runtime.store,runtime.authority)
        n=runtime.store.db.total_changes
        methods=[select(runtime.store,value,scope='lab',privacy=('PERSONAL',))[0] for value in selected]
        assert methods==[None,'NFKC_CASEFOLD'] and runtime.store.db.total_changes==n
        assert [runtime.store.one('lessons',lid)['state'] for lid in old['strategies']]==['ACTIVE','ACTIVE']
        records=RecordService(runtime.store)
        verdicts=[]
        for lid in old['strategies']:
            row=runtime.store.one('lessons',lid)
            rule=LearningStrategyLesson.model_validate(records.read(row['record_id'])['payload']['rule'])
            verdicts.append(checks(records,rule)['independent_selection_experiment'])
        assert verdicts==[False,True]
        future=spec('labels','learn.future',('CASEFOLD','NFKC_CASEFOLD'),('DELTA','ECHO','ＦＯＸＴＲＯＴ','foxtrot'))
        proposer=OriginalProposer()
        learner=LearningService(runtime.store,runtime.authority,(future,),privacy_classes=('PERSONAL',),scopes=('lab',),proposer=proposer)
        runtime.work.open_learning=learner
        start_learning(runtime,future,'future-selection')
        job=runtime.store.db.execute('SELECT * FROM jobs WHERE work_kind=\'LEARNING\' ORDER BY rowid DESC LIMIT 1').fetchone()
        body=RecordService(runtime.store).read(job['record_id'])['payload']
        assert not body.get('learning_strategy_record_id') and proposer.calls==[future.learning_key]
        assert job['state']=='DONE' and body['results']['TRANSFER']['all_passed']
        assert not runtime.store.all('actions') and not runtime.store.all('grants')
        print(json.dumps({'same_subject':True,'new_meta_choices':methods,'selection_write_rows':0,
            'qualified_old_rule_retained':True,'future_method':body['selected_method'],'future_state':job['state'],
            'independent_future_transfer':True,'ordinary_proposer_calls':len(proposer.calls),'external_model_calls':0}))
