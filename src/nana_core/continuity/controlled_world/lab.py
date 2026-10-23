"""Five independent real local services; timed changes are not planner answers.

The website bridges an original owned app (sixth child). Other processes expose
bounded document/feed/API/social observations. Operational state is environment
state, never another Subject Store. Controller mutation is harness-only.
"""
import argparse,json,os,selectors,subprocess,sys,time,hashlib,socket
from contextlib import ExitStack
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from ...contracts import CoreError
from ...storage import canonical
from ..hands.host import OwnedApplication,daily_tasks
from ..hands.browser import OwnedBrowser
from ..hands.contracts import process_start,ApplicationTask

KINDS=('documents','feed','api','social')

def _atomic(path,value):
    from ..hands.server import atomic
    from ..hands.contracts import private_directory
    root=private_directory(path.parent)
    directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:atomic(path,canonical(value).encode(),directory)
    finally:os.close(directory)

class LabService:
    def __init__(self,root,kind,*,seed=7,interval=30):
        self.root=Path(root).absolute();self.root.mkdir(mode=0o700,parents=True,exist_ok=False)
        boot="import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('nana_core.continuity.controlled_world.lab',run_name='__main__')"
        self.proc=subprocess.Popen([sys.executable,'-I','-c',boot,str(Path(__file__).resolve().parents[3]),'--root',str(self.root),'--kind',kind,'--seed',str(seed),'--interval',str(interval)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={'PATH':os.defpath,'LANG':'C.UTF-8','TZ':'UTC'})
        try:
            with selectors.DefaultSelector() as s:
                s.register(self.proc.stdout,selectors.EVENT_READ)
                if not s.select(5):raise CoreError('LAB_START_TIMEOUT')
                self.endpoint=json.loads(self.proc.stdout.readline(2048))
            if self.endpoint['pid']!=self.proc.pid:raise CoreError('LAB_OWNER_CHANGED')
        except BaseException:self.close();raise
    @property
    def url(self):return 'http://127.0.0.1:'+str(self.endpoint['port'])
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(2)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(2)
        if self.proc.stdout:self.proc.stdout.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class ControlledWorld:
    def __init__(self,root,*,seed=7,interval=30):
        self.root=Path(root).absolute();self.root.mkdir(mode=0o700,parents=True,exist_ok=False);self.stack=ExitStack()
        try:
            tasks=list(daily_tasks());tasks[4:4]=[ApplicationTask(task_id='document-new-transfer',kind='DOCUMENT',initial='Prior note: ',wanted='A bounded revised project note',context='handoff'),ApplicationTask(task_id='form-new-transfer',kind='FORM',wanted={'label':'reviewed'},fields=('other','label'),context='project-review')]
            self.host=self.stack.enter_context(OwnedApplication(self.root/'app',tasks=tuple(tasks)))
            self.browser=self.stack.enter_context(OwnedBrowser(self.host.profile,dynamic=True))
            self.services={k:self.stack.enter_context(LabService(self.root/k,k,seed=seed,interval=interval)) for k in KINDS}
            self.manifest={'scope':'OWNED_LOCALHOST_ONLY','website':self.browser.endpoint.model_dump(mode='json'),'services':{k:s.endpoint for k,s in self.services.items()},'backend_pid':self.host.proc.pid,'independent_service_processes':5,'subject_in_lab':False,'seed':seed,'change_interval_seconds':interval}
            _atomic(self.root/'lab-manifest.json',self.manifest)
        except BaseException:self.stack.close();raise
    def close(self):self.stack.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def serve(root,kind,seed,interval):
    root=Path(root);statefile=root/'environment.json';started=time.monotonic();start_us=time.time_ns()//1000
    state=json.loads(statefile.read_text()) if statefile.exists() else {'revision':1,'tick':-1,'requests':0,'effects':{},'tasks':{}}
    def evolve():
        tick=int((time.monotonic()-started)//interval)
        if tick==state['tick']:return
        state['tick']=tick;state['revision']+=1
        # Timed environment changes, no access to Subject state/driver answers.
        phase=(tick+seed)%6;value=('review-needed','review-needed','published','inconsistent','corrected','withdrawn')[phase]
        now=time.time_ns()//1000
        state['public']={'source':kind,'revision':state['revision'],'phase':phase,'world_claim':{'entity_id':'project-user','predicate':'lab.project-status','kind':'INTERPRETED','value':value,'valid_from_us':now,'valid_until_us':now+int(interval*2*1e6),'confidence':.55},'lifecycle':'WITHDRAWN' if value=='withdrawn' else 'CURRENT','not_authority':True}
        if kind=='documents':
            # Material version/rename/corruption are observable, not hidden oracle.
            name='status-new.json' if phase>=3 else 'status.json'
            for old in ('status.json','status-new.json'):
                p=root/old
                if p.exists() or p.is_symlink():p.unlink()
            if phase!=5:
                p=root/name
                if phase==3:
                    from ..hands.server import atomic
                    directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    try:atomic(p,b'{broken',directory)
                    finally:os.close(directory)
                else:_atomic(p,state['public'])
                fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
                try:os.fchmod(fd,0o400 if phase==2 else 0o600)
                finally:os.close(fd)
        _atomic(statefile,state)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def response(self,status,raw):
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
            try:self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_GET(self):
            evolve();state['requests']+=1;_atomic(statefile,state)
            if self.path=='/fault/500':return self.response(500,b'{"error":"TEMPORARY"}')
            if self.path=='/fault/malformed':return self.response(200,b'{broken')
            if self.path=='/fault/drop':self.connection.shutdown(socket.SHUT_RDWR);return
            if self.path=='/fault/delay':time.sleep(1.3)
            if self.path.startswith('/tasks/'):
                task=state['tasks'].get(self.path.removeprefix('/tasks/'))
                return self.response(200,canonical(task).encode()) if task else self.response(404,b'{}')
            if self.path=='/status':return self.response(200,canonical({'kind':kind,'revision':state['revision'],'requests':state['requests'],'effect_count':len(state['effects']),'effects':state['effects']}).encode())
            if self.path not in {'/source','/fault/delay','/events'}:return self.response(404,b'{}')
            if kind=='documents':
                name='status-new.json' if state['public']['phase']>=3 else 'status.json'
                try:
                    fd=os.open(root/name,os.O_RDONLY|os.O_NOFOLLOW)
                    with os.fdopen(fd,'rb') as f:raw=f.read(32769)
                    if len(raw)>32768:return self.response(413,b'{}')
                    return self.response(200,raw)
                except OSError:return self.response(410,b'{"lifecycle":"WITHDRAWN"}')
            public=dict(state['public'])
            if kind=='social':public['messages']=[{'message_id':str(state['tick']), 'thread_id':'lab-project','text':'Project status changed','occurred_at_us':start_us+state['tick']*int(interval*1e6),'sequence':state['tick'],'duplicate_delivery':True,'quiet_period':state['tick']%3==0}]
            if kind=='feed':public['noise']=[{'topic':'trivial-'+str(i),'value':0} for i in range(min(8,state['tick']+1))]
            return self.response(200,canonical(public).encode())
        def do_POST(self):
            # Harness-only owned task API. No API credentials, accounts or Subject.
            evolve()
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 1<=n<=4096:raise ValueError()
                body=json.loads(self.rfile.read(n));key=body['operation_id']
                if not isinstance(key,str) or not 1<=len(key)<=64 or set(body)-{'operation_id','revision','value','operation','task_id','expected_task_revision'}:raise ValueError()
                if key in state['effects']:
                    if state['effects'][key]['request_digest']!=hashlib.sha256(canonical(body).encode()).hexdigest():return self.response(409,b'{"error":"IDEMPOTENCY_COLLISION"}')
                    return self.response(200,canonical(state['effects'][key]).encode())
                if body['revision']!=state['revision']:return self.response(409,b'{"error":"STALE_REVISION"}')
                if self.path not in {'/task','/task/drop','/task/partial'}:return self.response(404,b'{}')
                if len(state['effects'])>=128:return self.response(429,b'{"error":"BOUND"}')
                task_id=body.get('task_id',key);operation=body.get('operation','CREATE');old_task=state['tasks'].get(task_id)
                if not isinstance(task_id,str) or not task_id.isidentifier() or len(task_id)>32:raise ValueError()
                if operation not in {'CREATE','UPDATE'}:raise ValueError()
                if operation=='CREATE' and old_task:return self.response(409,b'{"error":"TASK_EXISTS"}')
                if operation=='UPDATE' and (not old_task or body.get('expected_task_revision')!=old_task['revision']):return self.response(409,b'{"error":"STALE_TASK_REVISION"}')
                state['revision']+=1;value=str(body.get('value',''))[:256];partial=self.path.endswith('partial')
                state['tasks'][task_id]={'task_id':task_id,'revision':1 if old_task is None else old_task['revision']+1,'value':value[:len(value)//2] if partial else value,'partial':partial}
                receipt={'operation_id':key,'revision':state['revision'],'task':state['tasks'][task_id],'partial':partial,'request_digest':hashlib.sha256(canonical(body).encode()).hexdigest()}
                state['effects'][key]=receipt;_atomic(statefile,state)
                if self.path.endswith('drop'):self.connection.shutdown(socket.SHUT_RDWR);return
                return self.response(200,canonical(receipt).encode())
            except (KeyError,ValueError,TypeError):return self.response(400,b'{}')
    server=HTTPServer(('127.0.0.1',0),Handler)
    evolve();print(canonical({'kind':kind,'port':server.server_port,'pid':os.getpid(),'start':process_start(os.getpid())}),flush=True)
    server.timeout=.1
    try:
        while True:evolve();server.handle_request()
    finally:server.server_close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--kind',choices=KINDS,required=True);p.add_argument('--seed',type=int,default=7);p.add_argument('--interval',type=float,default=30);a=p.parse_args()
    if not 0.05<=a.interval<=86400:p.error('bounded interval required')
    serve(a.root,a.kind,a.seed,a.interval)
if __name__=='__main__':main()
