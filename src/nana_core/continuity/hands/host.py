"""Trusted developer lifecycle for an explicitly owned application child."""
import json,math,os,subprocess,sys,time
from pathlib import Path
from .contracts import ApplicationTask,load_target
from ...contracts import CoreError

def default_tasks():
    return (
        ApplicationTask(task_id='document-baseline',kind='DOCUMENT',initial='Obsolete draft: ',wanted='A verified note',context='notes'),
        ApplicationTask(task_id='document-transfer',kind='DOCUMENT',initial='Previous title: ',wanted='Meeting agenda',context='calendar'),
        ApplicationTask(task_id='form-baseline',kind='FORM',wanted={'color':'blue'},fields=('size','color'),context='preferences'),
        ApplicationTask(task_id='form-transfer',kind='FORM',wanted={'query':'wind'},fields=('sort','query'),context='search'),
        ApplicationTask(task_id='form-batch-gap',kind='FORM',wanted={'title':'Map','category':'reference'},fields=('category','title'),context='library'),
        ApplicationTask(task_id='form-batch-transfer',kind='FORM',wanted={'name':'Archive','format':'text','folder':'notes'},fields=('format','folder','name'),context='export'),
        ApplicationTask(task_id='document-counterexample',kind='DOCUMENT',initial='draft',wanted='  preserve deliberate spacing  ',context='literal-template'))

class OwnedApplication:
    def __init__(self,root,*,tasks=None,startup_timeout_seconds=15.0):
        # Host-only process readiness, before any Subject or action exists. This
        # is neither an action timeout nor a lease/Grant extension.
        if isinstance(startup_timeout_seconds,bool) or not isinstance(startup_timeout_seconds,(int,float)) or not math.isfinite(startup_timeout_seconds) or not 0 < startup_timeout_seconds <= 30:
            raise CoreError('OWNED_APPLICATION_START_TIMEOUT_INVALID')
        self.root=Path(root).absolute();self.root.mkdir(mode=0o700,parents=True,exist_ok=False)
        workspace=self.root/'application';workspace.mkdir(mode=0o700)
        manifest=self.root/'tasks.json';manifest.write_text(json.dumps([t.model_dump(mode='json') for t in (tasks or default_tasks())]));manifest.chmod(0o600)
        boot="import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('nana_core.continuity.hands.server',run_name='__main__')"
        self._log=(self.root/'application.log').open('w');self.proc=subprocess.Popen([sys.executable,'-I','-c',boot,str(Path(__file__).resolve().parents[3]),'--workspace',str(workspace),'--tasks',str(manifest)],stdin=subprocess.DEVNULL,stdout=self._log,stderr=self._log,env={'PATH':os.defpath,'LANG':'C.UTF-8','TZ':'UTC'})
        self.profile=workspace/'profile.json'
        start=time.monotonic()
        while not self.profile.exists():
            exit_code=self.proc.poll()
            elapsed=time.monotonic()-start
            if exit_code is not None or elapsed>=startup_timeout_seconds:
                self.startup_diagnostics={'status':'EXITED' if exit_code is not None else 'TIMED_OUT','exit_code':exit_code,'elapsed_seconds':elapsed,'timeout_seconds':startup_timeout_seconds}
                self.close()
                # Keep bounded numeric diagnostics even when a fixture removes
                # its workspace. Never copy arbitrary child output into errors.
                error=CoreError('OWNED_APPLICATION_START_EXITED' if exit_code is not None else 'OWNED_APPLICATION_START_TIMED_OUT')
                error.startup_diagnostics=self.startup_diagnostics
                raise error
            time.sleep(.02)
        self.startup_diagnostics={'status':'READY','elapsed_seconds':time.monotonic()-start,'timeout_seconds':startup_timeout_seconds}
        self.target=load_target(self.profile)
        if self.target.pid!=self.proc.pid:self.close();raise CoreError('OWNED_CHILD_PID_MISMATCH')
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(2)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(2)
        self._log.close()
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()

def daily_tasks():
    """Explicit host-approved daily work, never an automatic execution grant."""
    return (*default_tasks(),
        ApplicationTask(task_id='reading-list',kind='CONTENT',initial='wind\nmap\nwind\n\n',wanted='map\nwind',context='reading'),
        ApplicationTask(task_id='archive-notes',kind='FILES',initial='public project notes',fields=('draft','raw'),wanted={'draft':'reviewed','raw':'reference'},context='organize'),
        ApplicationTask(task_id='index-topics',kind='CONTENT',initial=' beta\nalpha\nbeta\n',wanted='alpha\nbeta',context='index'),
        ApplicationTask(task_id='organize-export',kind='FILES',initial='synthetic export',fields=('incoming',),wanted={'incoming':'processed'},context='export'))
