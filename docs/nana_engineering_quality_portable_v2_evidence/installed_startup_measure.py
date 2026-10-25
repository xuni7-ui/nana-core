"""Owned synthetic installed-process startup samples, not a whole-life benchmark.

Run after other CPU-heavy qualification. Never selects a current Subject or
provider. Every root is fresh. Reuses the existing verified unpacker from an
explicit developer checkout; installed subprocesses inherit no repository path.
"""
import argparse,json,statistics,subprocess,sys,time
from pathlib import Path


def measure(a):
    root=a.root.absolute()
    if root.exists():raise RuntimeError('FRESH_MEASUREMENT_ROOT_REQUIRED')
    root.mkdir(mode=0o700,parents=True)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'}
    def command(host,*args):
        p=subprocess.run([str(host/'nana'),*args],cwd=root,env=env,text=True,capture_output=True,timeout=30)
        if p.returncode:raise RuntimeError('INSTALLED_COMMAND_FAILED:'+str(args[0]))
        return json.loads(p.stdout)
    out={'execution':'ACTUAL_TWO_ARCHIVES_FRESH_SYNTHETIC_SUBJECTS','scope':'THREE_FRESH_PROCESS_LAUNCHES_INCLUDING_HEALTH_PROBE_NOT_COLD_DISK_CACHE_OR_LONG_LIFE','python':str(a.python),'new_provider_calls':0,'poll_seconds':.08,'samples_per_archive':3,'results':{}}
    for label,archive,digest in [('before',a.before,a.before_sha256),('after',a.after,a.after_sha256)]:
        host=root/label
        subprocess.run([sys.executable,'-m','tools.nana_portable_cloud.unpack',str(archive),'--sha256',digest,'--destination',str(host)],cwd=a.repository,env=env,text=True,capture_output=True,check=True,timeout=30)
        p=subprocess.run([str(host/'install.sh'),str(a.python)],cwd=root,env=env,text=True,capture_output=True,timeout=90)
        (root/(label+'-install.log')).write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError('OFFLINE_INSTALL_FAILED')
        preflight=[]
        for _ in range(3):
            start=time.perf_counter();report=command(host,'preflight');preflight.append((time.perf_counter()-start)*1000)
            if report['state']!='PREFLIGHT_PASS':raise RuntimeError('PREFLIGHT_DENIED')
        identity=command(host,'init','--fresh')['identity_id'];rows=[]
        for n in range(3):
            log=(root/(label+'-'+str(n)+'.log')).open('w')
            start=time.perf_counter();child=subprocess.Popen([str(host/'nana'),'start','--seconds','30'],cwd=root,env=env,stdout=log,stderr=log)
            try:
                deadline=time.monotonic()+15
                while True:
                    if child.poll() is not None:raise RuntimeError('EARLY_EXIT')
                    if time.monotonic()>=deadline:raise RuntimeError('READINESS_TIMEOUT_NO_RETRY')
                    if (host/'var/subject/control.sock').exists():
                        health=command(host,'health')
                        if health['process_ready'] and health['runtime']['lease']['pid']==child.pid:break
                    time.sleep(.08)
                ready_ms=(time.perf_counter()-start)*1000
                status=Path('/proc')/str(child.pid)/'status';lines=status.read_text().splitlines()
                rss_kib=int(next(line.split()[1] for line in lines if line.startswith('VmRSS:')))
                command(host,'stop');child.wait(timeout=10)
                if child.returncode!=0:raise RuntimeError('UNCLEAN_SHUTDOWN')
                rows.append({'launch_to_observed_health_ms':ready_ms,'runtime_rss_kib':rss_kib,'exit_code':child.returncode,'epoch':health['runtime']['lease']['epoch']})
            finally:
                if child.poll() is None:child.terminate();child.wait(timeout=10)
                log.close()
        out['results'][label]={'archive_sha256':digest,'preflight_ms':preflight,'preflight_median_ms':statistics.median(preflight),'launch_to_observed_health_median_ms':statistics.median(x['launch_to_observed_health_ms'] for x in rows),'rows':rows,'same_identity_through_restarts':command(host,'preflight')['identity_id']==identity,'repository_runtime_imports':False}
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['repository','python','root','before','after','output']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['before-sha256','after-sha256']:p.add_argument('--'+name,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(measure(a),indent=2)+'\n')
