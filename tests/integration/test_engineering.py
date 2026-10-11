import json,os,signal,subprocess,sys
import pytest
from nana_core.storage import Store,digest
from nana_core.contracts import CoreError,Invocation
from nana_core.integration.engineering_lab import run,initialize,bind

def test_patch_test_verify_commit_and_restart(tmp_path):
    p=tmp_path/'lab';first=run(p);assert first['status']=='PASS' and first['attempts']==8
    second=run(p);assert second['identity']==first['identity'] and second['commit_sha']==first['commit_sha'] and second['attempts']==8
    assert first['model_kind']=='fixture' and first['E12']=='NOT_RUN'

def test_grants_paths_execution_and_failed_tests_block_commit(tmp_path):
    p=tmp_path/'lab';p.mkdir();initialize(p/'workspace')
    with Store(p/'core.db') as s:
        port,k=bind(s,p)
        before=(p/'workspace/settings.py').read_bytes()
        aid=k.propose('file.patch',port.resource,{'path':'settings.py','before_hash':digest(before),'content':'VALUE = 2\n'})
        with pytest.raises(CoreError,match='AUTH_REQUIRED'):k.run(aid)
        assert (p/'workspace/settings.py').read_bytes()==before and not s.all('attempts')
        with pytest.raises(CoreError,match='PATH'):k.propose('file.read',port.resource,{'path':'../secret'})
        with pytest.raises(CoreError,match='EXECUTABLE_PATCH'):k.propose('file.patch',port.resource,{'path':'settings.py','before_hash':digest(before),'content':'import os\n'})
        with pytest.raises(CoreError,match='KERNEL_ROUTED'):port.execute(Invocation(action_id='fake',attempt_id='fake',capability='file.patch',resource=port.resource,args={},args_hash=digest({}),idempotency_key='fake'))
        port.close()
    with Store(p/'core.db') as s:
        port,k=bind(s,p,True)
        test=k.propose('tests.run',port.resource,{'test_id':'literal'});assert k.run(test)=='FAILED_EFFECT'
        parent=port._git('rev-parse','HEAD')
        commit=k.propose('git.commit',port.resource,{'message':'No passing test','test_action_id':test,'parent_sha':parent})
        assert k.run(commit)=='UNKNOWN' and port._git('rev-parse','HEAD')==parent
        assert k.run(commit)=='UNKNOWN' and len([a for a in s.all('attempts') if a['action_id']==commit and a['kind']=='EXECUTE'])==1
        port.close()

def test_real_sigkill_after_patch_recovers_verify_only(tmp_path):
    p=tmp_path/'crash';env=dict(os.environ);env['PYTHONPATH']=str(__import__('pathlib').Path('src').resolve())
    child=subprocess.run([sys.executable,'-m','nana_core.integration.engineering_lab',str(p),'--kill-after-patch'],env=env,capture_output=True)
    assert child.returncode==-signal.SIGKILL
    with Store(p/'core.db') as s:
        port,k=bind(s,p);identity=s.identity
        recovery=k.recover();assert list(recovery.values())==['SUCCEEDED']
        assert len([a for a in s.all('attempts') if a['kind']=='EXECUTE'])==1
        port.close()
    result=run(p);assert result['status']=='PASS' and result['identity']==identity

def test_read_inspect_diff_independent_verify_and_budget(tmp_path):
    p=tmp_path/'read';p.mkdir();initialize(p/'workspace')
    with Store(p/'core.db') as s:
        port,k=bind(s,p,True)
        for cap,args in [('repo.inspect',{}),('file.read',{'path':'settings.py'}),('git.diff',{})]:
            aid=k.propose(cap,port.resource,args);assert k.run(aid)=='SUCCEEDED'
        assert len(s.all('attempts'))==6 and s.one('budgets','write_attempts')['spent']==0
        assert s.one('budgets','external_requests')['spent']==6
        port.close()
