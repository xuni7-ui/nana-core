import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import pytest
from pydantic import ValidationError
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CAPABILITIES, CoreError, GrantSpec, Invocation, VERIFY_CAPABILITY
from nana_core.development.file_source import FileSourcePort, SourceBinding, SourceDocument
from nana_core.development.lab import run
from nana_core.fake_world import FakeWorld
from nana_core.migration.routing import CapabilityRouter
from nana_core.storage import Store, digest
from .proof import record


@pytest.fixture
def environment(tmp_path):
    root = tmp_path/'sources';root.mkdir()
    source = 'source://synthetic/dev/book'
    document = SourceDocument(synthetic_only=True,text='An invented paper garden.',locator='synthetic page 5, paragraph 2')
    raw = document.model_dump_json().encode();(root/'book.json').write_bytes(raw)
    binding = SourceBinding(synthetic_only=True,relative_path='book.json',blob_sha256=digest(raw))
    clock, authority = ManualClock(),OperatorAuthority()
    with Store(tmp_path/'core.db',clock) as store:
        world=FakeWorld(tmp_path/'world.db')
        port=FileSourcePort(root,{source:binding},world)
        router=CapabilityRouter(store,{c:world if c=='reading.card.create' else port for c in CAPABILITIES},authority)
        router.select_owner('core_simulator',authority)
        kernel=ActionKernel(store,router.bind('core_simulator',authority),authority)
        kernel.set_budgets({'external_requests':30,'cost_micro_units':30,'write_attempts':0},authority)
        try:yield root,source,port,world,router,kernel,store,authority,clock
        finally:port.close();world.close()


def grant(env):
    root,source,port,world,router,kernel,store,authority,clock=env
    return kernel.grant(GrantSpec(capabilities=('reading.source.read','reading.source.locate',VERIFY_CAPABILITY),
        resources=(source,),not_before_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+10_000_000),authority)


def test_real_read_and_independent_reread_do_not_modify_source(environment):
    root,source,port,world,router,kernel,store,authority,clock=environment
    grant(environment)
    before=(root/'book.json').read_bytes()
    for capability in ('reading.source.read','reading.source.locate'):
        action=kernel.propose(capability,source,{'source_id':source},effect_slot=capability)
        assert kernel.run(action)=='SUCCEEDED'
        result=json.loads(store.one('actions',action)['result_json'])
        assert result['source_blob_sha256']==digest(before)
        assert result['source_adapter']=='pinned_synthetic_file'
        assert kernel.run(action)=='SUCCEEDED'
    assert port.counts=={'execute_reads':2,'verify_reads':2}
    assert (root/'book.json').read_bytes()==before
    assert world.counts()['effects']==0
    assert store.one('budgets','external_requests')['spent']==4


@pytest.mark.parametrize('reason',['no_grant','expired','revoked','empty_budget','wrong_owner'])
def test_denied_attempt_never_reads_source(environment,reason):
    root,source,port,world,router,kernel,store,authority,clock=environment
    if reason!='no_grant':
        grant_id=grant(environment)
    if reason=='expired':clock.advance(11_000_000)
    if reason=='revoked':kernel.revoke(grant_id,authority)
    if reason=='empty_budget':kernel.set_budgets({'external_requests':0,'cost_micro_units':0,'write_attempts':0},authority)
    if reason=='wrong_owner':kernel=ActionKernel(store,router.bind('legacy_simulator',authority),authority)
    action=kernel.propose('reading.source.read',source,{'source_id':source})
    if reason=='wrong_owner':assert kernel.run(action)=='UNKNOWN'
    else:
        with pytest.raises(CoreError):kernel.run(action)
    assert port.counts=={'execute_reads':0,'verify_reads':0}
    assert world.counts()['execute_calls']==0


@pytest.mark.parametrize('path',['../outside.json','/absolute.json','a/../b.json','./book.json','a//b.json','.',r'a\b.json'])
def test_no_model_path_navigation(path):
    with pytest.raises(ValidationError):SourceBinding(synthetic_only=True,relative_path=path,blob_sha256='a'*64)


@pytest.mark.parametrize('kind',['symlink','nested_symlink','fifo','oversize','invalid_document','changed_blob'])
def test_untrusted_files_rejected_without_receipt(tmp_path,kind):
    root=tmp_path/'sources';root.mkdir();file=root/'book.json'
    good=SourceDocument(synthetic_only=True,text='Synthetic.',locator='page 1').model_dump_json().encode()
    raw=good
    relative='book.json'
    if kind=='symlink':
        outside=tmp_path/'outside.json';outside.write_bytes(good);file.symlink_to(outside)
    elif kind=='nested_symlink':
        outside=tmp_path/'outside';outside.mkdir();(outside/'book.json').write_bytes(good);(root/'nested').symlink_to(outside,target_is_directory=True);relative='nested/book.json'
    elif kind=='fifo':os.mkfifo(file)
    elif kind=='oversize':raw=b'x'*65_537;file.write_bytes(raw)
    elif kind=='invalid_document':raw=b'{"text":"not declared synthetic"}';file.write_bytes(raw)
    else:file.write_bytes(good+b' ')
    world=FakeWorld(tmp_path/'world.db')
    port=FileSourcePort(root,{'source://synthetic/dev':SourceBinding(synthetic_only=True,relative_path=relative,blob_sha256=digest(raw))},world)
    args={'source_id':'source://synthetic/dev'}
    inv=Invocation(action_id='test',attempt_id='test',capability='reading.source.read',resource=args['source_id'],args=args,args_hash=digest(args),idempotency_key='test')
    try:
        with pytest.raises(CoreError):port.execute(inv)
        assert world.db.execute('SELECT count(*) FROM operations').fetchone()[0]==0
    finally:port.close();world.close()


def test_source_change_after_receipt_stays_unknown_without_redispatch(environment):
    root,source,port,world,router,kernel,store,authority,clock=environment
    grant(environment)
    action=kernel.propose('reading.source.read',source,{'source_id':source});kernel.prepare(action);kernel.dispatch(action)
    original=(root/'book.json').read_bytes();(root/'book.json').write_bytes(original+b' ')
    assert kernel.verify(action)=='UNKNOWN'
    assert kernel.run(action)=='UNKNOWN'
    assert port.counts['execute_reads']==1
    (root/'book.json').write_bytes(original)
    assert kernel.run(action)=='SUCCEEDED'
    assert port.counts['execute_reads']==1


def test_missing_read_journal_is_inconclusive(environment):
    root,source,port,world,router,kernel,store,authority,clock=environment
    grant(environment);action=kernel.propose('reading.source.read',source,{'source_id':source});kernel.prepare(action)
    def interrupted(point):
        if point=='before_call':raise RuntimeError('synthetic interruption')
    with pytest.raises(RuntimeError):kernel.dispatch(action,fault=interrupted)
    assert kernel.recover()[action]=='UNKNOWN'
    assert port.counts['execute_reads']==0
    assert kernel.run(action)=='UNKNOWN'


def test_restart_after_real_sigkill_preserves_identity_and_read_receipt(tmp_path):
    script='''
import os,signal,sys,json
from pathlib import Path
from nana_core.development.lab import run
from nana_core.actions import ActionKernel,OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CAPABILITIES
from nana_core.development.file_source import FileSourcePort,SourceBinding
from nana_core.development.lab import SOURCE
from nana_core.fake_world import FakeWorld
from nana_core.migration.routing import CapabilityRouter
from nana_core.storage import Store,digest
root=Path(sys.argv[1]);run(root)
authority=OperatorAuthority();store=Store(root/'nana.db',ManualClock());world=FakeWorld(root/'world.db')
file=root/'synthetic_sources'/'paper.json'
port=FileSourcePort(file.parent,{SOURCE:SourceBinding(synthetic_only=True,relative_path=file.name,blob_sha256=digest(file.read_bytes()))},world)
router=CapabilityRouter(store,{c:world if c=='reading.card.create' else port for c in CAPABILITIES},authority)
kernel=ActionKernel(store,router.bind('core_simulator',authority),authority)
action=kernel.propose('reading.source.read',SOURCE,{'source_id':SOURCE});kernel.prepare(action)
print(json.dumps({'identity':store.identity,'action':action}),flush=True)
def kill(point):
 if point=='after_effect':os.kill(os.getpid(),signal.SIGKILL)
kernel.dispatch(action,fault=kill)
'''
    root=tmp_path/'lab'
    env={'PATH':os.environ.get('PATH',''),'PYTHONPATH':str(Path(__file__).resolve().parents[2]/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    child=subprocess.run([sys.executable,'-c',script,str(root)],env=env,capture_output=True,text=True,timeout=15)
    assert child.returncode==-signal.SIGKILL,child.stderr
    marker=json.loads(child.stdout)
    from nana_core.development.lab import SOURCE
    with Store(root/'nana.db',ManualClock()) as store:
        world=FakeWorld(root/'world.db');file=root/'synthetic_sources'/'paper.json'
        port=FileSourcePort(file.parent,{SOURCE:SourceBinding(synthetic_only=True,relative_path=file.name,blob_sha256=digest(file.read_bytes()))},world)
        authority=OperatorAuthority();router=CapabilityRouter(store,{c:world if c=='reading.card.create' else port for c in CAPABILITIES},authority)
        kernel=ActionKernel(store,router.bind('core_simulator',authority),authority)
        try:
            assert store.identity==marker['identity']
            recovered=kernel.recover()[marker['action']]
            assert recovered=='SUCCEEDED'
            assert port.counts=={'execute_reads':0,'verify_reads':1}
            assert world.counts()['effects']==2
            record('real_file_sigkill_recovery',{'returncode':child.returncode,'identity_equal':store.identity==marker['identity'],
                'action_id':marker['action'],'recovered_state':recovered,'file_reads_after_recovery':port.counts,
                'notebook_effects':world.counts()['effects'],'scope':'actual child SIGKILL after durable file-read receipt; verify-only restart'})
        finally:port.close();world.close()


def test_lab_reopens_identity_and_executes_learned_real_file_read(tmp_path):
    report=run(tmp_path/'lab')
    assert report['engineering_gate']=='PASS' and all(report['checks'].values())
    assert report['file_reads']=={'execute_reads':3,'verify_reads':3}
    assert report['real_model_attempts']==0 and report['E12']=='NOT_RUN'
    assert report['phases'][0]['plan']['applied_strategies']==[]
    assert report['phases'][1]['plan']['applied_strategies']
    assert report['phases'][1]['world_counts']=={'effects':2,'execute_calls':5,'locate_calls':1,'verify_calls':5}


def test_independent_location_is_not_mislabeled_as_learning(tmp_path,monkeypatch):
    from nana_core.development import lab
    from nana_core.contracts import PlanProposal,StepProposal
    class IndependentlyLocates:
        descriptor='engineering-independent-location-fixture'
        def propose(self,req):
            return PlanProposal(purpose='Synthetic independent location.',steps=(
                StepProposal(capability='reading.source.read',resource=req.source_id),
                StepProposal(capability='reading.source.locate',resource=req.source_id),
                StepProposal(capability='reading.card.create',resource=req.card_resource)))
    monkeypatch.setattr(lab,'FixtureModel',IndependentlyLocates)
    report=run(tmp_path/'lab')
    assert report['phases'][1]['world_counts']['locate_calls']==2
    assert report['experience_effect']['learned_strategy_ids']==[]
    assert report['experience_effect']['gate']=='NOT_DEMONSTRATED'
    assert report['engineering_gate']=='FAIL'
