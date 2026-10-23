"""Finite browser-like Hand for an explicitly owned local application.

HTML navigation is read-only. Form submission is only world.publish through the
existing Kernel/HandsEffectContext. Verify uses original Unix query + disk, not
the HTTP acknowledgement. No arbitrary URL, login, JavaScript or browser agent.
"""
import argparse,html,json,os,urllib.request,urllib.parse,urllib.error,subprocess,sys,selectors
from pydantic import Field
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from ...contracts import DTO,CoreError
from ...storage import canonical
from .contracts import load_target,process_start
from .port import OwnedApplicationPort
from .framing import receive_object


class BrowserEndpoint(DTO):
    port:int
    pid:int
    start:str
    paths:tuple[str,...]=Field(default=(),max_length=16)
    timeout_ms:int=Field(default=500,ge=50,le=1500)
    request_cap:int=Field(default=128,ge=1,le=512)


class OwnedBrowser:
    """Trusted development host constructor; owns only its new bridge child."""
    def __init__(self,profile,*,dynamic=False,drop_ack_tasks=()):
        boot="import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('nana_core.continuity.hands.browser',run_name='__main__')"
        self.proc=subprocess.Popen([sys.executable,'-I','-c',boot,str(Path(__file__).resolve().parents[3]),'--profile',str(profile),*(['--dynamic'] if dynamic else []),*sum((['--drop-ack',k] for k in drop_ack_tasks),[])],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={'PATH':os.defpath,'LANG':'C.UTF-8','TZ':'UTC'})
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(self.proc.stdout,selectors.EVENT_READ)
                if not selector.select(5):raise CoreError('BROWSER_START_TIMEOUT')
                self.endpoint=BrowserEndpoint.model_validate_json(self.proc.stdout.readline(1024))
                if self.endpoint.pid!=self.proc.pid:raise CoreError('BROWSER_OWNER_CHANGED')
        except BaseException:self.close();raise
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(2)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(2)
        if self.proc.stdout:self.proc.stdout.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class OwnedBrowserPort(OwnedApplicationPort):
    def __init__(self,identity_id,target,endpoint,*,host_enabled=False):
        super().__init__(identity_id,target,host_enabled=host_enabled)
        self.endpoint=endpoint;self.requests=0
        if not 1024<=endpoint.port<=65535:raise CoreError('BROWSER_ENDPOINT_DENIED')
        self._assert_browser()
    def _assert_browser(self):
        e=self.endpoint
        if process_start(e.pid)!=e.start or Path('/proc/'+str(e.pid)).stat().st_uid!=os.getuid():raise CoreError('BROWSER_OWNER_CHANGED')
        # Bind the listening socket to this exact owned PID, not merely to an
        # arbitrary other localhost service paired with a legitimate PID value.
        try:
            owned=set()
            for fd in list(Path('/proc/'+str(e.pid)+'/fd').iterdir())[:64]:
                try:owned.add(os.readlink(fd))
                except OSError:pass
            match=False
            for line in Path('/proc/'+str(e.pid)+'/net/tcp').read_text().splitlines()[1:]:
                fields=line.split()
                if fields[1]=='0100007F:'+format(e.port,'04X') and fields[3]=='0A' and 'socket:['+fields[9]+']' in owned:match=True
            if not match:raise CoreError('BROWSER_LISTENER_OWNER_MISMATCH')
        except OSError:raise CoreError('BROWSER_OWNER_CHANGED') from None
        self.assert_owned()
    def _allowed_path(self,path):
        if not isinstance(path,str) or not path.startswith('/') or len(path)>256 or any(x in path for x in ('%','\\','?','#','..','//')):raise CoreError('BROWSER_NAVIGATION_DENIED')
        allowed=('/', '/api/control',*('/tasks/'+key for key in self.tasks),*self.endpoint.paths)
        if path not in allowed:raise CoreError('BROWSER_NAVIGATION_DENIED')
        return path
    def _http(self,path,body=None):
        self._assert_browser();self._allowed_path(path)
        raw=canonical(body).encode() if body is not None else None
        if raw and (len(raw)>16384 or path!='/api/control'):raise CoreError('HANDS_REQUEST_BOUND')
        from ..open_life.sources import NoRedirect
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        for hop in range(4):
            if self.requests>=self.endpoint.request_cap:raise CoreError('BROWSER_REQUEST_CAP')
            self.requests+=1;url='http://127.0.0.1:'+str(self.endpoint.port)+path
            request=urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json'})
            try:
                with opener.open(request,timeout=self.endpoint.timeout_ms/1000) as response:
                    result=response.read(32769)
                    if response.status!=200 or len(result)>32768:raise CoreError('BROWSER_COMPLETION_UNKNOWN')
                    return result
            except urllib.error.HTTPError as exc:
                if raw is None and exc.code in {301,302,303,307,308} and hop<3:
                    target=urllib.parse.urlsplit(urllib.parse.urljoin(url,exc.headers.get('Location','')))
                    if target.scheme!='http' or target.hostname!='127.0.0.1' or target.port!=self.endpoint.port or target.username or target.password or target.query or target.fragment:raise CoreError('BROWSER_REDIRECT_DENIED') from None
                    path=self._allowed_path(target.path);continue
                raise CoreError('BROWSER_HTTP_'+str(exc.code) if raw is None else 'BROWSER_COMPLETION_UNKNOWN') from None
            except OSError:raise CoreError('BROWSER_COMPLETION_UNKNOWN') from None
        raise CoreError('BROWSER_REDIRECT_BOUND')
    def open_url(self,url):
        target=urllib.parse.urlsplit(url)
        if target.scheme!='http' or target.hostname!='127.0.0.1' or target.port!=self.endpoint.port or target.username or target.password or target.query or target.fragment:raise CoreError('BROWSER_NAVIGATION_DENIED')
        return self.page(target.path or '/')
    def page(self,path='/'):
        from .page import parse_page
        return parse_page(path,self._http(path))
    def follow(self,page,href):
        from .page import PageState
        if type(page) is not PageState or href not in {link.href for link in page.links}:raise CoreError('BROWSER_LINK_NOT_OBSERVED')
        # The new read is another observation; a link or success-shaped text is
        # never an action outcome. Stale forms are fenced again by Kernel revision.
        base='http://127.0.0.1:'+str(self.endpoint.port)+page.path
        return self.open_url(urllib.parse.urljoin(base,href))
    def open(self):return self._http('/').decode()
    def navigate(self,task_id):
        if task_id not in self.tasks:raise CoreError('BROWSER_NAVIGATION_DENIED')
        return self._http('/tasks/'+task_id).decode()
    def _request(self,channel,body):
        if channel=='query':return super()._request(channel,body)
        # Distinct reviewed Hand transport: files/documents retain original
        # owned IPC and file reopen Verify; forms use the browser HTTP bridge.
        if self.endpoint.paths and self.tasks[body['task_id']].kind!='FORM':return super()._request(channel,body)
        value=json.loads(self._http('/api/control',{'binding':self.target.binding,**body}))
        if value.get('ok') is not True or set(value)!={'ok','data'} or type(value['data']) is not dict:raise CoreError('BROWSER_COMPLETION_UNKNOWN')
        return value['data']
    def _pure(self,inv,key,args):
        if inv.capability=='world.observe':
            page=self.page('/tasks/'+key)
            if page.task_id!=key or page.error or not page.forms:raise CoreError('BROWSER_PAGE_BINDING_CHANGED')
            if self.tasks[key].kind=='FORM' and not set(self.tasks[key].fields)<=set(page.forms[0].fields):raise CoreError('BROWSER_FORM_STATE_CHANGED')
        result=super()._pure(inv,key,args)
        if inv.capability in {'world.compute','world.skill'} and self.tasks[key].kind=='FORM':
            from ..open_life.capabilities import EmbodiedGesture,EmbodiedProposal,compile_simulated_form
            from ...storage import digest
            prepared=result['data'];gestures=[EmbodiedGesture(operation='FOCUS_APP',target=key)]
            for command in prepared['commands']:
                if command['op']=='SET_FIELD':gestures.extend((EmbodiedGesture(operation='CLICK',target=command['field']),EmbodiedGesture(operation='TYPE',text=command['value'])))
                elif command['op']=='SUBMIT':gestures.append(EmbodiedGesture(operation='CLICK',target='submit'))
            gestures.extend((EmbodiedGesture(operation='READ_RESULT'),EmbodiedGesture(operation='VERIFY_STATE')))
            observation={'task':self.tasks[key].model_dump(mode='json'),'state':{'revision':prepared['revision']}}
            proposal=EmbodiedProposal(target_task_id=key,source_revision=prepared['revision'],observation_digest=digest(observation),gestures=tuple(gestures))
            result['data']=compile_simulated_form(observation,proposal)
            result['embodied_simulation']={'gesture_count':len(gestures),'realm':'OWNED_FORM_SIMULATOR_NOT_USER_DEVICE','execution_authority':False}
        return result


def serve(profile,*,dynamic=False,drop_ack_tasks=()):
    target=load_target(profile)
    # A transport bridge, no Subject/Store/Runtime/decisions in this process.
    port=OwnedApplicationPort('transport-no-subject-authority',target,host_enabled=True)
    if any(k not in port.tasks for k in drop_ack_tasks):raise CoreError('FAULT_TASK_NOT_OWNED')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,body,content='application/json'):
            self.send_response(status);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if dynamic and self.path=='/welcome':
                self.send_response(302);self.send_header('Location','/page/1');self.end_headers();return
            if dynamic and self.path=='/outside':
                self.send_response(302);self.send_header('Location','http://example.invalid/');self.end_headers();return
            if dynamic and self.path=='/error':return self.respond(200,b'<html><p role="alert">Temporary failure</p></html>','text/html')
            if dynamic and self.path=='/malformed':return self.respond(200,b'<html><form>success</html>','text/html')
            if dynamic and self.path in {'/page/1','/page/2'}:
                keys=list(port.tasks);n=0 if self.path.endswith('1') else 1
                page='<html><title>Owned project workspace</title><body>'+''.join('<a href="/tasks/'+k+'">Review '+html.escape(k)+'</a>' for k in keys[n::2])+'<a href="/page/'+('2' if n==0 else '1')+'">Next page</a></body></html>'
                return self.respond(200,page.encode(),'text/html')
            if self.path=='/':
                page='<html><body>'+''.join('<a href="/tasks/'+t+'">'+html.escape(t)+'</a>' for t in port.tasks)+'</body></html>'
                return self.respond(200,page.encode(),'text/html')
            if self.path.startswith('/tasks/'):
                key=self.path.removeprefix('/tasks/')
                if key not in port.tasks:return self.respond(404,b'{}')
                data=port.peek(key);state=data['state']
                page='<html><title>Review '+html.escape(key)+'</title><body data-task="'+key+'" data-revision="'+str(state['revision'])+'"><form method="post" action="/api/control">'
                page+=''.join('<input name="'+html.escape(k)+'" value="'+html.escape(v,quote=True)+'">' for k,v in (reversed(list(state['values'].items())) if dynamic and state['revision']%2 else state['values'].items()))
                page+='<textarea>'+html.escape(state['text'])+'</textarea><button>Apply</button></form></body></html>'
                return self.respond(200,page.encode(),'text/html')
            self.respond(404,b'{}')
        def do_POST(self):
            if self.path!='/api/control':return self.respond(404,b'{}')
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 1<=n<=16384:raise ValueError('bound')
                req=json.loads(self.rfile.read(n))
                if req.pop('binding',None)!=target.binding:raise ValueError('binding')
                value=port._request('control',req)
                if req['task_id'] in drop_ack_tasks:
                    import socket
                    self.connection.shutdown(socket.SHUT_RDWR);return
                self.respond(200,canonical({'ok':True,'data':value}).encode())
            except (CoreError,ValueError,OSError,KeyError,TypeError):self.respond(400,b'{"ok":false}')
    server=HTTPServer(('127.0.0.1',0),Handler);server.timeout=.5
    print(canonical(BrowserEndpoint(port=server.server_port,pid=os.getpid(),start=process_start(os.getpid()),paths=('/page/1','/page/2','/welcome','/outside','/error','/malformed') if dynamic else (),request_cap=512 if dynamic else 128).model_dump(mode='json')),flush=True)
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--dynamic',action='store_true');parser.add_argument('--drop-ack',action='append',default=[]);a=parser.parse_args()
    serve(a.profile,dynamic=a.dynamic,drop_ack_tasks=tuple(a.drop_ack))
if __name__=='__main__':main()
