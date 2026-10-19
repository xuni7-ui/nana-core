"""Trusted developer lifecycle for an explicitly owned application child."""
import json,os,subprocess,sys,time
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
    def __init__(self,root,*,tasks=None):
        self.root=Path(root).absolute();self.root.mkdir(mode=0o700,parents=True,exist_ok=False)
        workspace=self.root/'application';workspace.mkdir(mode=0o700)
        manifest=self.root/'tasks.json';manifest.write_text(json.dumps([t.model_dump(mode='json') for t in (tasks or default_tasks())]));manifest.chmod(0o600)
        self._log=(self.root/'application.log').open('w');self.proc=subprocess.Popen([sys.executable,'-m','nana_core.continuity.hands.server','--workspace',str(workspace),'--tasks',str(manifest)],stdin=subprocess.DEVNULL,stdout=self._log,stderr=self._log)
        self.profile=workspace/'profile.json'
        start=time.monotonic()
        while not self.profile.exists():
            if self.proc.poll() is not None or time.monotonic()-start>5:self.close();raise CoreError('OWNED_APPLICATION_START_FAILED')
            time.sleep(.02)
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
