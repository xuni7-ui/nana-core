"""Host-portable thin application CLI. Original Store/Runtime/B8 only."""
import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import sqlite3
import stat
import sys
import termios
import time
from pathlib import Path
from uuid import uuid4

from ..contracts import CoreError
from ..host_requirements import sqlite_runtime_report, unix_socket_path
from ..continuity import ContinuityStore
from ..continuity.provider_config import ProviderConfigService, ProviderConfigurationAuthority
from ..continuity.project_work.service import material_for
from ..continuity.portable import verify_package
from ..presence.cli import status
from .config import LifeConfig, load_config, write_config
from .application import LifeApplication
from .cloud import health, transfer, receive, backup
from .control import request
from .inspector import inspect
from .provider import ExplicitFDResolver, configured_router
from .surfaces import SurfaceBinding


def configuration(root):
    project = (Path(root) / 'materials').absolute()
    return LifeConfig(project_root=str(project), materials=(material_for(project,'sample.py'),),
        practice=material_for(project,'practice.py'), heldout=material_for(project,'heldout.py'),
        transfer=material_for(project,'transfer.py'), max_autonomous_materials=0,
        surface_bindings=(SurfaceBinding(
            binding_id='cloud.cli',platform='cloud.cli',surface='chat.direct',adapter='shadow.local'),))


def private_path(path):
    path=Path(path).absolute()
    if path.resolve()!=path:raise CoreError('PORTABLE_PATH_SYMLINK_DENIED')
    if path.exists() and (not path.is_dir() or path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077):
        raise CoreError('PORTABLE_PRIVATE_HOME_REQUIRED')
    return path


def owner_alive(report):
    return bool(report.get('process_alive') and report.get('lease',{}).get('state')=='ACTIVE')


def _dependency_check(root):
    """Read the pinned installed dependency metadata, never resolve/install it."""
    checks={}
    try:
        import importlib.metadata as md
        lock=json.loads((Path(root)/'runtime.json').read_text())['dependencies']
        checks['dependencies']=all(md.version(k)==v for k,v in lock.items())
    except (OSError,ValueError,KeyError,md.PackageNotFoundError):checks['dependencies']=False
    return checks['dependencies']


def _resource_checks(home):
    """Host-local resource ceilings only; no authority or Subject mutation."""
    checks={}
    parent=home
    while not parent.exists() and parent!=parent.parent:parent=parent.parent
    checks['writable_path']=os.access(parent,os.W_OK|os.X_OK)
    checks['disk']=shutil.disk_usage(parent).free>=64*1024*1024
    soft,_=resource.getrlimit(resource.RLIMIT_NOFILE);checks['fd_limit']=soft==resource.RLIM_INFINITY or soft>=128
    checks['memory']=os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')>=512*1024*1024
    try:
        ceiling=Path('/sys/fs/cgroup/memory.max').read_text().strip()
        checks['memory']=checks['memory'] and (ceiling=='max' or int(ceiling)>=512*1024*1024)
    except (OSError,ValueError):pass
    checks['secret_binding']=hasattr(os,'pipe') and hasattr(termios,'tcsetattr')
    return checks


def _subject_checks(home,*,starting):
    """Read-only Store/lease/privacy projection; never remove a stale socket."""
    checks={}
    exists=(home/'life.json').is_file()
    if starting and not exists:checks['existing_subject']=False
    if exists:
        cfg=load_config(home);p=home/'subject/self.db';current=status(p)
        checks['project_sources']=Path(cfg.project_root).resolve()==Path(cfg.project_root) and Path(cfg.project_root).is_dir()
        checks['no_external_adapters']=cfg.owned_application_profile is None and all(b.adapter=='shadow.local' and b.mode=='DEVELOPMENT_SHADOW_NO_SEND' for b in cfg.surface_bindings)
        checks['remote_privacy']=set(cfg.remote_privacy)<={'PUBLIC','PROJECT'}
        checks['owner_fence']=not owner_alive(current) if starting else True
        socket=home/'control.sock'
        checks['socket_path']=not (socket.exists() or socket.is_symlink()) or (stat.S_ISSOCK(socket.lstat().st_mode) and socket.lstat().st_uid==os.getuid() and socket.lstat().st_mode&0o077==0)
        if owner_alive(current) and not current.get('runtime_active'):checks['owner_fence']=False
        from .inspector import _regular, _ReadView
        _regular(p)
        with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            checks['schema']=db.execute('pragma user_version').fetchone()[0]==13
            checks['integrity']=db.execute('pragma quick_check').fetchone()[0]=='ok' and not db.execute('pragma foreign_key_check').fetchall()
            checks['one_identity']=db.execute('select count(*) from identities').fetchone()[0]==1
            checks['not_retired']=db.execute("select 1 from core_meta where key in ('portable.retired','recovery_quarantine') and value_json!='false'").fetchone() is None
            checks['no_live_old_grants']=db.execute('select count(*) from grants where revoked=0').fetchone()[0]==0
            from ..continuity.autonomy.governance import snapshot
            checks['manager']=snapshot(_ReadView(db,p,'project-work',('PUBLIC','PROJECT')))[0] is not None
            unresolved=db.execute("select count(*) from cognitive_requests where state in ('UNKNOWN','CALLING','PREPARED')").fetchone()[0]
        checks['inspector']=inspect(home,scope='project-work',entity_id='project-user').read_only
        checks['provider_configuration']=(home/'providers.json').is_file()
        if checks['provider_configuration']:
            ProviderConfigService(home/'providers.json',ProviderConfigurationAuthority()).load()
        identity=inspect(home,scope='project-work',entity_id='project-user').identity_id
    else:identity=None;unresolved=0
    return checks,exists,identity,unresolved


def preflight(root,home,*,starting=False):
    """Read existing state only. Never repair/start/create a Subject here."""
    home=private_path(home);checks={}
    checks['platform']=sys.platform=='linux' and platform.machine()=='x86_64'
    checks['python']=sys.version_info[:2]==(3,12)
    checks['venv']=sys.prefix!=sys.base_prefix
    sqlite_report=sqlite_runtime_report()
    checks['sqlite']=sqlite_report['supported']
    try:
        unix_socket_path(home/'control.sock');checks['socket_path_length']=True
    except ValueError:
        checks['socket_path_length']=False
    # Do not inspect/create Subject state with an unsupported interpreter/path.
    if not checks['sqlite'] or not checks['socket_path_length']:
        return {'state':'START_BLOCKED','checks':checks,'sqlite_runtime':sqlite_report,
                'code':sqlite_report['code'] if not checks['sqlite'] else 'UNIX_SOCKET_PATH_TOO_LONG',
                'subject_present':(home/'life.json').is_file(),'execution_authority':False}
    checks['dependencies']=_dependency_check(root)
    checks['sqlite_json']=sqlite_report['checks']['json']
    checks['sqlite_fts5']=sqlite_report['checks']['fts5']
    checks.update(_resource_checks(home))
    subject_checks,exists,identity,unresolved=_subject_checks(home,starting=starting)
    checks.update(subject_checks)
    from ..continuity.open_agency.code_skills import IsolatedSkillRunner
    return {'state':'PREFLIGHT_PASS' if all(checks.values()) else 'START_BLOCKED','checks':checks,
        'sqlite_runtime':sqlite_report,'optional_capabilities':{'generated_python_skill':IsolatedSkillRunner().qualify()},
        'identity_id':identity,'subject_present':exists,'unknown_provider_requests':unresolved,
        'failed_checks':[key for key,value in checks.items() if not value],
        'live_provider':'EXPLICIT_BINDING_REQUIRED','real_social_send':False,'private_history_connector':False}


def secret(reference,fd=None):
    if fd is not None:
        if not (stat.S_ISFIFO(os.fstat(fd).st_mode) or stat.S_ISSOCK(os.fstat(fd).st_mode)):raise CoreError('MEMORY_FD_REQUIRED')
        return ExplicitFDResolver(fd,reference)
    if not os.isatty(0):raise CoreError('EXPLICIT_PRIVATE_TTY_OR_FD_REQUIRED')
    old=termios.tcgetattr(0);masked=termios.tcgetattr(0);masked[3]&=~termios.ECHO
    termios.tcsetattr(0,termios.TCSANOW,masked)
    try:
        print('CREDENTIAL_INPUT_READY_ECHO_DISABLED',flush=True);raw=os.read(0,4097)
        if len(raw)>4096 or not raw.endswith(b'\n'):raise CoreError('SECRET_INPUT_BOUND')
        a,b=os.pipe()
        try:os.write(b,raw);os.close(b);b=None;return ExplicitFDResolver(a,reference)
        finally:
            os.close(a)
            if b is not None:os.close(b)
    finally:termios.tcsetattr(0,termios.TCSANOW,old)


def initialize(root,home):
    home=private_path(home)
    if home.exists():raise CoreError('FRESH_SUBJECT_DESTINATION_EXISTS')
    ready=preflight(root,home)
    if ready['state']!='PREFLIGHT_PASS':raise CoreError(ready.get('code','HOST_PREFLIGHT_REQUIRED'))
    write_config(home,configuration(root));authority=ProviderConfigurationAuthority();ProviderConfigService(home/'providers.json',authority).initialize(authority)
    with LifeApplication(home) as app:app.pause();identity=app.runtime.identity_id
    return {'state':'NEW SUBJECT CREATED','identity_id':identity,'history_inherited':False,'execution_grants':0}


def stop(home,emergency=False):
    if not owner_alive(status(home/'subject/self.db')):return {'state':'ALREADY_STOPPED'}
    results=[]
    for command in ('pause','revoke','stop'):
        value=request(home,{'operation':'control','command':command})
        if not value['ok']:raise CoreError(value['code'])
        results.append(value['result'])
    until=time.monotonic()+8
    while time.monotonic()<until:
        if not owner_alive(status(home/'subject/self.db')):return {'state':'STOPPED_AUTHORITY_REVOKED','controls':results}
        time.sleep(.05)
    raise CoreError('STOP_COMPLETION_UNKNOWN_NO_RETRY')


def execute(root,a):
    home=private_path(a.home);name=a.command
    if name=='preflight':return preflight(root,home)
    if name=='init':
        if not a.fresh:raise CoreError('EXPLICIT_FRESH_MODE_REQUIRED')
        return initialize(root,home)
    if name=='restore':
        ready=preflight(root,home)
        if ready['state']!='PREFLIGHT_PASS':raise CoreError(ready.get('code','HOST_PREFLIGHT_REQUIRED'))
        # Verify before creating destination; never guess init on a missing home.
        m,_=verify_package(a.package,expected_sha256=a.sha256)
        if m.source_schema!=13:raise CoreError('PORTABLE_RUNTIME_SCHEMA_MISMATCH')
        result=receive(a.package,home,sha256=a.sha256,destination_id=a.destination_id,config=configuration(root))
        with LifeApplication(home) as app:app.pause()
        return {**result,'lineage_transfer_id':m.transfer_id,'old_host_grants':0,'autonomy':'PAUSED_REEVALUATION_REQUIRED'}
    if name not in {'init','restore','preflight'} and not (home/'life.json').is_file():raise CoreError('EXISTING_SUBJECT_REQUIRED_NO_AUTO_INIT')
    if name=='start' or name=='restart':
        if name=='restart':stop(home)
        ready=preflight(root,home,starting=True)
        if ready['state']!='PREFLIGHT_PASS':return ready
        if not 0<a.seconds<=7*86400:raise CoreError('LIFE_DURATION_BOUND')
        resolver=None;router=None
        try:
            if a.live:
                if not a.secret_ref:raise CoreError('EXPLICIT_SECRET_REFERENCE_REQUIRED')
                if ready['unknown_provider_requests']:raise CoreError('UNRESOLVED_PROVIDER_CALL_NO_RETRY')
                resolver=secret(a.secret_ref,a.secret_fd);router=configured_router(home,load_config(home),resolver=resolver,authorized=True)
            elif a.secret_fd is not None or a.secret_ref:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED')
            from .__main__ import run
            run(home,a.seconds,headless=True,router=router,control_enabled=True)
            return {'state':'RUNTIME_EXITED','resolver_cleared_on_exit':True}
        finally:
            if resolver:resolver.clear()
    if name=='inspect':return inspect(home,scope='project-work',entity_id='project-user').model_dump(mode='json')
    if name=='status':return status(home/'subject/self.db')
    if name=='health':return health(home)
    if name in {'stop','emergency-stop'}:return stop(home,name=='emergency-stop')
    if name in {'pause','resume'}:return request(home,{'operation':'control','command':name})
    if name=='chat':
        from .review import chat
        chat(home,privacy='PROJECT',retain_shared_life=getattr(a,'retain_shared_life',False));return {'state':'CHAT_CLIENT_EXITED'}
    if name=='self-profile':
        return request(home,{'operation':'self-profile','name':a.name,'aliases':a.alias,'expected_revision':a.expected_revision,'reason':'Explicit host-owner instance profile'})
    if name=='review-expression-learning':
        return request(home,{'operation':'review-expression-learning','lesson_id':a.lesson_id})
    if name=='provider-command':
        from .provider import provider_command
        return provider_command(home,a.document)
    if name=='config':
        current=load_config(home)
        if a.document is None:return current.model_dump(mode='json')
        from .config import update_config
        from ..continuity.privacy import _json_object
        fd=os.open(a.document,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise CoreError('CONFIG_DOCUMENT_REQUIRED')
            raw=f.read(65537)
        if len(raw)>65536:raise CoreError('CONFIG_DOCUMENT_BOUND')
        cfg=LifeConfig.model_validate_json(json.dumps(json.loads(raw,object_pairs_hook=_json_object)))
        if cfg.owned_application_profile or set(cfg.remote_privacy)-{'PUBLIC','PROJECT'} or any(b.adapter!='shadow.local' for b in cfg.surface_bindings):raise CoreError('PORTABLE_HOST_POLICY_DENIED')
        if owner_alive(status(home/'subject/self.db')):raise CoreError('STOP_BEFORE_HOST_CONFIG_CHANGE')
        result=update_config(home,cfg,expected_revision=cfg.revision-1)
        return {'state':'HOST_CONFIG_UPDATED','revision':result.revision,'subject_identity_changed':False}
    if name=='export':
        if not a.retire_source:raise CoreError('EXPLICIT_SOURCE_RETIREMENT_REQUIRED')
        if owner_alive(status(home/'subject/self.db')):raise CoreError('STOP_SOURCE_FIRST')
        release=json.loads((root/'runtime.json').read_text())
        return transfer(home,a.output,destination_id=a.destination_id,source_commit=release['source_commit'],pending_effects=a.pending_effects)
    if name=='backup':
        if owner_alive(status(home/'subject/self.db')):raise CoreError('STOP_FOR_PORTABLE_BACKUP')
        with ContinuityStore(home/'subject/self.db',schema_target=13) as store:result=backup(store,a.output)
        result.update(sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),created_at_us=time.time_ns()//1000)
        meta=a.output.with_name(a.output.name+'.json')
        fd=os.open(meta,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as stream:json.dump(result,stream)
        return result
    raise CoreError('PORTABLE_OPERATION_DENIED')


def main(root=None):
    root=Path(root or Path(__file__).resolve().parents[3]).absolute()
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    for name in ('preflight','init','restore','start','restart','inspect','status','health','stop','emergency-stop','chat','backup','export','pause','resume','provider-command','config','self-profile','review-expression-learning'):
        s=subs.add_parser(name);s.add_argument('--home',type=Path,default=root/'var/subject')
        if name=='chat':s.add_argument('--retain-shared-life',action='store_true')
        if name=='self-profile':s.add_argument('--name',required=True);s.add_argument('--alias',action='append',default=[]);s.add_argument('--expected-revision',type=int,required=True)
        if name=='review-expression-learning':s.add_argument('--lesson-id',required=True)
        if name=='init':s.add_argument('--fresh',action='store_true')
        if name in {'start','restart'}:
            s.add_argument('--seconds',type=int,default=3600);s.add_argument('--live',action='store_true');s.add_argument('--secret-fd',type=int);s.add_argument('--secret-ref')
        if name in {'backup','export'}:s.add_argument('--output',type=Path,required=True)
        if name in {'export','restore'}:
            s.add_argument('--destination-id',required=True)
            if name=='export':s.add_argument('--retire-source',action='store_true');s.add_argument('--pending-effects',action='store_true')
            else:s.add_argument('--package',type=Path,required=True);s.add_argument('--sha256',required=True)
        if name=='provider-command':s.add_argument('--document',type=Path,required=True)
        if name=='config':s.add_argument('--document',type=Path)
    a=p.parse_args()
    try:
        result=execute(root,a);print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        if result.get('state')=='START_BLOCKED':raise SystemExit(2)
    except (CoreError,OSError,ValueError,sqlite3.Error):
        # Exception repr/path/validation inputs are not diagnostic output.
        exc=sys.exc_info()[1];print(json.dumps({'state':'START_BLOCKED','code':exc.code if isinstance(exc,CoreError) else 'PORTABLE_LOCAL_VALIDATION_FAILED'}));raise SystemExit(2) from None

if __name__=='__main__':main()
