"""Generated Python skills: test/review/hash/isolated enable/rollback, no install.

Only the exact bwrap-isolated pure-data transform realm is available. CPython
private names or AST inspection are not represented as a general sandbox.
"""
import ast,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
from typing import Literal,Any,Protocol
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import canonical,digest
from ..records import RecordService
from .world import bounded_data

class CodeSpec(DTO):
    name: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    revision: int = Field(ge=1)
    purpose: str = Field(min_length=1,max_length=512)
    contract: Literal['JSON_PURE_TRANSFORM_V1'] = 'JSON_PURE_TRANSFORM_V1'
    task: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    input_limit: int = Field(default=8192,ge=1,le=8192)
    output_limit: int = Field(default=8192,ge=1,le=8192)
class CodeCandidate(DTO):
    provenance: Literal['GENERATED_CODE_NOT_AUTHORITY'] = 'GENERATED_CODE_NOT_AUTHORITY'
    source: str = Field(min_length=1,max_length=8192)
class CodeProposerPort(Protocol):
    def implement(self,spec:CodeSpec,diagnostic:str|None=None)->CodeCandidate:...
class FixtureCodeProposer:
    def implement(self,spec,diagnostic=None):
        if spec.task=='FRACTIONAL_TOTAL':
            source='def transform(data):\n    return sum(x for x in data if isinstance(x, (int, float)))\n' if diagnostic else 'def transform(data):\n    return sum(int(x) for x in data if isinstance(x, (int, float)))\n'
        elif spec.task=='UNICODE_TOKENS':source='def transform(data):\n    return data.split()\n'
        else:raise CoreError('FIXTURE_CODE_TASK_UNAVAILABLE')
        return CodeCandidate(source=source)

def static_check(source):
    if type(source) is not str or len(source.encode())>8192:raise CoreError('SKILL_SOURCE_BOUND')
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError):raise CoreError('SKILL_SYNTAX_REJECTED') from None
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef) or tree.body[0].name!='transform' or tree.body[0].decorator_list or len(tree.body[0].args.args)!=1 or tree.body[0].args.args[0].arg!='data' or tree.body[0].args.defaults or tree.body[0].args.kwonlyargs or tree.body[0].args.vararg or tree.body[0].args.kwarg:raise CoreError('SKILL_CONTRACT_REJECTED')
    allowed=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Return,ast.Expr,ast.Name,ast.Load,ast.Store,ast.Constant,ast.Call,ast.Attribute,ast.GeneratorExp,ast.ListComp,ast.comprehension,ast.Tuple,ast.List,ast.IfExp,ast.Compare,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.BinOp,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.UnaryOp,ast.USub,ast.BoolOp,ast.And,ast.Or,ast.Subscript,ast.Slice)
    names={'sum','len','sorted','min','max','isinstance','int','float','str','list','bool'}
    for n in ast.walk(tree):
        if not isinstance(n,allowed):raise CoreError('SKILL_STATIC_REJECTED')
        if isinstance(n,ast.Name) and n.id.startswith('_'):raise CoreError('SKILL_STATIC_REJECTED')
        if isinstance(n,ast.Attribute) and n.attr not in {'split','casefold','lower','strip'}:raise CoreError('SKILL_STATIC_REJECTED')
        if isinstance(n,ast.Call) and not ((isinstance(n.func,ast.Name) and n.func.id in names) or (isinstance(n.func,ast.Attribute) and n.func.attr in {'split','casefold','lower','strip'})):raise CoreError('SKILL_STATIC_REJECTED')
    compile(tree,'generated-skill','exec') # compilation only; execution is isolated
    return digest(source.encode())

class IsolatedSkillRunner:
    """No host workspace mounts; runtime data/controller never enter the child."""
    def __init__(self):self.available=None
    def _command(self,root):
        bwrap=shutil.which('bwrap')
        if not bwrap:raise CoreError('SKILL_SANDBOX_UNAVAILABLE')
        args=[bwrap,'--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--setenv','PATH','/usr/bin','--setenv','LANG','C.UTF-8']
        # System stdlib/shared libraries only. Never mount /workspace, /home,
        # /root, host /tmp, sockets, credentials or the subject directory.
        for source in ('/usr/bin','/usr/lib','/usr/lib64','/lib','/lib64'):
            if Path(source).exists():args+=['--ro-bind',source,source]
        args+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(root),'/work','--chdir','/tmp','/usr/bin/python3','-I','/work/runner.py']
        return args
    def run(self,source,data):
        static_check(source);bounded_data(data)
        with tempfile.TemporaryDirectory(prefix='subject-skill-') as directory:
            root=Path(directory);root.chmod(0o700)
            (root/'skill.py').write_text(source);(root/'request.json').write_text(canonical({'input':data}))
            (root/'runner.py').write_bytes(Path(__file__).with_name('skill_runner.py').read_bytes())
            with (root/'out').open('wb') as out,(root/'err').open('wb') as err:
                try:
                    proc=subprocess.run(self._command(root),stdin=subprocess.DEVNULL,stdout=out,stderr=err,env={'PATH':os.defpath},timeout=3,check=False)
                except (subprocess.TimeoutExpired,OSError):raise CoreError('SKILL_SANDBOX_UNKNOWN') from None
            if proc.returncode:raise CoreError('SKILL_SANDBOX_FAILED')
            if (root/'out').stat().st_size>8192:raise CoreError('SKILL_OUTPUT_BOUND')
            try:value=json.loads((root/'out').read_text())['result']
            except (ValueError,KeyError,UnicodeError):raise CoreError('SKILL_OUTPUT_INVALID') from None
            bounded_data(value);self.available=True;return value

class CodeSkillService:
    def __init__(self,store,authority,*,runner=None):
        if store.schema_target<12:raise CoreError('OPEN_AGENCY_SCHEMA_REQUIRED')
        self.store,self.authority=store,authority;self.records=RecordService(store);self.runner=runner or IsolatedSkillRunner();self._tested=set();self._enabled=set()
    def propose(self,cycle,spec,proposer,*,diagnostic=None):
        if not cycle.evaluation or cycle.evaluation.normative!='ENDORSED' or not cycle.record_id or cycle.intention.behavior not in {'LEARN','SEEK_CAPABILITY','CREATE'}:raise CoreError('SUBJECT_SKILL_NEED_REQUIRED')
        if not self.records.current_support(cycle.record_id):raise CoreError('SKILL_SOURCE_RETIRED')
        candidate=proposer.implement(spec,diagnostic)
        if type(candidate) is not CodeCandidate:raise CoreError('SKILL_PROPOSAL_INVALID')
        candidate=CodeCandidate.model_validate_json(candidate.model_dump_json());sha=static_check(candidate.source)
        scope=self.records.read(cycle.record_id)['scope'];key=digest([cycle.cycle_id,spec.model_dump(mode='json'),sha])
        old=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='CODE_SKILL' AND target_id=?",(key,)).fetchone()
        if old:return old[0]
        with self.store.transaction('open.code_skill_proposed',{'source_digest':sha}) as tx:
            rid=self.records.create(tx,kind='CODE_SKILL',scope=scope,payload={'state':'GENERATED','spec':spec.model_dump(mode='json'),'source':candidate.source,'source_digest':sha,'tests':None,'realm':'BWRAP_LOCAL_DATA_ONLY','installed':False},records=(cycle.record_id,),target_id=key)
        return rid
    def test(self,rid,cases):
        row=self.records.read(rid);body=row['payload']
        if row['record_kind']!='CODE_SKILL' or body['state'] not in {'GENERATED','ACTIVE','TESTED'} or not self.records.current_support(rid):raise CoreError('SKILL_NOT_TESTABLE')
        if not 1<=len(cases)<=16:raise CoreError('SKILL_TEST_BOUND')
        results=[];started=time.monotonic_ns()
        for case in cases:
            actual=self.runner.run(body['source'],case.data)
            results.append({'case_id':case.case_id,'input_digest':digest(case.data),'actual_digest':digest(actual),'expected_digest':digest(case.expected),'passed':digest(actual)==digest(case.expected)})
        new={**body,'state':'TESTED' if all(x['passed'] for x in results) else 'REJECTED','tests':{'cases':results,'wall_latency_us':(time.monotonic_ns()-started)//1000,'actual_model_cost_micro':0,'isolation':'BWRAP_NAMESPACES_READONLY_NO_NETWORK'}}
        with self.store.transaction('open.code_skill_tested',{'source_digest':body['source_digest'],'passed':new['state']=='TESTED'}) as tx:
            out=self.records.create(tx,kind='CODE_SKILL',scope=row['scope'],payload=new,records=(rid,),supersedes=rid,target_id=row['target_id'])
        self._tested.add(out)
        return out
    def review(self,rid,*,authority,expected_digest):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        row=self.records.read(rid);b=row['payload']
        if rid not in self._tested:raise CoreError('CURRENT_REALM_TEST_REQUIRED')
        if b['state']!='TESTED' or b['source_digest']!=expected_digest or not self.records.current_support(rid) or not all(x['passed'] for x in b['tests']['cases']):raise CoreError('SKILL_REVIEW_REJECTED')
        # Activation is an application reviewed local realm only. Invoking still
        # requires the ordinary world.skill Kernel Grant/Manager/Budget gates.
        with self.store.transaction('open.code_skill_reviewed',{'source_digest':expected_digest,'realm':'ISOLATED_ONLY'}) as tx:
            active=self.records.create(tx,kind='CODE_SKILL',scope=row['scope'],payload={**b,'state':'ACTIVE'},records=(rid,),supersedes=rid,target_id=row['target_id'])
        self._enabled.add(active)
        return active
    def retire(self,rid,*,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        row=self.records.read(rid)
        if row['record_kind']!='CODE_SKILL' or row['payload']['state']!='ACTIVE':raise CoreError('ACTIVE_SKILL_REQUIRED')
        with self.store.transaction('open.code_skill_retired',{'record_id':rid}) as tx:
            return self.records.create(tx,kind='CODE_SKILL',scope=row['scope'],payload={**row['payload'],'state':'RETIRED'},records=(rid,),supersedes=rid,target_id=row['target_id'])
    def invoke(self,rid,data):
        if rid not in self._enabled:raise CoreError('CURRENT_REALM_REVIEW_REQUIRED')
        row=self.records.read(rid);b=row['payload']
        if row['record_kind']!='CODE_SKILL' or b['state']!='ACTIVE' or not self.records.current_support(rid) or static_check(b['source'])!=b['source_digest']:raise CoreError('SKILL_NOT_ACTIVE')
        if len(canonical(data).encode())>b['spec']['input_limit']:raise CoreError('SKILL_INPUT_BOUND')
        value=self.runner.run(b['source'],data)
        if len(canonical(value).encode())>b['spec']['output_limit']:raise CoreError('SKILL_OUTPUT_BOUND')
        return value
    def package(self,rid,destination):
        row=self.records.read(rid);b=row['payload']
        if row['record_kind']!='CODE_SKILL' or b['state'] not in {'TESTED','ACTIVE'} or not self.records.current_support(rid):raise CoreError('SKILL_PACKAGE_REJECTED')
        path=Path(destination)
        if path.exists():raise CoreError('DESTINATION_EXISTS')
        path.mkdir(mode=0o700,parents=False)
        (path/'skill.py').write_text(b['source'])
        manifest={'format':'LOCAL_SKILL_CANDIDATE_V1','spec':b['spec'],'source_digest':b['source_digest'],'tests':b['tests'],'record_id':rid,'installation_authority':False}
        (path/'manifest.json').write_text(canonical(manifest))
        return {'manifest_digest':digest(manifest),'source_digest':b['source_digest'],'installation_authority':False}
