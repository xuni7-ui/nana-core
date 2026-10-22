"""Finite browser-like Hand for an explicitly owned local application.

HTML navigation is read-only. Form submission is only world.publish through the
existing Kernel/HandsEffectContext. Verify uses original Unix query + disk, not
the HTTP acknowledgement. No arbitrary URL, login, JavaScript or browser agent.
"""
import argparse,html,json,os,socket,struct,urllib.parse,urllib.request
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


class OwnedBrowserPort(OwnedApplicationPort):
    def __init__(self,identity_id,target,endpoint,*,host_enabled=False):
        super().__init__(identity_id,target,host_enabled=host_enabled)
        self.endpoint=endpoint
        if not 1024<=endpoint.port<=65535:raise CoreError('BROWSER_ENDPOINT_DENIED')
        self._assert_browser()
    def _assert_browser(self):
        e=self.endpoint
        if process_start(e.pid)!=e.start or Path('/proc/'+str(e.pid)).stat().st_uid!=os.getuid():raise CoreError('BROWSER_OWNER_CHANGED')
        self.assert_owned()
    def _http(self,path,body=None):
        self._assert_browser()
        if path!='/' and not path.startswith(('/tasks/','/api/')):raise CoreError('BROWSER_NAVIGATION_DENIED')
        raw=canonical(body).encode() if body is not None else None
        if raw and len(raw)>16384:raise CoreError('HANDS_REQUEST_BOUND')
        request=urllib.request.Request('http://127.0.0.1:'+str(self.endpoint.port)+path,data=raw,headers={'Content-Type':'application/json'})
        from ..open_life.sources import NoRedirect
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        try:
            with opener.open(request,timeout=.5) as response:
                result=response.read(32769)
                if response.status!=200 or len(result)>32768:raise CoreError('BROWSER_COMPLETION_UNKNOWN')
        except OSError:raise CoreError('BROWSER_COMPLETION_UNKNOWN') from None
        return result
    def open(self):return self._http('/').decode()
    def navigate(self,task_id):
        if task_id not in self.tasks:raise CoreError('BROWSER_NAVIGATION_DENIED')
        return self._http('/tasks/'+task_id).decode()
    def _request(self,channel,body):
        if channel=='query':return super()._request(channel,body)
        value=json.loads(self._http('/api/control',{'binding':self.target.binding,**body}))
        if value.get('ok') is not True or set(value)!={'ok','data'} or type(value['data']) is not dict:raise CoreError('BROWSER_COMPLETION_UNKNOWN')
        return value['data']
    def _pure(self,inv,key,args):
        if inv.capability=='world.observe':
            page=self.navigate(key)
            if 'data-task="'+key+'"' not in page or '<form' not in page:raise CoreError('BROWSER_PAGE_BINDING_CHANGED')
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


def serve(profile):
    target=load_target(profile)
    # A transport bridge, no Subject/Store/Runtime/decisions in this process.
    port=OwnedApplicationPort('transport-no-subject-authority',target,host_enabled=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,body,content='application/json'):
            self.send_response(status);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/':
                page='<html><body>'+''.join('<a href="/tasks/'+t+'">'+html.escape(t)+'</a>' for t in port.tasks)+'</body></html>'
                return self.respond(200,page.encode(),'text/html')
            if self.path.startswith('/tasks/'):
                key=self.path.removeprefix('/tasks/')
                if key not in port.tasks:return self.respond(404,b'{}')
                data=port.peek(key);state=data['state']
                page='<html><body data-task="'+key+'"><form method="post" action="/api/control">'
                page+=''.join('<input name="'+html.escape(k)+'" value="'+html.escape(v,quote=True)+'">' for k,v in state['values'].items())
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
                self.respond(200,canonical({'ok':True,'data':value}).encode())
            except (CoreError,ValueError,OSError,KeyError,TypeError):self.respond(400,b'{"ok":false}')
    server=HTTPServer(('127.0.0.1',0),Handler);server.timeout=.5
    print(canonical(BrowserEndpoint(port=server.server_port,pid=os.getpid(),start=process_start(os.getpid())).model_dump(mode='json')),flush=True)
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',type=Path,required=True)
    serve(parser.parse_args().profile)
if __name__=='__main__':main()
