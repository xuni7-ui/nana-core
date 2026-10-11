"""Development only: reproduce bounded subprocess/SIGKILL bundle validation."""
import hashlib,json,os,pathlib,signal,sqlite3,subprocess,sys,tarfile,tempfile,time
archive=pathlib.Path(sys.argv[1]);output=pathlib.Path(sys.argv[2])
with tempfile.TemporaryDirectory(prefix='nana-bootstrap-validation-') as d:
 root=pathlib.Path(d)
 with tarfile.open(archive) as t:t.extractall(root,filter='data')
 b=next(root.iterdir());commands={};run=b/'run_shadow.sh'
 def call(command,*args,check=True):
  p=subprocess.run([str(run),command,*map(str,args)],capture_output=True,text=True,timeout=15)
  if check:assert p.returncode==0,p.stdout+p.stderr
  return json.loads(p.stdout)
 filehash=lambda:{str(p.relative_to(b)):hashlib.sha256(p.read_bytes()).hexdigest() for p in b.rglob('*') if p.is_file()}
 before=filehash()
 for script in ('run_shadow.sh','stop_shadow.sh','collect_shadow.sh','rollback_shadow.sh'):
  argv=[str(b/script)]+(['preflight'] if script=='run_shadow.sh' else [])+['--dry-run']
  p=subprocess.run(argv,capture_output=True,text=True,timeout=15);assert p.returncode==0,p.stdout+p.stderr;assert json.loads(p.stdout)['status']=='DRY_RUN'
 assert filehash()==before and not (b/'data').exists()
 pf=call('preflight');assert pf['adapter_local_probe_ready'];assert pf['SHADOW_RUNTIME_ENV']['sqlite']=='3.51.3' and pf['SHADOW_RUNTIME_ENV']['pydantic']=='2.13.5'
 first=call('probe','--window-seconds',0);second=call('restart-check')
 assert first['identity']==second['identity'] and first['probe_event_id']==second['probe_event_id'] and first['evidence_hash']==second['evidence_hash']
 assert not first['identity_restored'] and second['identity_restored'] and len(second['memory_context_ids'])==1
 assert second['goal_candidate_state']=='ACCEPTED' and second['counts']['jobs']==1
 assert second['shadow_plan_count']==second['shadow_decision_count']==1
 assert all(second['counts'][t]==0 for t in ['actions','attempts','grants','budgets'])
 assert all(r['status']=='SHADOW_BLOCKED' for r in second['barrier'])
 child=subprocess.Popen([str(run),'probe','--window-seconds','30'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   s=json.loads((b/'data/session.json').read_text())
   if s['phase']=='RUNNING' and s['pid']==child.pid:break
   if child.poll() is not None:raise AssertionError(child.communicate())
   time.sleep(.01)
  assert s['phase']=='RUNNING' and s['pid']==child.pid
  os.kill(child.pid,signal.SIGKILL);child.communicate(timeout=5);assert child.returncode==-9
  unknown=call('rollback');assert unknown['status']=='UNKNOWN_UNCLEAN_TERMINATION'
  recovered=call('restart-check');assert recovered['prior_termination']=='UNKNOWN' and recovered['identity']==first['identity'] and recovered['probe_event_id']==first['probe_event_id']
  assert recovered['counts']['actions']==0
  rollback=call('rollback');assert rollback['status']=='PASS';assert call('rollback')==rollback
  collection=call('collect');assert not collection['runtime_active'] and not collection['database_exported']
  (b/'README_HOST.txt').write_text('tamper')
  blocked=call('preflight',check=False);assert blocked['reason']=='BLOCKED_PACKAGE_INTEGRITY' and blocked['status']=='BLOCKED'
  report={'status':'PASS','scope':'development actual archive extraction + subprocesses; NOT real host','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'preflight':pf,'first':first,'restart':second,'dry_run_no_writes':True,'SIGKILL_exit_code':child.returncode,'unknown_rollback':unknown,'recovered':recovered,'rollback':rollback,'collected_report_count':len(collection['reports']),'tamper_blocked':blocked,'production_calls':0,'private_records_read':0,'external_messages':0,'E12':'NOT_RUN'}
  output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'SIGKILL':child.returncode,'reports':len(collection['reports']),'same_identity':True}))
 finally:
  if child.poll() is None:child.kill();child.wait()
