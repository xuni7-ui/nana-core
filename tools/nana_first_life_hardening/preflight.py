"""Read-only readiness check. Does not launch First-Life or inspect production."""
import argparse,json,subprocess
from pathlib import Path

def preflight(root):
 root=Path(root);audit=json.loads((root/'docs/nana_master_framework_foundation_audit_v1_evidence/audit.json').read_text())
 open_ids=[c['id'] for d in audit['domains'] if d['id']!='S10' for c in d['criteria'] if c['status']!='FOUNDATION_QUALIFIED']
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 return {'source_head':head,'derived':True,'foundation_prerequisites':'OPEN' if open_ids else 'QUALIFIED_AS_RECORDED_RECHECK_ARTIFACTS','open_criteria':open_ids,'human_review':'NOT_RUN','first_life_started':False,'first_life_experience_ready':'NOT_READY','production_authorized':False,'next':'WAIT_FOR_ORIGINAL_S4_FINAL_RESULT' if open_ids else 'REQUEST_FIRST_LIFE_INTEGRATION_GATE_START','provider_calls':0}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',type=Path,default=Path.cwd());a=p.parse_args()
 result=preflight(a.repository);print(json.dumps(result,indent=2))
 if result['open_criteria']:raise SystemExit(2)
if __name__=='__main__':main()
