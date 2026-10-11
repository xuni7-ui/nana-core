from pathlib import Path
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError,Invocation
from nana_core.actions import ActionKernel,OperatorAuthority
from nana_core.fake_world import FakeWorld
from nana_core.storage import Store
from nana_core.semantic.contracts import Endpoint
from nana_core.semantic.selection import ModelCapabilities,ModelSelectionPolicy,TaskRequirements
from nana_core.phase3.engineering import EngineeringPreparationPort,EngineeringTask


def endpoint(alias,local=True):return Endpoint(alias=alias,base_url='http://127.0.0.1:9191/v1' if local else 'https://development.example.invalid/v1',model=alias+'-model',account_scope='local_offline' if local else 'development',funding='local_offline' if local else 'existing_quota',service_kind='real_model',credential_env=None if local else 'NANA_S5_DEV_SELECTION_FIXTURE')
def metadata(e,cost='free'):return ModelCapabilities(alias=e.alias,model_id=e.model,provider='synthetic-selection-fixture',service_kind=e.service_kind,
    context_limit=8000,tool_support=('reading',),privacy_class='local_only' if e.account_scope=='local_offline' else 'development_remote',
    cost_class=cost,latency_class='normal',allowed_task_classes=('reading',))


def test_selection_respects_endpoint_privacy_tasks_tools_cost_and_no_invocation():
    local,remote=endpoint('local'),endpoint('remote',False);policy=ModelSelectionPolicy()
    req=TaskRequirements(task_class='reading',context_tokens=1000,tools=('reading',))
    assert policy.select(req,[local,remote],[metadata(local),metadata(remote)])==local
    for blocked in (req.model_copy(update={'context_tokens':9000}),req.model_copy(update={'task_class':'engineering'}),req.model_copy(update={'tools':('contact',)})):
        with pytest.raises(CoreError,match='MODEL_SELECTION_BLOCKED'):policy.select(blocked,[local],[metadata(local)])
    with pytest.raises(CoreError,match='MODEL_SELECTION_BLOCKED'):policy.select(req,[remote],[metadata(remote)])
    with pytest.raises(CoreError,match='MODEL_SELECTION_BLOCKED'):policy.select(req,[],[metadata(local)])
    with pytest.raises(CoreError,match='MODEL_SELECTION_BLOCKED'):policy.select(req,[local],[metadata(local,'low')])
    with pytest.raises(CoreError,match='MODEL_METADATA_BINDING_MISMATCH'):policy.select(req,[local],[metadata(local).model_copy(update={'model_id':'other'})])
    with pytest.raises(CoreError,match='MODEL_PRIVACY_METADATA_MISMATCH'):policy.select(req,[remote],[metadata(remote).model_copy(update={'privacy_class':'local_only'})])


@pytest.mark.parametrize('operation',['inspect_repository','read_file','patch_file','run_tests','inspect_diff','create_commit'])
def test_bridge_integrated_fixture_prepares_only_no_execution(tmp_path,operation):
    workspace=tmp_path/'isolated';workspace.mkdir()
    port=EngineeringPreparationPort(workspace,('src/demo.py','tests/test_demo.py'),{'unit':('python','-m','pytest','tests/test_demo.py')})
    task=EngineeringTask(operation=operation,path='src/demo.py' if operation in {'read_file','patch_file'} else None,
        new_content='print("synthetic")' if operation=='patch_file' else None,test_id='unit' if operation=='run_tests' else None,
        branch='dev/synthetic',commit_message='Synthetic preview' if operation=='create_commit' else None)
    result=port.prepare(task)
    assert result['bridge_task_spec'].test_command is None
    assert result['execution']=='NOT_ENABLED' and result['core_authorization']=='BLOCKED_UNKNOWN_CAPABILITY'
    assert list(workspace.iterdir())==[]
    inv=Invocation(action_id='synthetic',attempt_id='synthetic',capability=result['capability'],resource='engineering://synthetic',args={},args_hash='synthetic',idempotency_key='synthetic')
    with pytest.raises(CoreError,match='NOT_ENABLED'):port.execute(inv)
    with pytest.raises(CoreError,match='NO_ENGINEERING_EXECUTION_EVIDENCE'):port.verify(inv)


@pytest.mark.parametrize('path',['../outside','/etc/passwd','.env','src/secrets.py','src/nana_core/runtime.py','src/not_allowed.py'])
def test_engineering_sensitive_and_outside_paths_are_denied(tmp_path,path):
    port=EngineeringPreparationPort(tmp_path,('src/demo.py',),{})
    with pytest.raises(CoreError):port.prepare(EngineeringTask(operation='read_file',path=path,branch='dev/synthetic'))


def test_engineering_live_core_symlink_shell_and_main_are_denied(tmp_path):
    with pytest.raises(CoreError,match='LIVE_CORE'):EngineeringPreparationPort(Path('src/nana_core').resolve().parents[1],('demo.py',),{})
    (tmp_path/'link').symlink_to(tmp_path/'inside')
    with pytest.raises(CoreError,match='SYMLINK'):EngineeringPreparationPort(tmp_path,('link/demo.py',),{})
    with pytest.raises(CoreError,match='TEST_TARGET'):EngineeringPreparationPort(tmp_path,('demo.py',),{'bad':('sh','-c','true')})
    with pytest.raises(ValidationError):EngineeringTask(operation='create_commit',branch='main',commit_message='No')


def test_engineering_unknown_capability_cannot_obtain_core_action(tmp_path):
    world=FakeWorld(tmp_path/'world.db')
    try:
        with Store(tmp_path/'core.db') as store:
            kernel=ActionKernel(store,world,OperatorAuthority())
            with pytest.raises(CoreError,match='UNKNOWN_CAPABILITY'):
                kernel.propose('engineering.patch_file','engineering://synthetic',{'path':'src/demo.py'})
            assert store.all('actions')==store.all('grants')==[]
            assert world.counts()['effects']==0
    finally:world.close()
