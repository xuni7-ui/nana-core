import sys,json,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
slot,home,report,now=sys.argv[1:]
slot=Path(slot);sys.path.insert(0,str(slot/'src'))
spec=importlib.util.spec_from_file_location('sealed_bootstrap',slot/'bootstrap.py');bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap);bootstrap.verify(slot)
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.retrieval_growth import qualified_method
import sqlite3
out={'source_commit':json.loads((slot/'runtime.json').read_text())['source_commit'],'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'steps':0}
try:
 with LifeApplication(Path(home),clock=VirtualClock(int(now))) as app:
  r=app.runtime;out.update(identity=r.identity_id,epoch=r.lease.epoch,calls_before=len(r.store.all('cognitive_requests')),cycles_before=len(r.store.all('subject_cycles')),actions_before=len(r.store.all('actions')))
  out['selected_before']=qualified_method(r.store,r.authority,r.config.entity_id,'project-work',r.config.privacy_classes)
  for _ in range(12):
   r.clock.source.advance(1_000_000);r.step();out['steps']+=1
  out.update(calls_after=len(r.store.all('cognitive_requests')),cycles_after=len(r.store.all('subject_cycles')),actions_after=len(r.store.all('actions')),now_us=r.clock.utc_now_us())
except Exception as exc:
 out['error_type']=type(exc).__name__;out['error_code']=getattr(exc,'code',None)
 if hasattr(exc,'errors'):out['error_locations']=[{'type':v['type'],'loc':v['loc']} for v in exc.errors(include_input=False,include_context=False)]
finally:
 modules=[Path(m.__file__).resolve() for n,m in sys.modules.items() if (n=='nana_core' or n.startswith('nana_core.')) and getattr(m,'__file__',None)]
 assert all(str(p).startswith(str(slot/'src')+'/') for p in modules)
 bootstrap.verify(slot);out['pinned_core_modules']=len(modules);out['sealed_files_unchanged']=True
 Path(report).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
