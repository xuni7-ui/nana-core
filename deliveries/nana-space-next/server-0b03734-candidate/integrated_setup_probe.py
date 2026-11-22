"""Reuse the fixed original journey.setup on a fresh stopped Gateway DEV only.

This external acceptance tool loads three original public fixture factories;
all business modules come from the installed slot. No real model or account.
"""
import argparse,ast,hashlib,importlib,importlib.util,json,sqlite3,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--gateway',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if not __debug__:raise ValueError('QUALIFICATION_REQUIRES_ASSERTIONS')
sys.dont_write_bytecode=True;bundle=a.bundle.resolve();work=a.work.resolve();home=work/'life';root=Path(__file__).resolve().parent;sha='0b03734567ccb7c9313dd1eaa9d94f7a06ecbfd5';gateway=json.loads(a.gateway.read_text());runtime=json.loads((bundle/'runtime.json').read_text())
if (Path(sys.prefix).resolve()!=bundle/'.venv' or runtime['source_commit']!=sha or gateway.get('source_commit')!=sha or gateway.get('execution')!='ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD'):raise ValueError('INSTALLED_MATCHING_DEV_REQUIRED')
if json.loads((home/'nana-space-development.json').read_text())!={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':gateway['subject_id']}:raise ValueError('OWNED_DEV_REQUIRED')
sys.path.insert(0,str(bundle/'src'))
from nana_core.life.portable_runtime import owner_alive,status
from nana_core.life.live_api.supervisor import existing_identity
if owner_alive(status(home/'subject/self.db')) or existing_identity(home)[:2]!=(gateway['subject_id'],gateway['lineage_binding']):raise ValueError('STOPPED_SAME_DEV_REQUIRED')
with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
 if db.execute('select count(*) from cognitive_requests').fetchone()[0]:raise ValueError('FRESH_GATEWAY_BEFORE_COGNITION_REQUIRED')
if (work/'observed-project.json').exists():raise ValueError('FRESH_OWNED_FIXTURE_FILE_REQUIRED')
fixtures={}
for suffix in ('continuity/open_agency/fixtures.py','continuity/world_loop/reference.py','continuity/world_loop/harness.py'):
 name='nana_core.'+suffix.removesuffix('.py').replace('/','.');path=root/'qualification'/suffix;importlib.import_module(name.rpartition('.')[0]);spec=importlib.util.spec_from_file_location(name,path);item=importlib.util.module_from_spec(spec);sys.modules[name]=item;spec.loader.exec_module(item);fixtures[name]=hashlib.sha256(path.read_bytes()).hexdigest()
source=(root/'qualification/journey.py').read_bytes();nodes=[]
for node in ast.parse(source).body:
 if isinstance(node,(ast.Import,ast.ImportFrom)):
  if isinstance(node,ast.ImportFrom) and node.module=='tools.nana_cloud_daily_life.qualification':continue
  nodes.append(node)
 elif isinstance(node,ast.FunctionDef) and node.name=='setup':nodes.append(node)
space={'__name__':'fixed_original_journey_setup'};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<fixed-original-journey-setup>','exec'),space)
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
original=load_config(home);update_config(home,original.model_copy(update={'revision':original.revision+1,'provider_calls_per_day':8,'provider_total_calls_limit':8,'per_provider_calls_per_day':8,'provider_total_reserved_cost_micro':0}),expected_revision=original.revision)
try:
 with LifeApplication(home,bootstrap_grant=False) as app:
  app.pause();result=space['setup'](app,work);assert app.runtime.identity_id==gateway['subject_id'];business=[str(m.__file__) for n,m in sys.modules.items() if n.startswith('nana_core') and n not in fixtures and getattr(m,'__file__',None)];assert business and all(Path(n).is_relative_to(bundle/'src') for n in business)
finally:
 current=load_config(home);update_config(home,original.model_copy(update={'revision':current.revision+1}),expected_revision=current.revision)
report={'source_commit':sha,'execution':'ORIGINAL_SETUP_FUNCTION_IN_ACTUAL_INSTALLED_DEV_NOT_FULL_RESIDENCY','same_gateway_subject':True,'identity_id':gateway['subject_id'],'lineage_binding':gateway['lineage_binding'],'result':result,'original_setup_source_sha256':hashlib.sha256(source).hexdigest(),'all_business_modules_from_installed_slot':len(business),'external_public_fixture_factories':fixtures,'real_provider_calls':0,'production_changed':False};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
