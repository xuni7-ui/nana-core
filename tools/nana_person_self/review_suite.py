"""List heldout review prompts; execution requires one explicit selected case.

No credential handling, retries, automatic model switching or bulk model calls.
"""
import argparse,json
from pathlib import Path
from uuid import uuid4
from nana_core.life.control import request
ROOT=Path(__file__).resolve().parents[2]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path);p.add_argument('--case');p.add_argument('--execute',action='store_true');p.add_argument('--retain-shared-life',action='store_true');a=p.parse_args()
    suite=json.loads((ROOT/'docs/nana_persistent_person_self_v1_evidence/heldout_conversations.json').read_text())
    if not a.execute:
        print(json.dumps({'provider_calls':0,'human_review':'NOT_RUN','cases':suite['cases']},ensure_ascii=False,indent=2));return
    if not a.home or not a.case:p.error('--execute requires --home and exactly one --case')
    case=next((c for c in suite['cases'] if c['id']==a.case),None)
    if not case:p.error('unknown case')
    # Original application budget/credential/privacy gates remain authoritative.
    # A client timeout is not permission to resubmit the same event.
    data={'operation':'surface','observation':{'binding_id':'cloud.cli','event_id':str(uuid4()),'topic':'project' if case['mode']!='CASUAL' else 'daily','text':case['project_owned_prompt'],'privacy_class':'PROJECT','retain_shared_life':a.retain_shared_life}}
    print(json.dumps(request(a.home,data),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
