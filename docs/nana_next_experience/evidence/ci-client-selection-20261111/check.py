import os,subprocess,tempfile,json,textwrap
from pathlib import Path
repo=Path('/workspace/nana-unified-release');workflow='.github/workflows/nana-next-qualification.yml'
text=(repo/workflow).read_text();script=textwrap.dedent(text.split("python3 - <<'PYPATHS'\n",1)[1].split('\n          PYPATHS',1)[0]);compile(script,'workflow-path-selection','exec')
def run(cmd,cwd):return subprocess.check_output(cmd,cwd=cwd,text=True,stderr=subprocess.PIPE).strip()
cases=[
 ('core-job-only',text.replace('timeout-minutes: 90','timeout-minutes: 91'),None,'push',True,False),
 ('push-path-only',text.replace('    paths:\n','    paths:\n      - tests/new-core-path.py\n',1),None,'push',True,False),
 ('client-job',text.replace('timeout-minutes: 15','timeout-minutes: 16'),None,'push',True,True),
 ('shared-global',text.replace('  contents: read','  contents: none'),None,'push',True,True),
 ('shared-classifier',text.replace("print('Affected components:'","print('Components:'"),None,'push',True,True),
 ('unknown-extra-job',text.replace('\n  client-feedback:', '\n  additional-job:\n    runs-on: ubuntu-24.04\n\n  client-feedback:'),None,'push',True,True),
 ('unknown-layout',text.replace('\n  original-core-feedback:', '\n  renamed-core-job:'),None,'push',True,True),
 ('backend-algorithm',text,'src/nana_core/continuity/retrieval_growth.py','push',True,False),
 ('backend-http',text,'src/nana_core/life/live_api/server.py','push',True,True),
 ('backend-auth',text,'src/nana_core/life/live_api/auth.py','push',True,True),
 ('frontend',text,'apps/nana-space/src/fixture.ts','push',False,True),
 ('wire-schema',text,'tools/nana_first_life_android_v2/schema.py','push',True,True),
 ('docs-only',text,'docs/fixture.md','push',False,False),
 ('manual',text,'docs/fixture.md','workflow_dispatch',True,True),
 ('new-workflow',text,None,'push',True,True),
]
root=Path(tempfile.mkdtemp(prefix='nana-ci-selection-',dir='/tmp'));results=[]
for name,new,changed,event,core,client in cases:
 d=root/name;d.mkdir();run(['git','init','-q'],d);run(['git','config','user.email','synthetic@example.invalid'],d);run(['git','config','user.name','Synthetic CI fixture'],d)
 if name!='new-workflow':(d/workflow).parent.mkdir(parents=True);(d/workflow).write_text(text)
 else:(d/'baseline.txt').write_text('synthetic')
 run(['git','add','.'],d);run(['git','commit','-qm','synthetic baseline'],d);base=run(['git','rev-parse','HEAD'],d)
 if name=='new-workflow':(d/workflow).parent.mkdir(parents=True)
 (d/workflow).write_text(new)
 if changed:p=d/changed;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic fixture')
 run(['git','add','.'],d);run(['git','commit','-qm','synthetic change'],d)
 output=d/'output';env={**os.environ,'NANA_CHANGE_BASE':base,'NANA_EVENT_NAME':event,'GITHUB_OUTPUT':str(output)}
 r=subprocess.run(['python3','-c',script],cwd=d,env=env,text=True,capture_output=True,check=True)
 actual=dict(line.split('=',1) for line in output.read_text().splitlines());assert actual['core']==str(core).lower() and actual['client']==str(client).lower(),(name,actual)
 results.append({'case':name,'core':core,'client':client,'actual':actual})
print(json.dumps({'controlled_real_git_cases':results,'fixtures_root':str(root),'result':'PASS'},indent=2))
