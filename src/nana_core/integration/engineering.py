"""Small operator-scoped engineering registry for synthetic disposable git repos.

No arbitrary executable patches/tests yet: file.patch permits literal-assignment
Python data. Fixed trusted runner checks AST, never imports generated code. This
avoids pretending argv allowlisting is an OS filesystem sandbox.
"""
import json,os,sqlite3,subprocess,sys
from pathlib import Path
from types import MappingProxyType
from pydantic import Field
from ..contracts import DTO,CoreError,Receipt,Verification
from ..storage import canonical,digest
from ..phase3.engineering import EngineeringPreparationPort,EngineeringTask
from .engineering_test_runner import literal_values

class RepoArgs(DTO):pass
class FileArgs(DTO):path:str=Field(min_length=1,max_length=128)
class PatchArgs(FileArgs):
    before_hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    content:str=Field(min_length=1,max_length=16384)
class TestArgs(DTO):test_id:str
class CommitArgs(DTO):
    message:str=Field(min_length=1,max_length=128,pattern=r'^[a-zA-Z0-9 .,/_-]+$')
    test_action_id:str
    parent_sha:str=Field(pattern=r'^[a-f0-9]{40}$')

MODELS={'repo.inspect':RepoArgs,'file.read':FileArgs,'file.patch':PatchArgs,'tests.run':TestArgs,'git.diff':RepoArgs,'git.commit':CommitArgs}
WRITE=frozenset({'file.patch','tests.run','git.commit'})

class EngineeringRegistry:
    verify_capability='engineering.action.verify'
    def __init__(self,port):self.port=port;self.definitions=MappingProxyType(MODELS)
    def is_write(self,capability):return capability in WRITE
    def validate(self,capability,resource,args):
        if resource!=self.port.resource:raise CoreError('ENGINEERING_RESOURCE_MISMATCH')
        parsed=MODELS[capability].model_validate(args).model_dump()
        self.port.validate(capability,parsed)
        return parsed

class EngineeringCapabilityPort:
    def __init__(self,store,workspace,journal_path,*,allow_paths,branch,test_contracts):
        self.store=store;self.workspace=Path(workspace).resolve();self.path=Path(journal_path).resolve()
        self.branch=branch;self.allow_paths=tuple(allow_paths);self.test_contracts=dict(test_contracts)
        self.preparation=EngineeringPreparationPort(workspace,allow_paths,{})
        if not branch.startswith('dev/') or self.path==store.path.resolve() or self.workspace==self.path or self.workspace in self.path.parents:
            raise CoreError('ISOLATED_ENGINEERING_REQUIRED')
        marker=self.workspace/'.nana-engineering-fixture.json'
        if marker.is_symlink() or not marker.is_file() or marker.stat().st_size>2048:raise CoreError('SYNTHETIC_WORKSPACE_MARKER_REQUIRED')
        data=json.loads(marker.read_text())
        if data!={'synthetic_only':True,'workspace_id':'synthetic-engineering'}:raise CoreError('SYNTHETIC_WORKSPACE_REQUIRED')
        if not (self.workspace/'.git').is_dir() or (self.workspace/'.git').is_symlink():raise CoreError('DISPOSABLE_GIT_REPO_REQUIRED')
        self.resource='workspace://synthetic/'+digest(str(self.workspace))
        self.db=sqlite3.connect(self.path);self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS receipts(action_id TEXT PRIMARY KEY,idem TEXT UNIQUE,result TEXT)');self.db.commit()
        self._branch_guard()
        for target,expected in self.test_contracts.values():
            self.preparation._path(target)
            if target not in self.allow_paths or not isinstance(expected,dict):raise CoreError('APPROVED_TEST_CONTRACT_REQUIRED')
    def close(self):self.db.close()
    def _env(self):return {'PATH':os.defpath,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0',
        'GIT_AUTHOR_NAME':'Nana synthetic dev','GIT_AUTHOR_EMAIL':'synthetic@example.invalid','GIT_COMMITTER_NAME':'Nana synthetic dev','GIT_COMMITTER_EMAIL':'synthetic@example.invalid'}
    def _git(self,*args):
        try:
            r=subprocess.run(['git','--no-pager','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','commit.gpgsign=false',
                '-c','core.attributesFile=/dev/null','-C',str(self.workspace),*args],env=self._env(),capture_output=True,timeout=10,check=False)
        except subprocess.TimeoutExpired:raise CoreError('ENGINEERING_COMMAND_UNKNOWN') from None
        if len(r.stdout)>65536 or len(r.stderr)>65536:raise CoreError('ENGINEERING_OUTPUT_LIMIT')
        if r.returncode:raise CoreError('ENGINEERING_GIT_FAILED')
        return r.stdout.decode(errors='replace').strip()
    def _branch_guard(self):
        if self._git('branch','--show-current')!=self.branch or not self.branch.startswith('dev/'):raise CoreError('DEVELOPMENT_BRANCH_REQUIRED')
    def _file(self,path):
        self.preparation._path(path)
        if path not in self.allow_paths:raise CoreError('ENGINEERING_PATH_NOT_ALLOWED')
        p=self.workspace/path
        if not p.is_file() or p.stat().st_nlink!=1 or p.stat().st_size>16384:raise CoreError('BOUNDED_REGULAR_DEV_FILE_REQUIRED')
        return p
    def _hash(self):return digest({p:digest(self._file(p).read_bytes()) for p in self.allow_paths})
    def validate(self,cap,args):
        self._branch_guard()
        if cap in {'file.read','file.patch'}:self._file(args['path'])
        if cap=='file.patch':
            try:literal_values(args['content'])
            except Exception:raise CoreError('EXECUTABLE_PATCH_NOT_ENABLED') from None
        if cap=='tests.run' and args['test_id'] not in self.test_contracts:raise CoreError('APPROVED_TEST_REQUIRED')
    def _proof(self,inv,verify=False):
        action=self.store.one('actions',inv.action_id)
        claim=self.store.one('core_meta','migration.route_claim:'+inv.action_id)
        if not action or not claim or action['args_hash']!=digest(inv.args) or action['args_hash']!=inv.args_hash or action['idempotency_key']!=inv.idempotency_key:
            raise CoreError('KERNEL_ROUTED_ACTION_REQUIRED')
        if (action['capability'],action['resource'],action['attempt_id'])!=(inv.capability,inv.resource,inv.attempt_id):raise CoreError('ROUTE_INVOCATION_MISMATCH')
        if inv.resource!=self.resource:raise CoreError('ENGINEERING_RESOURCE_MISMATCH')
        if action['state'] not in ({'UNKNOWN','PENDING_VERIFY'} if verify else {'DISPATCHING'}):raise CoreError('KERNEL_DISPATCH_REQUIRED')
        owner=json.loads(self.store.one('core_meta','migration.execution_owner')['value_json']);route=json.loads(claim['value_json'])
        if (owner['actor'],owner['epoch'])!=(route['actor'],route['epoch']):raise CoreError('EXECUTION_OWNER_MISMATCH')
        attempts=[a for a in self.store.all('attempts') if a['action_id']==inv.action_id and a['kind']==('VERIFY' if verify else 'EXECUTE') and a['started_at_us'] is not None and a['outcome'] is None]
        if not attempts:raise CoreError('AUTHORIZED_ATTEMPT_REQUIRED')
        attempt=attempts[-1]
        if verify and not self.store.one('core_meta','migration.verify_claim:'+attempt['attempt_id']):raise CoreError('ROUTED_VERIFY_REQUIRED')
        grant=self.store.one('grants',attempt['grant_id']);scope=json.loads(grant['body_json'])
        now=self.store.clock.utc_now_us()
        cap='engineering.action.verify' if verify else inv.capability
        if grant['revoked'] or not grant['not_before_us']<=now<grant['expires_at_us'] or cap not in scope['capabilities'] or inv.resource not in scope['resources']:raise CoreError('AUTH_REQUIRED')
        holds={h['dimension']:h for h in self.store.all('budget_holds') if h['owner_id']==attempt['attempt_id']}
        expected={'external_requests':'SPENT','cost_micro_units':'HELD'}
        if not verify and inv.capability in WRITE:expected['write_attempts']='SPENT'
        if any(k not in holds or holds[k]['status']!=v or holds[k]['amount']!=1 for k,v in expected.items()):raise CoreError('CONSUMED_ATTEMPT_BUDGET_REQUIRED')
        self.validate(inv.capability,inv.args)
    def _journal(self,inv,result):
        self.db.execute('INSERT INTO receipts VALUES(?,?,?)',(inv.action_id,inv.idempotency_key,canonical(result)));self.db.commit()
    def execute(self,inv):
        self._proof(inv)
        if self.db.execute('SELECT 1 FROM receipts WHERE idem=?',(inv.idempotency_key,)).fetchone():raise CoreError('ENGINEERING_ALREADY_EXECUTED')
        cap,args=inv.capability,inv.args;self._branch_guard();result={'capability':cap,'workspace_hash':self._hash(),'resource':self.resource}
        if cap=='repo.inspect':result.update(branch=self.branch,head=self._git('rev-parse','HEAD'))
        elif cap=='file.read':result.update(path=args['path'],content=self._file(args['path']).read_text(),content_hash=digest(self._file(args['path']).read_bytes()))
        elif cap=='file.patch':
            p=self._file(args['path'])
            if digest(p.read_bytes())!=args['before_hash']:raise CoreError('PATCH_BASE_MISMATCH')
            # Atomically replace only a regular, nonhardlinked allowlisted file.
            tmp=p.with_name(p.name+'.nana-patch')
            fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            try:
                with os.fdopen(fd,'w') as f:f.write(args['content']);f.flush();os.fsync(f.fileno())
                os.replace(tmp,p)
            finally:
                if tmp.exists():tmp.unlink()
            result.update(path=args['path'],content_hash=digest(p.read_bytes()),workspace_hash=self._hash())
        elif cap=='tests.run':
            target,expected=self.test_contracts[args['test_id']]
            runner=Path(__file__).with_name('engineering_test_runner.py')
            try:r=subprocess.run([sys.executable,'-I',str(runner),str(self.workspace),target,canonical(expected)],env=self._env(),capture_output=True,timeout=5)
            except subprocess.TimeoutExpired:raise CoreError('ENGINEERING_TEST_UNKNOWN') from None
            result.update(test_id=args['test_id'],exit_code=r.returncode,passed=r.returncode==0,stdout_hash=digest(r.stdout),workspace_hash=self._hash())
        elif cap=='git.diff':result.update(diff_hash=digest(self._git('diff','--no-ext-diff','--no-textconv','HEAD','--',*self.allow_paths).encode()))
        elif cap=='git.commit':
            test=self.store.one('actions',args['test_action_id'])
            if not test or test['capability']!='tests.run' or test['state']!='SUCCEEDED' or test['resource']!=self.resource:raise CoreError('VERIFIED_PASSING_TEST_REQUIRED')
            proof=json.loads(test['result_json'])
            if not proof.get('passed') or proof.get('workspace_hash')!=self._hash():raise CoreError('CURRENT_PASSING_TEST_REQUIRED')
            if self._git('rev-parse','HEAD')!=args['parent_sha']:raise CoreError('COMMIT_PARENT_MISMATCH')
            # Refuse dirty files/index outside exact operator scope, even pre-staged.
            dirty=set(self._git('diff','--name-only','HEAD').splitlines())|set(self._git('ls-files','--others','--exclude-standard').splitlines())
            if not dirty or not dirty<=set(self.allow_paths):raise CoreError('COMMIT_SCOPE_REJECTED')
            self._git('add','--',*self.allow_paths)
            self._git('commit','-m',args['message']+'\n\nNana-Action: '+inv.action_id)
            result.update(commit_sha=self._git('rev-parse','HEAD'),parent_sha=args['parent_sha'],test_action_id=args['test_action_id'],workspace_hash=self._hash())
        else:raise CoreError('UNKNOWN_CAPABILITY')
        self._journal(inv,result);return Receipt(external_id=inv.idempotency_key,result=result)
    def verify(self,inv):
        self._proof(inv,verify=True);row=self.db.execute('SELECT result FROM receipts WHERE action_id=? AND idem=?',(inv.action_id,inv.idempotency_key)).fetchone()
        if not row:
            if inv.capability=='file.patch' and digest(self._file(inv.args['path']).read_bytes())==digest(inv.args['content'].encode()):
                return Verification(verdict='MATCH',evidence={'result':{'path':inv.args['path'],'content_hash':digest(inv.args['content'].encode()),'workspace_hash':self._hash(),'recovered_without_receipt':True}})
            return Verification(verdict='INCONCLUSIVE',evidence={'reason':'NO_DURABLE_ENGINEERING_RECEIPT'})
        result=json.loads(row[0]);ok=result['workspace_hash']==self._hash()
        if inv.capability=='repo.inspect':ok=ok and result['head']==self._git('rev-parse','HEAD')
        if inv.capability=='git.diff':ok=ok and result['diff_hash']==digest(self._git('diff','--no-ext-diff','--no-textconv','HEAD','--',*self.allow_paths).encode())
        if inv.capability=='file.read':ok=ok and result['content_hash']==digest(self._file(inv.args['path']).read_bytes())
        if inv.capability=='tests.run':ok=ok and result['passed']
        if inv.capability=='git.commit':ok=ok and self._git('rev-parse','HEAD')==result['commit_sha'] and 'Nana-Action: '+inv.action_id in self._git('log','-1','--format=%B')
        return Verification(verdict='MATCH' if ok else 'EFFECT_MISMATCH',evidence={'result':result,'independent_workspace_hash':self._hash()})
