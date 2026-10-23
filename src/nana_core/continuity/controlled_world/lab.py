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
from ..hands.contracts import process_start

KINDS=('documents','feed','api','social')

def _atomic(path,value):
    tmp=path.with_suffix('.tmp')
    with tmp.open('w') as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())
    os.chmod(tmp,0o600);os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

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
            self.host=self.stack.enter_context(OwnedApplication(self.root/'app',tasks=daily_tasks()))
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
    state=json.loads(statefile.read_text()) if statefile.exists() else {'revision':1,'tick':-1,'requests':0,'effects':{},'entries':[]}
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
                if p.exists():p.chmod(0o600);p.unlink()
            if phase!=5:
                p=root/name;p.write_text('{broken' if phase==3 else canonical(state['public']));p.chmod(0o400 if phase==2 else 0o600)
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
            if self.path=='/status':return self.response(200,canonical({'kind':kind,'revision':state['revision'],'requests':state['requests'],'effect_count':len(state['effects']),'effects':state['effects']}).encode())
            if self.path not in {'/source','/fault/delay','/events'}:return self.response(404,b'{}')
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
                if not isinstance(key,str) or not 1<=len(key)<=64 or set(body)-{'operation_id','revision','value'}:raise ValueError()
                if key in state['effects']:return self.response(200,canonical(state['effects'][key]).encode())
                if body['revision']!=state['revision']:return self.response(409,b'{"error":"STALE_REVISION"}')
                if self.path not in {'/task','/task/drop','/task/partial'}:return self.response(404,b'{}')
                if len(state['effects'])>=128:return self.response(429,b'{"error":"BOUND"}')
                state['revision']+=1;receipt={'operation_id':key,'revision':state['revision'],'partial':self.path.endswith('partial'),'value':str(body.get('value',''))[:256]}
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
