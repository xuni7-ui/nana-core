"""Standalone foreground life. No AstrBot, QQ, capture, production or social send."""
import argparse,json,os,selectors,signal,sys,time
from collections import deque
from pathlib import Path
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
        material=next((m for m in app.config.materials if parts[1] in {m.material_id,m.relative_path,Path(m.relative_path).name}),None)
        if not material:raise CoreError('PROJECT_MATERIAL_NOT_CONFIGURED')
        return {'source_memory_id':app.work.request(material.material_id),'state':'OFFERED_TO_ORIGINAL_C_NOT_FORCED_ADOPTION'}
    return {'commands':['/status','/life','/journal','/activities','/sources','/pause','/resume','/busy','/available','/work <approved filename>','/topic <key> <text>','/forget <memory-id>','/revoke','/quit'],'ordinary_text':'type a normal sentence; provider off by default'}


def run(home,seconds,*,headless=False,router=None):
    config=load_config(home);resource=apply_resource_limits(config);started=time.monotonic();cpu=time.process_time();child=__import__('resource').getrusage(__import__('resource').RUSAGE_CHILDREN);child_cpu=child.ru_utime+child.ru_stime
    with LifeApplication(home,router=router) as app:
        emit({'state':'STARTED','identity_id':app.runtime.identity_id,'mode':'OFFLINE_LIMITED' if router is None else 'PROVIDER_CONFIGURED_NOT_QUALIFIED','resources':resource,'commands':'/help; ordinary text; /status','autonomous_materials':len(config.materials[:config.max_autonomous_materials])})
        def stop(*unused):app.runtime.request_stop()
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        selector=selectors.SelectSelector()
        if not headless:selector.register(sys.stdin,selectors.EVENT_READ)
        pending=deque();buffer=b'';eof=False;discard=False
        while not app.runtime.stop_requested and time.monotonic()-started<seconds:
            ready=selector.select(0 if pending else max(.1,min(1.,app.runtime.next_wait_seconds())))
            if ready:
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
            value=app.tick()
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
    for parser in (init,start,status,provider,inspect):parser.add_argument('--json',action='store_true',help='machine-readable output')
    a=p.parse_args();resolver=None
    global JSON_OUTPUT
    JSON_OUTPUT=a.json
    try:
        home=home_path(a.home)
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
            config=LifeConfig(owned_application_profile=a.owned_application_profile,document_learning=tuple(material_for(a.project,x) for x in DOC_TRAIN) if a.document_work else (),allow_local_skills=a.allow_local_skills,max_autonomous_materials=len(sources),provider_hosts=tuple(a.provider_host),remote_privacy=tuple(a.remote_privacy),provider_cost_ceiling_micro=a.provider_cost_ceiling_micro,project_root=str(a.project.absolute()),materials=tuple(material_for(a.project,x) for x in sources),practice=material_for(a.project,training[0]),heldout=material_for(a.project,training[1]),transfer=material_for(a.project,training[2]))
            write_config(home,config)
            authority=ProviderConfigurationAuthority();ProviderConfigService(home/'providers.json',authority).initialize(authority)
            with LifeApplication(home,bootstrap_grant=a.allow_local_artifacts) as app:emit({'state':'INITIALIZED','identity_id':app.runtime.identity_id,'local_grant_installed':a.allow_local_artifacts,'config':str(home/'life.json')})
            return
        if not 0<a.seconds<=86400:raise CoreError('LIFE_DURATION_BOUND')
        router=None
        if a.live_provider_authorized:
            from .provider import ExplicitFDResolver,configured_router
            if a.secret_fd is None or not a.secret_ref:raise CoreError('EXPLICIT_SECRET_RESOLVER_REQUIRED')
            cfg=load_config(home)
            if not cfg.provider_hosts or not cfg.remote_privacy or cfg.provider_cost_ceiling_micro<=0 or cfg.provider_calls_per_day<=0:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED_OR_BUDGETED')
            resolver=ExplicitFDResolver(a.secret_fd,a.secret_ref);router=configured_router(home,cfg,resolver=resolver,authorized=True)
        elif a.secret_fd is not None or a.secret_ref is not None:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED')
        run(home,a.seconds,headless=a.headless,router=router)
    except (CoreError,OSError,ValueError) as exc:
        emit({'state':'BLOCKED','code':exc.code if isinstance(exc,CoreError) else 'LIFE_CONFIGURATION_OR_RUNTIME_REJECTED'});raise SystemExit(2) from None
    finally:
        if resolver:resolver.clear()
if __name__=='__main__':main()
