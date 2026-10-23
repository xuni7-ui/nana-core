"""Read-only numeric /proc observer for this mission's owned lab, not Runtime.

May start after residency starts: evidence records its actual observation span.
No HTTP polling, source edits, signals, Store writes or environment/argv reads.
"""
import argparse,json,os,sqlite3,tempfile,time
from pathlib import Path


def proc(pid):
    root=Path('/proc')/str(pid);raw=(root/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
    # stat field3 starts fields[0], starttime is22. No command-line/env read.
    return {'parent':int(fields[1]),'start':fields[19],
        'cpu_seconds':(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK'),
        'rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),
        'threads':len(list((root/'task').iterdir())), 'fds':len(list((root/'fd').iterdir()))}


def observe(root,output,interval=60):
    root=Path(root).resolve();output=Path(output).absolute()
    if output.exists() or output.is_symlink() or output.is_relative_to(root):raise ValueError('FRESH_SEPARATE_OBSERVER_OUTPUT_REQUIRED')
    manifest=json.loads((root/'world/lab-manifest.json').read_text());source=json.loads((root/'source-manifest.json').read_text())
    backend=proc(manifest['backend_pid']);owner=backend['parent']
    with sqlite3.connect('file:'+str(root/'life/subject/self.db')+'?mode=ro',uri=True) as db:
        lease=db.execute('SELECT pid,process_start FROM runtime_lease WHERE state=\'ACTIVE\'').fetchone()
    if not lease or lease!=(owner,proc(owner)['start']):raise ValueError('OWNED_RUNTIME_LEASE_MISMATCH')
    children={'browser':manifest['website'],**manifest['services'],'backend':{'pid':manifest['backend_pid'],'start':backend['start']}}
    processes={'original-runtime':{'pid':owner,'start':proc(owner)['start']},**children}
    for item in children.values():
        state=proc(item['pid'])
        if state['parent']!=owner or state['start']!=item['start']:raise ValueError('OWNED_PROCESS_MISMATCH')
    started=time.monotonic();samples=[];complete=False;failure=None
    def write():
        data={'kind':'LATE_STARTED_READ_ONLY_OWNED_PROCESS_OBSERVER','source_commit':source['source_head'],
            'process_roles':list(processes),'sample_interval_seconds':interval,'duration_seconds':time.monotonic()-started,
            'status':'COMPLETE' if complete else 'STOPPED_EARLY' if failure else 'OBSERVING_NOT_QUALIFIED',
            'failure':failure,'samples':samples}
        fd,name=tempfile.mkstemp(prefix='.nana-resource-',dir=output.parent)
        try:
            with os.fdopen(fd,'w') as stream:json.dump(data,stream,separators=(',',':'));stream.flush();os.fsync(stream.fileno())
            os.replace(name,output)
        finally:
            if os.path.exists(name):os.unlink(name)
    deadline=time.monotonic()
    while time.monotonic()-started<21600:
        if (root/'result.json').exists():complete=True;break
        if time.monotonic()>=deadline:
            try:
                rows={}
                for role,item in processes.items():
                    state=proc(item['pid'])
                    if state['start']!=item['start']:raise ValueError('OWNED_PID_REUSED')
                    rows[role]=state
                progress=json.loads((root/'progress.json').read_text())
                samples.append({'observed_at_us':time.time_ns()//1000,'residency_elapsed_seconds':progress['sample']['elapsed_seconds'],'processes':rows})
                write();deadline=time.monotonic()+interval
            except (OSError,ValueError) as exc:
                # The owned processes may exit milliseconds before result is
                # atomically published; wait briefly, never signal/restart them.
                for _ in range(10):
                    if (root/'result.json').exists():complete=True;break
                    time.sleep(.1)
                if not complete:failure=type(exc).__name__
                break
        time.sleep(min(1,max(0,deadline-time.monotonic())))
    write()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();observe(args.root,args.output)
if __name__=='__main__':main()
