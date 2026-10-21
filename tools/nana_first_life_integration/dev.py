"""First-Life private development entry. Offline by default; no secret discovery."""
import argparse,json,os,shutil,sqlite3,stat,subprocess
from pathlib import Path
from nana_core.contracts import CoreError
from nana_core.life.config import load_config,write_config
from nana_core.life.cloud import health,transfer,receive
from nana_core.life.inspector import inspect
from nana_core.life.control import request
from nana_core.life.application import LifeApplication
from nana_core.continuity.current_state import ProjectStateBinding
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService
from tools.nana_cloud_daily_life.qualification import configuration

BASE='8a1e2cfba3c71d7f397ac8486e4565a915959cb5'
BRANCH='dev/nana-core-cloud-first-life-launch-v1-codex'
REPO=Path(__file__).resolve().parents[2]


def preflight(home,*,live=False,resolver=None):
    """Existing metadata only. No Store construction, initialization or repair."""
    home=Path(home).absolute();checks={};head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    checks['lineage']=subprocess.run(['git','merge-base','--is-ancestor',BASE,head],cwd=REPO).returncode==0
    checks['branch']=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()==BRANCH
    audit=json.loads((REPO/'docs/nana_master_framework_foundation_audit_v1_evidence/audit.json').read_text())
    checks['foundation']=all(d['foundation_status']=='FOUNDATION_QUALIFIED' for d in audit['domains'] if d['id']!='S10')
    if not home.is_dir() or home!=home.resolve() or home.stat().st_uid!=os.getuid() or home.stat().st_mode&0o077:raise CoreError('FIRST_LIFE_PRIVATE_HOME_REQUIRED')
    from nana_core.life.inspector import _regular
    _regular(home/'life.json')
    cfg=load_config(home);dbpath=home/'subject/self.db'
    if not dbpath.is_file() or dbpath.is_symlink():raise CoreError('FIRST_LIFE_EXISTING_STORE_REQUIRED')
    from nana_core.presence.cli import status
    state=status(dbpath)
    checks['no_active_writer']=not state.get('runtime_active',False)
    checks['stale_writer_fenced']=not state.get('runtime_active',False) # original Runtime rechecks under exclusive lock
    checks['control_socket_safe']=not (home/'control.sock').exists() or (stat.S_ISSOCK((home/'control.sock').lstat().st_mode) and (home/'control.sock').lstat().st_uid==os.getuid())
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
        checks['schema13']=db.execute('PRAGMA user_version').fetchone()[0]==13
        checks['integrity']=db.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
        identities=db.execute('SELECT identity_id FROM identities LIMIT 2').fetchall();checks['one_identity']=len(identities)==1
        checks['no_unknown_provider']=db.execute("SELECT count(*) FROM cognitive_requests WHERE state IN ('PREPARED','CALLING','UNKNOWN')").fetchone()[0]==0
        checks['not_retired_or_quarantined']=not db.execute("SELECT 1 FROM core_meta WHERE key IN ('portable.retired','recovery_quarantine') AND value_json!='false'").fetchone()
    checks['writable_owned_paths']=all(os.access(p,os.W_OK) for p in (home,dbpath,dbpath.parent))
    checks['disk_guard']=shutil.disk_usage(home).free>=cfg.min_free_disk_mb*1024*1024
    from nana_core.life.durability import read_window
    guard=read_window(home/'storage-monitor.json');checks['resource_guard']=guard is None or guard.status=='OBSERVING'
    checks['owned_scope']=Path(cfg.project_root).resolve()==REPO and cfg.owned_application_profile is None
    checks['no_production_or_private_connector']=all(b.adapter=='shadow.local' and b.mode=='DEVELOPMENT_SHADOW_NO_SEND' for b in cfg.surface_bindings)
    checks['privacy']=set(cfg.remote_privacy)<={'PUBLIC','PROJECT'}
    checks['inspector_read_only']=inspect(home,scope='project-work',entity_id='project-user').read_only
    # Governance is the existing original Kernel/Manager path, not a new grant.
    from nana_core.life.inspector import _ReadView
    from nana_core.continuity.autonomy.governance import snapshot
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        view=_ReadView(db,dbpath,'project-work',('PUBLIC','PROJECT'))
        signature,_=snapshot(view)
        checks['manager_path']=signature is not None
    checks['rollback_anchor']=subprocess.run(['git','cat-file','-e',BASE+'^{commit}'],cwd=REPO).returncode==0
    configured=(home/'providers.json').exists()
    checks['provider_configuration']=configured if live else True
    checks['explicit_secret_binding']=resolver is not None if live else True
    if live:
        from nana_core.life.provider import configured_router
        from nana_core.continuity.provider_routing import RouteRequest
        from nana_core.continuity.context import ContextPolicy
        try:
            router=configured_router(home,cfg,resolver=resolver,authorized=True)
            router.resolve(RouteRequest(operation='COGNITION',privacy_class='PROJECT',timeout_ms=cfg.provider_timeout_ms,cost_ceiling=cfg.provider_cost_ceiling_micro,context_limit=cfg.provider_context_tokens,output_limit=cfg.provider_output_tokens),ContextPolicy(policy_id='first-life',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'),remote_privacy=cfg.remote_privacy))
            checks['live_route']=True
        except CoreError:checks['live_route']=False
    return {'state':'PREFLIGHT_PASS' if all(checks.values()) else 'FIRST_LIFE_START_BLOCKED','checks':checks,'identity_id':identities[0][0] if identities else None,'source_head':head,'provider_mode':'LIVE_EXPLICIT' if live else 'OFFLINE_LIMITED_NOT_NATURALNESS','read_only':True,'production':False}


def initialize(home,*,owned_work=False):
    home=Path(home)
    if home.exists():raise CoreError('FIRST_LIFE_FRESH_HOME_REQUIRED')
    cfg=configuration(REPO).model_copy(update={'max_autonomous_materials':1 if owned_work else 0,'current_project_state':ProjectStateBinding(relative_path='PROJECT_BRAIN/09_STATE.md',source_id='project.mainline.current',scope='project-work')})
    write_config(home,cfg)
    authority=ProviderConfigurationAuthority();ProviderConfigService(home/'providers.json',authority).initialize(authority)
    with LifeApplication(home,bootstrap_grant=owned_work) as app:
        identity=app.runtime.identity_id
    return {'identity_id':identity,'state':'INITIALIZED_OFFLINE','execution_grant':'OWNED_REPORTS_ONLY' if owned_work else 'NONE','home':str(home)}


def render_inspector(snapshot):
    labels={'runtime':'运行','activities':'活动','goals':'目标','concerns':'关注','needs':'需要','affect':'社交倾向','relationship':'关系影响','interests':'兴趣','decisions':'WHAT / WHY（来源支持的代码）','suppressed_deferred':'克制 / 延后','experience':'有来源的实际结果','learning':'学习影响 / 方法状态','skills':'受限技能','world':'世界信念','authority':'权限与阻断','unknown':'未确定结果','provider':'Provider','queue':'待办','health':'健康'}
    lines=['Nana Core Inspector · 只读派生视图','主体 '+snapshot.identity_id,'私人活动 '+snapshot.private_activity+'（内容默认不展示）']
    for key,label in labels.items():
        values=snapshot.sections[key]
        lines.append(label+'：'+'；'.join(v.category+'='+v.state for v in values[:4]))
    lines.append('UNKNOWN表示本有界视图没有足够证据；不是没有欲望/情感。--json可查看ID与来源，不提供权限。')
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('init','preflight','start','chat','inspect','pause','resume','stop','emergency-stop','backup','export','restore','health'));p.add_argument('--home',type=Path,required=True);p.add_argument('--seconds',type=int,default=3600);p.add_argument('--json',action='store_true');p.add_argument('--allow-owned-work',action='store_true');p.add_argument('--live-authorized',action='store_true');p.add_argument('--secret-fd',type=int);p.add_argument('--secret-ref');p.add_argument('--package',type=Path);p.add_argument('--sha256');p.add_argument('--destination-id');a=p.parse_args();resolver=None
    try:
        if a.command=='init':value=initialize(a.home,owned_work=a.allow_owned_work)
        elif a.command in {'start','preflight'}:
            if a.live_authorized:
                if a.secret_fd is None or not a.secret_ref:raise CoreError('EXPLICIT_SECRET_RESOLVER_REQUIRED')
                from nana_core.life.provider import ExplicitFDResolver
                resolver=ExplicitFDResolver(a.secret_fd,a.secret_ref)
            elif a.secret_fd is not None or a.secret_ref:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED')
            value=preflight(a.home,live=a.live_authorized,resolver=resolver)
            if value['state']!='PREFLIGHT_PASS':print(json.dumps(value));raise SystemExit(2)
            if a.command=='start':
                if not 0<a.seconds<=7200:raise CoreError('FIRST_LIFE_DURATION_BOUND')
                from nana_core.life.__main__ import run
                from nana_core.life.provider import configured_router
                router=configured_router(a.home,load_config(a.home),resolver=resolver,authorized=True) if a.live_authorized else None
                run(a.home,a.seconds,headless=True,router=router,control_enabled=True);return
        elif a.command=='chat':
            from nana_core.life.review import chat
            chat(a.home,privacy='PROJECT');return
        elif a.command=='inspect':
            snapshot=inspect(a.home,scope='project-work',entity_id='project-user')
            if not a.json:
                print(render_inspector(snapshot));return
            value=snapshot.model_dump(mode='json')
        elif a.command=='health':value=health(a.home)
        elif a.command in {'export','restore'}:
            if not a.package or not a.destination_id:raise CoreError('EXPLICIT_TRANSFER_REQUIRED')
            if a.command=='export':value=transfer(a.home,a.package,destination_id=a.destination_id,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip())
            else:
                if not a.sha256:raise CoreError('TRANSFER_DIGEST_REQUIRED')
                value=receive(a.package,a.home,sha256=a.sha256,destination_id=a.destination_id,config=configuration(REPO))
        elif a.command=='backup':value=request(a.home,{'operation':'backup','name':'first-life-checkpoint'})
        elif a.command=='emergency-stop':
            value=[request(a.home,{'operation':'control','command':x}) for x in ('pause','revoke','stop')]
        else:value=request(a.home,{'operation':'control','command':a.command})
        print(json.dumps(value,ensure_ascii=False,indent=2))
    except (CoreError,OSError,ValueError) as exc:
        print(json.dumps({'state':'FIRST_LIFE_START_BLOCKED','code':exc.code if isinstance(exc,CoreError) else 'FIRST_LIFE_LOCAL_CONFIGURATION_INVALID'}));raise SystemExit(2) from None
    finally:
        if resolver:resolver.clear()

if __name__=='__main__':main()
