import sys,json,pathlib
bundle=pathlib.Path('/tmp/nc162');repo=pathlib.Path('/workspace/nana-unified-release')
assert pathlib.Path(sys.prefix).resolve()==bundle/'.venv'
manifest=json.loads((bundle/'runtime.json').read_text());assert manifest['source_commit']=='c162df34c832fb9241f12529e0d02e3cdec5b101'
sys.dont_write_bytecode=True
sys.path.insert(0,str(bundle/'src'))
import nana_core
assert pathlib.Path(nana_core.__file__).resolve().is_relative_to(bundle/'src')
sys.path.extend(['/workspace/nana-test-env/lib/python3.12/site-packages',str(repo)])
import pytest
config=pathlib.Path('/tmp/nana-installed-policy.ini');config.write_text('[pytest]\naddopts =\n')
files=['open_life/test_learning_renewal.py','open_life/test_long_goals.py','open_autonomy/test_delivery.py','open_autonomy/test_planning.py']
code=pytest.main(['-q','-c',str(config),'--rootdir',str(repo),'--basetemp=/tmp/nana-c162-installed-tests-fixed',*[str(repo/'tests'/p) for p in files]])
from nana_core.continuity.subject.policy import Situation,appraise,motivate,decide
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,OpportunityAssessment
for behavior in ('REST','WATCH','DO_NOTHING','STAY_SILENT','WITHDRAW','IGNORE','DEFER'):
 event=SubjectInput(source_key='synthetic.installed.quiet.'+behavior,kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-person',scope='lab',observed_at_us=1)
 situation=Situation(scope='lab',memory_ids=('synthetic.source',),project_ids=(),commitment_ids=(),due_commitment_ids=(),adopted_interests=(),unresolved_interest=None,familiar=False,allowed_methods=(),lesson_ids=(),lesson_record_ids=(),support_record_ids=(),pending_count=0,idle=True,cue=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CURIOSITY',topic_key='quiet.choice',possible_behaviors=(behavior,),cognitive_load='HIGH',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED')))
 appraisal=appraise(event,situation);choice=decide(event,situation,appraisal,motivate(event,situation,appraisal))
 assert choice[2].behavior==behavior and choice[2].kind=='NO_ACTION'
loaded=[pathlib.Path(m.__file__).resolve() for name,m in sys.modules.items() if (name=='nana_core' or name.startswith('nana_core.')) and getattr(m,'__file__',None)]
assert all(p.is_relative_to(bundle/'src') for p in loaded)
report={'source_commit':manifest['source_commit'],'execution':'INSTALLED_BUNDLE_PYTHON_AND_CORE_WITH_EXTERNAL_EXISTING_PYTEST_FIXTURES','pytest_exit':code,'installed_pure_quiet_judgments':7,'all_loaded_core_modules_from_bundle':True,'core_modules':len(loaded),'real_model_calls':0,'real_social_sends':0,'production_changed':False,'original_tests':files}
pathlib.Path('/tmp/nana-c162-installed-policy.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(code)
