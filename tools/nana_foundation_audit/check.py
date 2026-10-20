"""Check the existing frozen 63-criterion audit; no behavioral qualification."""
import hashlib,json,re,subprocess
from pathlib import Path
from nana_core.clock import Clock
from nana_core.continuity.current_state import ProjectStateBinding,ProjectStateSource

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/nana_master_framework_foundation_audit_v1_evidence'
ANCHOR='af52371d0201b72ce83b00fdf6e4e1b33cd1d198'

def blob(name):return subprocess.check_output(['git','show',ANCHOR+':'+name],cwd=ROOT)
def check(*,verify_manifest=True):
 a=json.loads((E/'audit.json').read_text());old=json.loads(blob(str((E/'audit.json').relative_to(ROOT))))
 matrix=(ROOT/'PROJECT_BRAIN/01_CAPABILITY_MATRIX.md').read_text()
 assert (ROOT/'PROJECT_BRAIN/00_MASTER_FRAMEWORK.md').read_bytes()==blob('PROJECT_BRAIN/00_MASTER_FRAMEWORK.md')
 assert a['criteria_version']==old['criteria_version']=='1.0'
 assert [(d['id'],d['foundation_definition'],[(c['id'],c['criterion']) for c in d['criteria']]) for d in a['domains']]==[(d['id'],d['foundation_definition'],[(c['id'],c['criterion']) for c in d['criteria']]) for d in old['domains']]
 assert {d['id']:len(d['criteria']) for d in a['domains']}=={'S1':5,'S2':6,'S3':9,'S4':6,'S5':6,'S6':7,'S7':5,'S8':7,'S9':6,'S10':6}
 statuses={'NOT_STARTED','FOUNDATION_PARTIAL','FOUNDATION_IMPLEMENTED','FOUNDATION_TESTED','FOUNDATION_QUALIFIED','ADVANCED_GROWTH','UNKNOWN_AUDIT_REQUIRED'}
 for d in a['domains']:
  assert d['foundation_status'] in statuses
  assert '| '+d['id']+' '+d['name']+' | '+d['foundation_status']+' |' in matrix
  for c in d['criteria']:
   assert c['status'] in statuses and c['evidence']
   assert '| '+c['id']+' | '+c['criterion']+' | '+c['status']+' |' in matrix
   assert len(re.findall(r'^\| '+c['id']+r' \|',matrix,re.M))==1
   for ref in c['evidence']:assert ref in a['references']
  if d['foundation_status']=='FOUNDATION_QUALIFIED':assert all(c['status']=='FOUNDATION_QUALIFIED' for c in d['criteria'])
 for paths in a['references'].values():
  for name in paths:assert (ROOT/name).is_file(),name
 for entry in json.loads((E/'source_inspection.json').read_text())['domains']:
  for source in entry['code']:assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256']
 assert not subprocess.check_output(['git','diff',ANCHOR,'--','src','tests'],cwd=ROOT)
 assert not re.search(r'\d+(?:\.\d+)?\s*%',matrix)
 source=ProjectStateSource(ROOT,ProjectStateBinding(relative_path='PROJECT_BRAIN/09_STATE.md',source_id='project.audit.current',scope='project-work'))
 state=source.projection(scopes=('project-work',),privacy_classes=('PROJECT',),now_us=Clock().utc_now_us())
 assert state['state']['workstream']=='MASTER_FRAMEWORK_FREEZE_AND_FOUNDATION_CAPABILITY_AUDIT_V1'
 assert state['state']['revision']>=4
 if verify_manifest:
  m=json.loads((E/'manifest.json').read_text())
  assert 'PROJECT_BRAIN/09_STATE.md' not in m['files'] and str((E/'manifest.json').relative_to(ROOT)) not in m['files']
  for name,value in m['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,name
 return {'result':'PASS','kind':'FROZEN_DEFINITION_REFERENCE_AND_HASH_VALIDATION_NOT_APPLICATION_QUALIFICATION','domains':10,'criteria':63,'framework_bytes_unchanged':True,'definitions_unchanged':True,'business_source_tests_unchanged':True,'projection_bytes':len(json.dumps(state,ensure_ascii=False).encode()),'new_provider_calls':0}

if __name__=='__main__':print(json.dumps(check(),indent=2))
