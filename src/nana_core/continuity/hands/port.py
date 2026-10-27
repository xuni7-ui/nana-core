"""Sealed opt-in owned-process boundary. No global input or arbitrary paths."""
import json,os,socket,stat,struct,time
from pathlib import Path
from ...contracts import CoreError,Receipt,Verification
from ...storage import canonical,digest
from ..open_agency.world import LocalWorldRegistry,transform
from .contracts import OwnedTarget,HandsEffectContext,private_directory,process_start
from .framing import receive_object

class OwnedApplicationPort:
    evidence_namespace='recorded.project.owned-application-action'
    def __init__(self,identity_id,target,*,host_enabled=False):
        if type(target) is not OwnedTarget or host_enabled is not True:raise CoreError('OWNED_APPLICATION_OPT_IN_REQUIRED')
        self.identity_id,self.target=identity_id,target;self.permitted_privacy=('PROJECT',);self.code_skills=None
        self.tasks={t.task_id:t for t in target.tasks};self.context_provider=None
        from ...execution_context.contracts import ContextBinding
        from ...execution_context.probe import LocalContextProbe
        from ...execution_context.routing import require_identity
        self._execution_probe=LocalContextProbe(ContextBinding(target_id='owned-application',binding_id='hands.local'))
        context=self._execution_probe.capture();require_identity(context)
        self._execution_context_id=context.context_id
        self._directory_device=private_directory(target.workspace).stat().st_dev
        self.assert_owned()
    def assert_owned(self):
        t=self.target;root=private_directory(t.workspace)
        from ...execution_context.routing import require_identity
        context=self._execution_probe.capture();require_identity(context)
        if context.context_id!=self._execution_context_id or root.stat().st_dev!=self._directory_device:
            raise CoreError('HANDS_EXECUTION_CONTEXT_CHANGED')
        try:
            for namespace in ('user','mnt'):
                if os.readlink(f'/proc/{t.pid}/ns/{namespace}')!=os.readlink(f'/proc/self/ns/{namespace}'):
                    raise CoreError('HANDS_TARGET_NAMESPACE_MISMATCH')
        except OSError:raise CoreError('HANDS_TARGET_CONTEXT_UNAVAILABLE') from None
        if root.stat().st_ino!=t.directory_inode or t.uid!=os.getuid() or process_start(t.pid)!=t.process_start:raise CoreError('HANDS_OWNERSHIP_CHANGED')
        try:
            if Path(f'/proc/{t.pid}').stat().st_uid!=t.uid:raise CoreError('HANDS_OWNERSHIP_CHANGED')
            for name,inode in [('control',t.control_inode),('query',t.query_inode)]:
                s=(root/(name+'.sock')).lstat()
                if not stat.S_ISSOCK(s.st_mode) or s.st_ino!=inode or s.st_uid!=t.uid or s.st_mode&0o077:raise CoreError('HANDS_SOCKET_CHANGED')
        except OSError:raise CoreError('HANDS_TARGET_UNAVAILABLE') from None
        return root
    def execution_evidence(self):
        """Current local IPC realm; numeric UID and path never imply host access."""
        root=self.assert_owned();context=self._execution_probe.capture()
        return {'source_context_id':context.context_id,'target_context_id':context.context_id,
                'target_id':'owned-application','actual_path':str(root),'transport':'LOCAL_OWNED_IPC',
                'observed_at_us':context.observed_at_us,'directory_device':root.stat().st_dev,
                'directory_inode':root.stat().st_ino,'uid':context.euid,
                'user_namespace':context.user_namespace,'mount_namespace':context.mount_namespace,
                'host_identity':'UNKNOWN','execution_authority':False}
    def _request(self,channel,body):
        root=self.assert_owned();body={'binding':self.target.binding,**body};raw=canonical(body).encode()+b'\n'
        if len(raw)>16384:raise CoreError('HANDS_REQUEST_BOUND')
        with socket.socket(socket.AF_UNIX) as s:
            s.settimeout(.5);s.connect(str(root/(channel+'.sock')))
            pid,uid,_=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if (pid,uid)!=(self.target.pid,self.target.uid):raise CoreError('HANDS_PEER_IDENTITY_CHANGED')
            self.assert_owned() # immediate TOCTOU recheck after connection, before effect
            s.sendall(raw)
            try:value=receive_object(s,limit=32768,seconds=.5)
            except ValueError:raise CoreError('HANDS_COMPLETION_UNKNOWN') from None
        if not value.get('ok'):raise CoreError('HANDS_APPLICATION_REJECTED')
        if value.get('ok') is not True or set(value)!={'ok','data'} or type(value['data']) is not dict:raise CoreError('HANDS_COMPLETION_UNKNOWN')
        return value['data']
    def peek(self,key,effect_id=None):
        if key not in self.tasks:raise CoreError('HANDS_TASK_SCOPE_DENIED')
        return self._request('query',{'task_id':key,**({'effect_id':effect_id} if effect_id else {})})
    def _valid(self,inv):
        args=LocalWorldRegistry().validate(inv.capability,inv.resource,inv.args)
        prefix='hands://'+self.target.instance_id+'/'
        if not inv.resource.startswith(prefix):raise CoreError('HANDS_TARGET_SCOPE_DENIED')
        parts=inv.resource[len(prefix):].split('/')
        if len(parts)!=2 or parts[0] not in self.tasks or parts[1] not in {'source','commands','effect'}:raise CoreError('HANDS_RESOURCE_DENIED')
        if inv.capability not in {'source':{'world.observe'},'commands':{'world.compute','world.skill'},'effect':{'world.publish'}}[parts[1]]:raise CoreError('HANDS_OPERATION_DENIED')
        if 'PROJECT' not in self.permitted_privacy or args.get('data_privacy','PROJECT')!='PROJECT':raise CoreError('HANDS_PRIVACY_DENIED')
        self.assert_owned();return parts[0],args
    def _command_data(self,key,args):
        task=self.tasks[key];data=args['data']
        if type(data)!=dict or data.get('task_id')!=key or type(data.get('revision'))!=int or set(data)!={'task_id','revision','commands'}:raise CoreError('HANDS_PREPARED_COMMANDS_REQUIRED')
        if not 1<=len(data['commands'])<=9:raise CoreError('HANDS_EFFECT_BOUND')
        for c in data['commands']:
            if task.kind in {'DOCUMENT','CONTENT'}:
                if set(c)!={'op','value'} or c['op'] not in {'APPEND','REPLACE'} or c['value'] not in {task.wanted,task.wanted.strip()}:raise CoreError('HANDS_EFFECT_SCOPE_DENIED')
            elif task.kind=='FILES':
                if set(c)!={'op','source','destination'} or c['op']!='MOVE' or task.wanted.get(c['source'])!=c['destination']:raise CoreError('HANDS_EFFECT_SCOPE_DENIED')
            elif c.get('op')=='SET_FIELD':
                if set(c)!={'op','field','value'} or c['field'] not in task.fields or c['value'] not in {*task.wanted.values(),''}:raise CoreError('HANDS_EFFECT_SCOPE_DENIED')
            elif c!={'op':'SUBMIT'}:raise CoreError('HANDS_EFFECT_SCOPE_DENIED')
        return data
    def preflight(self,capability,resource,args):
        from types import SimpleNamespace
        key,args=self._valid(SimpleNamespace(capability=capability,resource=resource,args=args))
        if capability=='world.publish':
            data=self._command_data(key,args)
            if self.peek(key)['state']['revision']!=data['revision']:raise CoreError('HANDS_STALE_TASK_REVISION')
    def _prepared(self,inv,key,args):
        data=self._command_data(key,args)
        if not callable(self.context_provider):raise CoreError('HANDS_AUTHORIZATION_CONTEXT_REQUIRED')
        context=self.context_provider(inv)
        if type(context) is not HandsEffectContext or context.action_id!=inv.action_id or context.subject_id!=self.identity_id or context.target_ownership_evidence!=self.target.binding:raise CoreError('HANDS_CONTEXT_BINDING_MISMATCH')
        return {'context':context.model_dump(mode='json'),'task_id':key,'revision':data['revision'],'commands':data['commands'],'idempotency_key':inv.idempotency_key,'action_id':inv.action_id,'subject_id':self.identity_id}
    def _pure(self,inv,key,args):
        if inv.capability=='world.observe':
            observed=self.peek(key);value={'task':observed['task'],'revision':observed['state']['revision']}
            if self.tasks[key].kind=='CONTENT':
                root=self.assert_owned();fd=os.open(root/(key+'.input.txt'),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                with os.fdopen(fd,'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(2049).decode()!=self.tasks[key].initial:raise CoreError('HANDS_SOURCE_BINDING_MISMATCH')
        else:
            source=args['data']
            if source.get('task')!=self.tasks[key].model_dump(mode='json'):raise CoreError('HANDS_SOURCE_BINDING_MISMATCH')
            if inv.capability=='world.compute':value=transform(args['method'],source)
            else:
                if self.code_skills is None:raise CoreError('HANDS_SKILL_REALM_REQUIRED')
                value=self.code_skills.invoke(args['skill_record_id'],source)
        return {'data':value,'data_privacy':'PROJECT','origin':'REAL_OS_CONTROLLED_APPLICATION' if inv.capability=='world.observe' else 'LOCAL_COMMAND_PREPARATION',**({'method':args['method']} if 'method' in args else {}),'target_binding':self.target.binding,'execution_context':self.execution_evidence()}
    def execute(self,inv):
        key,args=self._valid(inv)
        if inv.capability!='world.publish':return Receipt(external_id=inv.idempotency_key,result=self._pure(inv,key,args))
        request=self._prepared(inv,key,args)
        self._request('control',request)
        return Receipt(external_id=inv.idempotency_key,result={'application_acknowledged':True,'not_independently_verified':True,'execution_context':self.execution_evidence()})
    def verify(self,inv):
        try:
            key,args=self._valid(inv)
            if inv.capability!='world.publish':return Verification(verdict='MATCH',evidence={'result':self._pure(inv,key,args)})
            request=self._prepared(inv,key,args);observed=self.peek(key,inv.idempotency_key);effect=observed['effect']
            if effect is None:return Verification(verdict='INCONCLUSIVE',evidence={'reason':'NO_AUTHORITATIVE_EFFECT_RECEIPT_NO_RETRY'})
            if effect['request_digest']!=digest({'binding':self.target.binding,**request}) or effect['action_id']!=inv.action_id or effect['subject_id']!=self.identity_id:raise CoreError('HANDS_CORRELATION_MISMATCH')
            state=observed['state']
            if state['revision']!=effect['revision'] or digest(state)!=effect['after_digest']:raise CoreError('HANDS_STATE_CHANGED_SINCE_EFFECT')
            task=self.tasks[key]
            if task.kind in {'DOCUMENT','CONTENT'}:
                root=self.assert_owned();directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    fd=os.open(key+'.txt',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
                    with os.fdopen(fd,'rb') as stream:
                        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise CoreError('HANDS_DOCUMENT_INVALID')
                        actual=stream.read(2049).decode()
                finally:os.close(directory)
                if actual!=state['text']:raise CoreError('HANDS_STRUCTURAL_EVIDENCE_DISAGREES')
                value=actual
            elif task.kind=='FILES':
                root=self.assert_owned();directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                actual={}
                try:
                    for name in (*task.fields,*task.wanted.values()):
                        try:fd=os.open(key+'--'+name+'.txt',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
                        except FileNotFoundError:continue
                        with os.fdopen(fd,'rb') as stream:
                            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise CoreError('HANDS_DOCUMENT_INVALID')
                            actual[name]=stream.read(2049).decode()
                finally:os.close(directory)
                if actual!=state['values']:raise CoreError('HANDS_STRUCTURAL_EVIDENCE_DISAGREES')
                value={'values':actual,'submitted':False}
            else:
                # Independent read-only channel AND persisted application state.
                root=self.assert_owned();fd=os.open(root/'application-state.json',os.O_RDONLY|os.O_NOFOLLOW)
                with os.fdopen(fd,'rb') as stream:persisted=json.loads(stream.read(200000))
                if persisted['instance_id']!=self.target.instance_id or persisted['state'][key]!=state or persisted['effects'].get(inv.idempotency_key)!=effect:raise CoreError('HANDS_STRUCTURAL_EVIDENCE_DISAGREES')
                value={'values':state['values'],'submitted':state['submitted']}
            result={'data':value,'data_privacy':'PROJECT','origin':'REAL_OS_CONTROLLED_INDEPENDENT_VERIFICATION','target_binding':self.target.binding,'execution_context':self.execution_evidence(),'task_id':key,'revision':state['revision'],'effect':effect,'verify_paths':['READ_ONLY_APPLICATION_IPC','DOCUMENT_FILE' if task.kind in {'DOCUMENT','CONTENT','FILES'} else 'PERSISTED_APPLICATION_STATE']}
            return Verification(verdict='MATCH',evidence={'result':result,'effect_digest':digest(effect)})
        except (CoreError,OSError,ValueError,KeyError):return Verification(verdict='INCONCLUSIVE',evidence={'reason':'INDEPENDENT_HANDS_VERIFICATION_UNKNOWN'})
