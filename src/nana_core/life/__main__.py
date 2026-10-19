"""Standalone foreground life. No AstrBot, QQ, capture, production or social send."""
import argparse,json,os,selectors,signal,sys,time
from collections import deque
from pathlib import Path
from contextlib import nullcontext
from ..contracts import CoreError
from ..continuity.project_work.service import material_for
from ..continuity.provider_config import ProviderConfigService,ProviderConfigurationAuthority
from ..presence.cli import status as runtime_status
from .config import LifeConfig,home_path,write_config,load_config,apply_resource_limits
from .application import LifeApplication

DEMO_SOURCES=('src/nana_core/continuity/recurrence.py','src/nana_core/continuity/extensions.py')
DOC_SOURCES=('docs/nana_h2_perception_ingress_v1_frontend_contract.md','docs/nana_h2_live_real_screen_v1_frontend_contract.md')
DOC_TRAIN=('README.md','docs/nana_provider_capability_routing_v1_frontend_contract.md','docs/bridge_node_rebuild.md')
DEMO_TRAIN=('src/nana_core/continuity/identity.py','src/nana_core/continuity/autonomy/requests.py','src/nana_core/continuity/subject/social.py')


JSON_OUTPUT=False
def emit(value):
    from .presentation import display
    print(json.dumps(value,ensure_ascii=False) if JSON_OUTPUT else display(value),flush=True)


def command(app,line):
    if not line.startswith('/'):return {'dialogue':app.chat(line)}
    parts=line.split();name=parts[0]
    if name in {'/status','/activities'}:return app.status()
    if name in {'/life','/journal'}:return {'life':app.board()}
    if name=='/sources':return app.sources()
    if name in {'/actions','/outcomes'} and app.config.owned_application_profile:return {'external_outcomes':app.board()['external_outcomes'],'unknown_actions':app.board()['unknown_actions']}
    if name=='/pause':return app.pause()
    if name=='/resume':return app.pause(False)
    if name=='/busy':return app.presence('BUSY')
    if name=='/available':return app.presence('AVAILABLE')
    if name=='/quit':app.runtime.request_stop();return {'state':'STOP_REQUESTED'}
    if name=='/revoke':return app.revoke()
    if name=='/forget' and len(parts)==2:return app.forget(parts[1])
    if name=='/topic' and len(parts)>=3:return {'dialogue':app.chat(' '.join(parts[2:]),topic=parts[1])}
    if name=='/work' and len(parts)==2:
        if app.config.owned_application_profile:raise CoreError('OWNED_TASK_REPLAY_NOT_AUTHORIZED')
        material=next((m for m in app.config.materials if parts[1] in {m.material_id,m.relative_path,Path(m.relative_path).name}),None)
        if not material:raise CoreError('PROJECT_MATERIAL_NOT_CONFIGURED')
        return {'source_memory_id':app.work.request(material.material_id),'state':'OFFERED_TO_ORIGINAL_C_NOT_FORCED_ADOPTION'}
    return {'commands':['/status','/life','/journal','/activities','/sources','/pause','/resume','/busy','/available','/work <approved filename>','/topic <key> <text>','/forget <memory-id>','/revoke','/quit'],'ordinary_text':'type a normal sentence; provider off by default'}


def run(home,seconds,*,headless=False,router=None,control_enabled=False):
    config=load_config(home);resource=apply_resource_limits(config);started=time.monotonic();cpu=time.process_time();child=__import__('resource').getrusage(__import__('resource').RUSAGE_CHILDREN);child_cpu=child.ru_utime+child.ru_stime
    from .control import ControlServer
    from .cloud import RotatingJSONLog
    with LifeApplication(home,router=router) as app, (ControlServer(app) if control_enabled else nullcontext()) as control:
        log=RotatingJSONLog(home,config.log_max_bytes);next_log=0
        emit({'state':'STARTED','identity_id':app.runtime.identity_id,'mode':'OFFLINE_LIMITED' if router is None else 'PROVIDER_CONFIGURED_NOT_QUALIFIED','resources':resource,'commands':'/help; ordinary text; /status','autonomous_materials':len(config.materials[:config.max_autonomous_materials])})
        def stop(*unused):app.runtime.request_stop()
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        selector=selectors.SelectSelector()
        if not headless:selector.register(sys.stdin,selectors.EVENT_READ,'stdin')
        if control:selector.register(control.socket,selectors.EVENT_READ,'control')
        pending=deque();buffer=b'';eof=False;discard=False
        while not app.runtime.stop_requested and time.monotonic()-started<seconds:
            ready=selector.select(0 if pending else max(.1,min(1.,app.runtime.next_wait_seconds())))
            if control and any(key.data=='control' for key,_ in ready):control.poll()
            if any(key.data=='stdin' for key,_ in ready):
                # Read the FD directly: TextIOWrapper.readline can read ahead,
                # leaving buffered commands invisible to select() on the FD.
                raw=os.read(sys.stdin.fileno(),4096)
                if not raw:
                    eof=True;selector.unregister(sys.stdin)
                    if buffer:raw=b'\n'
                buffer+=raw
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    if discard:discard=False;continue
                    if len(line)>8192:emit({'state':'REJECTED','code':'LOCAL_MESSAGE_BOUND'});continue
                    if len(pending)>=16:emit({'state':'REJECTED','code':'LOCAL_INPUT_BACKPRESSURE'});continue
                    try:line=line.decode('utf-8').strip()
                    except UnicodeError:emit({'state':'REJECTED','code':'LOCAL_INPUT_ENCODING_INVALID'});continue
                    if len(line)>2048:emit({'state':'REJECTED','code':'LOCAL_MESSAGE_BOUND'});continue
                    if line:pending.append(line)
                if len(buffer)>8192:
                    buffer=b'';discard=True;emit({'state':'REJECTED','code':'LOCAL_MESSAGE_BOUND'})
            if pending:
                line=pending.popleft()
                try:emit(command(app,line))
                except (CoreError,ValueError):emit({'state':'BLOCKED','code':'LOCAL_COMMAND_OR_STATE_REJECTED'})
            elif eof:
                app.runtime.request_stop();continue
            import shutil
            if shutil.disk_usage(home).free<config.min_free_disk_mb*1024*1024 and not app.runtime.work.paused:app.pause()
            value=app.tick()
            if time.monotonic()>=next_log:
                import shutil
                free=shutil.disk_usage(home).free
                if free<config.min_free_disk_mb*1024*1024:
                    if not app.runtime.work.paused:app.pause()
                else:log.write(state=app.runtime.health().status,clock_us=app.runtime.clock.utc_now_us(),queue_depth=app.runtime.queue.depth())
                next_log=time.monotonic()+60
            if value and ((value.get('cycle') and value['cycle'].intention.kind!='NO_ACTION') or value.get('maintenance')):
                cycle=value.get('cycle');emit({'activity':value.get('reason'),'judgment':cycle.judgment.stance if cycle else None,'intention':cycle.intention.kind if cycle else None,'social_candidate':cycle.social_proposal.act if cycle and cycle.social_proposal else None,'maintenance_stage':(value.get('maintenance') or {}).get('stage'),'external_send':False})
        selector.close();emit({'state':'STOPPING','summary':app.status(),'wall_seconds':time.monotonic()-started,'cpu_seconds':time.process_time()-cpu,'max_rss_kib':__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss,'children_cpu_seconds':sum(__import__('resource').getrusage(__import__('resource').RUSAGE_CHILDREN)[:2])-child_cpu,'children_max_rss_kib':__import__('resource').getrusage(__import__('resource').RUSAGE_CHILDREN).ru_maxrss})


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    init=sub.add_parser('init');init.add_argument('--home',type=Path,required=True);init.add_argument('--project',type=Path,required=True);init.add_argument('--demo-materials',action='store_true');init.add_argument('--source',action='append');init.add_argument('--practice');init.add_argument('--heldout');init.add_argument('--transfer');init.add_argument('--allow-local-artifacts',action='store_true');init.add_argument('--document-work',action='store_true');init.add_argument('--allow-local-skills',action='store_true');init.add_argument('--owned-application-profile');init.add_argument('--provider-host',action='append',default=[]);init.add_argument('--remote-privacy',action='append',choices=['PUBLIC','PROJECT','PERSONAL'],default=[]);init.add_argument('--provider-cost-ceiling-micro',type=int,default=0)
    start=sub.add_parser('run');start.add_argument('--home',type=Path,required=True);start.add_argument('--seconds',type=float,default=3600);start.add_argument('--headless',action='store_true');start.add_argument('--live-provider-authorized',action='store_true');start.add_argument('--secret-fd',type=int);start.add_argument('--secret-ref')
    status=sub.add_parser('status');status.add_argument('--home',type=Path,required=True)
    provider=sub.add_parser('provider-command');provider.add_argument('--home',type=Path,required=True);provider.add_argument('--document',type=Path,required=True)
    inspect=sub.add_parser('provider-status');inspect.add_argument('--home',type=Path,required=True)
    start.add_argument('--control',action='store_true')
    init.add_argument('--daily-life',action='store_true');init.add_argument('--timezone',default='UTC')
    health=sub.add_parser('health');health.add_argument('--home',type=Path,required=True)
    control=sub.add_parser('request');control.add_argument('--home',type=Path,required=True)
    backup=sub.add_parser('backup');backup.add_argument('--home',type=Path,required=True);backup.add_argument('--destination',type=Path,required=True)
    transfer=sub.add_parser('transfer');transfer.add_argument('--home',type=Path,required=True);transfer.add_argument('--package',type=Path,required=True);transfer.add_argument('--destination-id',required=True);transfer.add_argument('--source-commit',required=True);transfer.add_argument('--retire-source',action='store_true');transfer.add_argument('--pending-effects',action='store_true')
    receive=sub.add_parser('receive');receive.add_argument('--home',type=Path,required=True);receive.add_argument('--package',type=Path,required=True);receive.add_argument('--sha256',required=True);receive.add_argument('--destination-id',required=True);receive.add_argument('--host-config',type=Path,required=True)
    for parser in (init,start,status,provider,inspect,health,control,backup,transfer,receive):parser.add_argument('--json',action='store_true',help='machine-readable output')
    a=p.parse_args();resolver=None
    global JSON_OUTPUT
    JSON_OUTPUT=a.json
    try:
        if a.action=='receive':
            from .cloud import receive
            from ..continuity.privacy import _json_object
            config=LifeConfig.model_validate_json(json.dumps(json.loads(a.host_config.read_text(),object_pairs_hook=_json_object)))
            emit(receive(a.package,a.home,sha256=a.sha256,destination_id=a.destination_id,config=config));return
        home=home_path(a.home)
        if a.action=='health':
            from .cloud import health
            emit(health(home));return
        if a.action=='request':
            from .control import request,LIMIT
            from ..continuity.privacy import _json_object
            raw=sys.stdin.buffer.read(LIMIT+1)
            if len(raw)>LIMIT:raise CoreError('CLOUD_REQUEST_BOUND')
            emit(request(home,json.loads(raw,object_pairs_hook=_json_object)));return
        if a.action=='backup':
            from .cloud import backup
            from ..continuity import ContinuityStore
            load_config(home)
            with ContinuityStore(home/'subject/self.db',schema_target=13) as store:emit(backup(store,a.destination))
            return
        if a.action=='transfer':
            if not a.retire_source:raise CoreError('CLOUD_SOURCE_RETIREMENT_ACK_REQUIRED')
            from .cloud import transfer
            emit(transfer(home,a.package,destination_id=a.destination_id,source_commit=a.source_commit,pending_effects=a.pending_effects));return
        if a.action in {'provider-command','provider-status'}:
            from .provider import provider_command,provider_status
            emit(provider_command(home,a.document) if a.action=='provider-command' else provider_status(home));return
        if a.action=='status':emit(runtime_status(home/'subject/self.db'));return
        if a.action=='init':
            sources=a.source or (DEMO_SOURCES if a.demo_materials else ())
            training=DEMO_TRAIN if a.demo_materials else (a.practice,a.heldout,a.transfer)
            if not sources or not all(training):raise CoreError('EXPLICIT_PROJECT_MATERIALS_REQUIRED')
            if a.document_work:sources=(*sources,*DOC_SOURCES)
            if a.allow_local_skills and not a.document_work and not a.owned_application_profile:raise CoreError('DOCUMENT_WORK_REQUIRED_FOR_LOCAL_SKILLS')
            from .surfaces import SurfaceBinding
            bindings=tuple(SurfaceBinding(binding_id=k,platform=k,surface='chat.direct',adapter='shadow.local') for k in ('cloud.cli','qq.shadow','bili.shadow')) if a.daily_life else ()
            config=LifeConfig(surface_bindings=bindings,shared_presence=a.daily_life,timezone=a.timezone,owned_application_profile=a.owned_application_profile,document_learning=tuple(material_for(a.project,x) for x in DOC_TRAIN) if a.document_work else (),allow_local_skills=a.allow_local_skills,max_autonomous_materials=len(sources),provider_hosts=tuple(a.provider_host),remote_privacy=tuple(a.remote_privacy),provider_cost_ceiling_micro=a.provider_cost_ceiling_micro,project_root=str(a.project.absolute()),materials=tuple(material_for(a.project,x) for x in sources),practice=material_for(a.project,training[0]),heldout=material_for(a.project,training[1]),transfer=material_for(a.project,training[2]))
            write_config(home,config)
            authority=ProviderConfigurationAuthority();ProviderConfigService(home/'providers.json',authority).initialize(authority)
            with LifeApplication(home,bootstrap_grant=a.allow_local_artifacts) as app:emit({'state':'INITIALIZED','identity_id':app.runtime.identity_id,'local_grant_installed':a.allow_local_artifacts,'config':str(home/'life.json')})
            return
        if not 0<a.seconds<=7*86400:raise CoreError('LIFE_DURATION_BOUND')
        router=None
        if a.live_provider_authorized:
            from .provider import ExplicitFDResolver,configured_router
            if a.secret_fd is None or not a.secret_ref:raise CoreError('EXPLICIT_SECRET_RESOLVER_REQUIRED')
            cfg=load_config(home)
            if not cfg.provider_hosts or not cfg.remote_privacy or cfg.provider_cost_ceiling_micro<=0 or cfg.provider_calls_per_day<=0:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED_OR_BUDGETED')
            resolver=ExplicitFDResolver(a.secret_fd,a.secret_ref);router=configured_router(home,cfg,resolver=resolver,authorized=True)
        elif a.secret_fd is not None or a.secret_ref is not None:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED')
        run(home,a.seconds,headless=a.headless,router=router,control_enabled=a.control)
    except (CoreError,OSError,ValueError) as exc:
        emit({'state':'BLOCKED','code':exc.code if isinstance(exc,CoreError) else 'LIFE_CONFIGURATION_OR_RUNTIME_REJECTED'});raise SystemExit(2) from None
    finally:
        if resolver:resolver.clear()
if __name__=='__main__':main()
