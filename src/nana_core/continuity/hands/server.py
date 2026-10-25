"""An owned *external application*, with finite document/form commands.

This process has no Core imports beyond typed DTOs/storage hashing; no Subject,
planner, Memory, identity, model or grants. State is application data, not a second
Subject Store. Read-only IPC and actual document files are independent Verify paths.
"""
import argparse,json,os,selectors,socket,stat,struct,signal,tempfile,time
from pathlib import Path
from .contracts import ApplicationTask,OwnedTarget,HandsEffectContext,private_directory,process_start
from ...storage import canonical,digest
from ...host_requirements import unix_socket_path
from .framing import receive_object

def atomic(path,data,directory):
    # Writes remain beneath the original owned directory inode even if its
    # pathname is exchanged. No symlink/temp-path escape between check/effect.
    name='.app-'+os.urandom(12).hex()
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path.name,src_dir_fd=directory,dst_dir_fd=directory);os.fsync(directory)
    finally:
        try:os.unlink(name,dir_fd=directory)
        except FileNotFoundError:pass

def serve(workspace,tasks):
    unix_socket_path(Path(workspace)/'control.sock')
    unix_socket_path(Path(workspace)/'query.sock')
    root=private_directory(workspace)
    if any(root.iterdir()):raise ValueError('fresh owned application directory required')
    directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    tasks=tuple(ApplicationTask.model_validate_json(canonical(t)) for t in tasks)
    sockets=[];selector=selectors.DefaultSelector();running=True
    state={t.task_id:{'revision':1,'text':t.initial,'values':{k:'' for k in t.fields},'submitted':False} for t in tasks};effects={}
    for t in tasks:
        if t.kind in {'DOCUMENT','CONTENT'}:atomic(root/(t.task_id+'.txt'),t.initial.encode(),directory)
        if t.kind=='CONTENT':atomic(root/(t.task_id+'.input.txt'),t.initial.encode(),directory)
        if t.kind=='FILES':
            for key in t.fields:
                text=t.initial+':'+key;state[t.task_id]['values'][key]=text
                atomic(root/(t.task_id+'--'+key+'.txt'),text.encode(),directory)
    for name in ['control','query']:
        s=socket.socket(socket.AF_UNIX);s.bind(str(root/(name+'.sock')));os.chmod(root/(name+'.sock'),0o600);s.listen(4);selector.register(s,selectors.EVENT_READ,name);sockets.append(s)
    profile=OwnedTarget(workspace=str(root),pid=os.getpid(),uid=os.getuid(),process_start=process_start(os.getpid()),directory_inode=os.fstat(directory).st_ino,control_inode=(root/'control.sock').stat().st_ino,query_inode=(root/'query.sock').stat().st_ino,instance_id=os.urandom(16).hex(),tasks=tasks)
    by_id={t.task_id:t for t in tasks}
    atomic(root/'profile.json',profile.model_dump_json().encode(),directory)
    def checkpoint():atomic(root/'application-state.json',canonical({'instance_id':profile.instance_id,'state':state,'effects':effects}).encode(),directory)
    checkpoint()
    def stop(*args):nonlocal running;running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    print(json.dumps({'state':'READY','profile':str(root/'profile.json'),'pid':os.getpid()}),flush=True)
    try:
        while running:
            for key,_ in selector.select(.25):
                conn,_=key.fileobj.accept();conn.settimeout(1)
                with conn:
                    try:
                        pid,uid,gid=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                        if uid!=profile.uid:raise ValueError('peer owner')
                        request=receive_object(conn,limit=16384,seconds=1)
                        task_id=request['task_id'];task=by_id[task_id]
                        if request['binding']!=profile.binding:raise ValueError('binding')
                        if key.data=='query':
                            if set(request)-{'binding','task_id','effect_id'}:raise ValueError('read-only channel')
                            response={'instance_id':profile.instance_id,'task':task.model_dump(mode='json'),'state':state[task_id],'effect':effects.get(request.get('effect_id'))}
                        else:
                            if set(request)!={'binding','task_id','idempotency_key','action_id','subject_id','commands','revision','context'}:raise ValueError('request shape')
                            context=HandsEffectContext.model_validate_json(canonical(request['context']))
                            if context.action_id!=request['action_id'] or context.subject_id!=request['subject_id'] or context.target_identity!=profile.instance_id or context.target_ownership_evidence!=profile.binding or context.idempotency_key!=request['idempotency_key']:raise ValueError('effect context')
                            eid=request['idempotency_key'];fingerprint=digest(request)
                            if eid in effects:
                                if effects[eid]['request_digest']!=fingerprint:raise ValueError('idempotency collision')
                                response=effects[eid]
                            else:
                                if root.is_symlink() or root.stat().st_ino!=os.fstat(directory).st_ino:raise ValueError('target directory changed')
                                if time.time_ns()//1000>context.deadline_us:raise ValueError('deadline')
                                if len(effects)>=256:raise ValueError('effect journal bound')
                                if request['revision']!=state[task_id]['revision']:raise ValueError('stale task revision')
                                commands=request['commands']
                                if type(commands)!=list or not 1<=len(commands)<=9:raise ValueError('command bound')
                                new=json.loads(canonical(state[task_id]));before=digest(new)
                                for command in commands:
                                    if task.kind in {'DOCUMENT','CONTENT'}:
                                        if set(command)!={'op','value'} or command['op'] not in {'REPLACE','APPEND'} or type(command['value'])!=str or len(command['value'])>512:raise ValueError('document command')
                                        new['text']=(new['text'] if command['op']=='APPEND' else '')+command['value']
                                        if len(new['text'])>2048:raise ValueError('document size')
                                    elif task.kind=='FILES':
                                        if set(command)!={'op','source','destination'} or command['op']!='MOVE' or task.wanted.get(command['source'])!=command['destination'] or command['source'] not in new['values']:raise ValueError('finite file mapping')
                                        new['values'][command['destination']]=new['values'].pop(command['source'])
                                    elif command['op']=='SET_FIELD':
                                        if set(command)!={'op','field','value'} or command['field'] not in task.fields or type(command['value'])!=str or len(command['value'])>128:raise ValueError('form field')
                                        new['values'][command['field']]=command['value']
                                    elif command!={'op':'SUBMIT'}:raise ValueError('form command')
                                    else:new['submitted']=True
                                new['revision']+=1
                                # Application persistence, not a claimed expected output. A crash
                                # across two files is detectable disagreement, never replayed here.
                                if task.kind in {'DOCUMENT','CONTENT'}:atomic(root/(task_id+'.txt'),new['text'].encode(),directory)
                                if task.kind=='FILES':
                                    # Finite owned basenames only. link+unlink never overwrites
                                    # an existing destination; a partial crash stays observable.
                                    for command in commands:
                                        src=task_id+'--'+command['source']+'.txt';dst=task_id+'--'+command['destination']+'.txt'
                                        if not stat.S_ISREG(os.stat(src,dir_fd=directory,follow_symlinks=False).st_mode):raise ValueError('source file type')
                                        os.link(src,dst,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False);os.unlink(src,dir_fd=directory);os.fsync(directory)
                                state[task_id]=new
                                response={'request_digest':fingerprint,'action_id':request['action_id'],'subject_id':request['subject_id'],'task_id':task_id,'idempotency_key':eid,'before_digest':before,'after_digest':digest(new),'revision':new['revision'],'at_ns':time.time_ns(),'status':'APPLIED','commands':commands}
                                effects[eid]=response;checkpoint()
                        conn.sendall(canonical({'ok':True,'data':response}).encode()+b'\n')
                    except (ValueError,KeyError,TypeError,OSError):
                        try:conn.sendall(b'{"ok":false,"code":"APPLICATION_REQUEST_REJECTED"}\n')
                        except OSError:pass
    finally:
        selector.close()
        for s in sockets:s.close()
        os.close(directory)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--tasks',type=Path,required=True);a=p.parse_args()
    serve(a.workspace,json.loads(a.tasks.read_text()))
if __name__=='__main__':main()
