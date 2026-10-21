"""Actual installed-bundle owned-host rehearsal; no current Subject/provider."""
import argparse,json,os,shutil,sqlite3,subprocess,sys,time,hashlib
from pathlib import Path
from uuid import uuid4
from .unpack import unpack


def run(archive,sha256,root):
    root=Path(root).absolute()
    if root.exists():raise ValueError('fresh rehearsal root required')
    root.mkdir(mode=0o700,parents=True);env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'}
    hosts=[unpack(archive,root/name,sha256) for name in ('host-a','host-b')]
    def cmd(host,*args,ok=True,input=None):
        p=subprocess.run([str(host/'nana'),*map(str,args)],input=input,text=True,capture_output=True,cwd=root,env=env,timeout=40)
        if ok and p.returncode:raise RuntimeError('portable command failed: '+args[0]+' '+p.stdout[-500:])
        return p
    def value(host,*args):return json.loads(cmd(host,*args).stdout)
    def script(host,code,*args):
        return subprocess.run([str(host/'.venv/bin/python'),'-B','-c','import sys;sys.path.insert(0,sys.argv.pop(1));'+code,str(host/'src'),*map(str,args)],capture_output=True,text=True,cwd=root,env=env,check=True,timeout=30).stdout
    results={'execution':'OWNED_LOCAL_INSTALLED_BUNDLE_NOT_REAL_CLOUD','source_archive_sha256':sha256,'new_provider_calls':0}
    for host in hosts:
        p=subprocess.run([str(host/'install.sh'),sys.executable],capture_output=True,text=True,cwd=root,env=env,timeout=90)
        (root/(host.name+'-install.log')).write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError('offline install failed')
        assert value(host,'preflight')['state']=='PREFLIGHT_PASS'
        assert value(host,'preflight')['state']=='PREFLIGHT_PASS' # imports never alter SHA tree
    a,b=hosts;first=value(a,'init','--fresh');identity=first['identity_id'];assert first['state']=='NEW SUBJECT CREATED'
    assert cmd(a,'init','--fresh',ok=False).returncode==2
    fresh=value(b,'init','--fresh','--home',root/'different-subject');assert fresh['identity_id']!=identity
    results['fresh_subject_mode']='PASS_EXPLICIT_DISTINCT_NO_OVERWRITE'
    seed=script(a,"""
import json
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.autonomy.private_intent import candidates
with LifeApplication(Path(sys.argv[1]),bootstrap_grant=True) as app:
 app.pause();r=app.runtime
 cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='cloud-portable',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE','REST'),resource_class='ORDINARY')
 mid=capture(r,'portable.rehearsal',cue.model_dump(mode='json'),predicate='concern.cloud-portable')
 c=r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.portable.rehearsal',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us()))
 intent=candidates(r.store,'project-work',('PUBLIC','PROJECT'))[0][1]
 from nana_core.continuity.world_loop.cognition import CognitionSession
 class OfflineTimeout:
  provider_id='synthetic.portable';model_id='fixture-timeout';remote=False
  def exchange(self,request):raise TimeoutError()
 session=CognitionSession(r,OfflineTimeout(),app.policy)
 unknown=session.prepare('portable.synthetic-unknown','INTERPRET',(mid,),pinned_only=True)
 assert session.execute(unknown)['state']=='UNKNOWN'
 print(json.dumps({'identity':r.identity_id,'source':mid,'intent':intent.intent_id,'policy':intent.disclosure_policy,'actions':len(r.store.all('actions')),'grants':len(r.store.all('grants')),'synthetic_unknown':unknown}))
""",a/'var/subject')
    seeded=json.loads(seed);assert seeded['grants']>0 and seeded['actions']==0
    destination=str(uuid4());package=root/'subject.zip'
    exported=value(a,'export','--retire-source','--output',package,'--destination-id',destination)
    assert exported['source_retired'] and cmd(a,'start','--seconds','2',ok=False).returncode==2
    bad=cmd(b,'restore','--package',package,'--sha256','0'*64,'--destination-id',destination,ok=False);assert bad.returncode==2 and not (b/'var/subject').exists()
    restored=value(b,'restore','--package',package,'--sha256',exported['sha256'],'--destination-id',destination)
    assert restored['identity_id']==identity and restored['old_host_grants']==0
    view=value(b,'inspect');assert view['private_activity']=='PRESENT_CONTENT_WITHHELD'
    blocked=cmd(b,'start','--live','--secret-ref','never-read.fixture',ok=False)
    assert blocked.returncode==2 and 'UNRESOLVED_PROVIDER_CALL_NO_RETRY' in blocked.stdout
    results['transfer']={'same_identity':True,'identity_id':identity,'transfer_id':exported['manifest']['transfer_id'],'source_retired':True,'old_start_rejected':True,'old_grants_revoked':True,'provider_config_transferred':False,'private_intent_continuity':True,'private_content_displayed':False}
    # Both installs are isolated venvs, no inherited PYTHONPATH/Codex environment.
    site=next((a/'.venv/lib').glob('python*/site-packages'));folder=site/'pydantic';missing=site/'pydantic-disabled'
    folder.rename(missing)
    try:assert cmd(a,'preflight',ok=False).returncode==2
    finally:missing.rename(folder)
    results['missing_dependency_fail_closed']=True
    active=[];log=(root/'runtime-stdout.log').open('w')
    def launch(command='start'):
        p=subprocess.Popen([str(b/'nana'),command,'--seconds','120'],stdout=log,stderr=log,cwd=root,env=env);active.append(p)
        end=time.monotonic()+10
        while time.monotonic()<end:
            if p.poll() is not None:raise RuntimeError('installed runtime exited')
            if (b/'var/subject/control.sock').exists():
                h=value(b,'health')
                if h['process_ready'] and h['runtime']['lease']['pid']==p.pid:return p,h
            time.sleep(.08)
        raise RuntimeError('installed runtime not ready')
    try:
        p,h=launch();epoch=h['runtime']['lease']['epoch']
        assert cmd(b,'start','--seconds','2',ok=False).returncode==2
        chat=cmd(b,'chat',input='This is a PUBLIC project migration check.\n/quit\n');assert 'offline' in chat.stdout.lower() or '离线' in chat.stdout
        # Identical surface event ID is a no-op on replay, not a new provider call.
        repeated=script(b,"""
import json
from pathlib import Path
from nana_core.life.control import request
h=Path(sys.argv[1]);data={'operation':'surface','observation':{'binding_id':'cloud.cli','event_id':'same-event-no-replay','topic':'migration','text':'A public project observation','privacy_class':'PROJECT'}}
a=request(h,data);b=request(h,data);print(json.dumps({'first':a['ok'],'second':b['result']['state']}))
""",b/'var/subject')
        assert json.loads(repeated)['second']=='ALREADY_REVIEWED_NO_REPLAY'
        p2,h2=launch('restart');p.wait(10);assert p.returncode==0 and h2['runtime']['lease']['epoch']>epoch
        # Real SIGKILL leaves the old socket. Original Runtime must fence the dead
        # owner and remove that socket only after its exclusive writer lock.
        p2.kill();p2.wait(5);assert p2.returncode==-9
        p3,h3=launch();assert h3['runtime']['lease']['epoch']>h2['runtime']['lease']['epoch']
        view=value(b,'inspect');assert view['identity_id']==identity and view['private_activity']=='PRESENT_CONTENT_WITHHELD'
        value(b,'emergency-stop');p3.wait(10);assert p3.returncode==0
        results['process']={'duplicate_start_blocked':True,'restart_same_identity':True,'epochs':[epoch,h2['runtime']['lease']['epoch'],h3['runtime']['lease']['epoch']],'real_sigkill':True,'dead_owner_fenced':True,'stale_socket_recovered':True,'same_event_no_replay':True,'emergency_stop_confirmed':True,'offline_chat':True}
    finally:
        for p in active:
            if p.poll() is None:p.kill();p.wait(5)
        log.close()
    backed=value(b,'backup','--output',root/'review.db')
    assert not backed['runnable'] and hashlib.sha256((root/'review.db').read_bytes()).hexdigest()==backed['sha256']
    closed=script(b,"""
import json,hashlib
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.life.inspector import inspect
from nana_core.continuity import ContinuityStore
from nana_core.continuity.autonomy.private_intent import candidates
h=Path(sys.argv[1]);mid=sys.argv[2];p=h/'subject/self.db';before=hashlib.sha256(p.read_bytes()).hexdigest()
view=inspect(h,scope='project-work',entity_id='project-user');assert hashlib.sha256(p.read_bytes()).hexdigest()==before
with LifeApplication(h) as app:
 calls=app.runtime.store.all('cognitive_requests');assert len(calls)==1 and calls[0]['state']=='UNKNOWN'
 assert not app.runtime.store.all('actions') and all(x['revoked'] for x in app.runtime.store.all('grants'))
 app.forget(mid);assert not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
with ContinuityStore(Path(sys.argv[3]),schema_target=13) as s:
 assert s.one('memories',mid)['lifecycle']=='DELETED'
 assert s.one('core_meta','recovery_quarantine')['value_json']=='true'
 print(json.dumps({'no_real_calls':True,'synthetic_unknown_preserved_no_retry':True,'no_effects':True,'inspector_read_only':True,'source_withdrawal':True,'backup_deletion_propagation':True,'backup_quarantined':True}))
""",b/'var/subject',seeded['source'],root/'review.db')
    results['closure']=json.loads(closed);results['offline_install']='PASS_TWO_INDEPENDENT_VENVS';results['supported_platform']='Linux x86_64 / Python3.12';results['rehearsal_root']=str(root)
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=run(a.archive,a.sha256,a.root);a.output.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({'status':'PASS_OWNED_INSTALLED_BUNDLE','new_provider_calls':0}))
if __name__=='__main__':main()
