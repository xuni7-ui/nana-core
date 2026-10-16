"""Trusted isolated worker. Receives no Store, authority, network or host data."""
import json,resource,sys

def main():
    resource.setrlimit(resource.RLIMIT_CPU,(1,1))
    resource.setrlimit(resource.RLIMIT_AS,(192*1024*1024,192*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(65536,65536))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    resource.setrlimit(resource.RLIMIT_NPROC,(8,8))
    request=json.load(open('/work/request.json'))
    # Static checking is additional hygiene. OS namespaces/read-only mounts,
    # fresh /tmp, empty environment and resource bounds are the isolation fence.
    code=open('/work/skill.py').read()
    namespace={'__builtins__':{'sum':sum,'len':len,'sorted':sorted,'min':min,'max':max,'isinstance':isinstance,'int':int,'float':float,'str':str,'list':list,'bool':bool}}
    exec(compile(code,'/work/skill.py','exec'),namespace)
    output=namespace['transform'](request['input'])
    raw=json.dumps({'result':output},allow_nan=False,sort_keys=True,separators=(',',':'))
    if len(raw.encode())>8192:raise ValueError('OUTPUT_LIMIT')
    sys.stdout.write(raw)
if __name__=='__main__':main()
