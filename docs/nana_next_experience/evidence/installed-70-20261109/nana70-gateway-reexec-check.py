import json,hashlib,subprocess,os
from pathlib import Path
old=Path('/workspace/scratch/nana-scope32-installed');new=Path('/workspace/scratch/nana-resumed70-installed');work=Path('/tmp/n70installed')
cfg=json.loads((work/'host.json').read_text());assert cfg['binding']['subject_id']=='167595ca-8e5c-4cf6-8803-f4acba8a7643'
assert cfg['releases'][0]['source_commit']=='70c70d0b2d3c8105da765f92b1ce621e8e130f9c'
cfg['releases'].append({'release_id':'old-d2','source_commit':'d2d5e8ca5277dcd0c6ea034266ad652d16e53bcf','root':str(old),'python':str(old/'.venv/bin/python')});cfg['active_release']='old-d2'
p=work/'host-reexec-check2.json';assert not p.exists();p.write_text(json.dumps(cfg));p.chmod(0o600)
paths=[work/'life/subject/self.db',work/'life/subject/self.db.privacy.json',work/'life/life.json',work/'host/supervisor.json']
def hashes():return {str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=hashes();trace=Path('/workspace/scratch/nana70-gateway-reexec.trace');output=Path('/workspace/scratch/nana70-gateway-reexec-output.json')
r=subprocess.run(['/usr/bin/strace','-f','-qq','-s','4096','-e','trace=execve','-o',str(trace),str(old/'.venv/bin/python'),'-I','-B',str(old/'host_gateway.py'),'--config',str(p),'--check-only'],cwd='/workspace',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'},capture_output=True,text=True,timeout=30)
output.write_text(r.stdout);Path('/workspace/scratch/nana70-gateway-reexec.stderr').write_text(r.stderr)
assert r.returncode==0,(r.returncode,r.stdout,r.stderr)
body=json.loads(r.stdout);assert body['state']=='READ_ONLY_BINDING_CHECKED' and body['provider_calls']==0 and body['subject_created'] is False
lines=[x for x in trace.read_text().splitlines() if 'execve(' in x]
assert len(lines)==2 and all(x.endswith('= 0') for x in lines),lines
assert str(old/'host_gateway.py') in lines[0] and str(new/'host_gateway.py') in lines[1]
assert hashes()==before
result={'scope':'ACTUAL_INSTALLED_DEV_CHECK_ONLY_NOT_PRODUCTION','old_source':'d2d5e8ca5277dcd0c6ea034266ad652d16e53bcf','target_source':'70c70d0b2d3c8105da765f92b1ce621e8e130f9c','actual_successful_execve_count':len(lines),'existing_snapshot_overrode_baked_old_selection':True,'same_dev_subject':body['subject_id'],'data_and_supervisor_hashes_unchanged':True,'before_sha256':before,'model_calls':0,'credential_fds_supplied':False,'source_registry_only_not_live_cutover':True}
Path('/workspace/scratch/nana70-gateway-reexec-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
