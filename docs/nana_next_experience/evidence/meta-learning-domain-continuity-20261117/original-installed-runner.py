import importlib,importlib.util,sys,json
from pathlib import Path
sys.dont_write_bytecode=True;bundle=Path('/tmp/ni277');repo=Path('/workspace/nana-next-refinement-work');sys.path[:0]=[str(bundle/'src'),'/tmp/nana-fee8-qualification/test-dependencies',str(repo)];fixtures={}
for suffix in ('continuity/open_agency/fixtures.py','continuity/world_loop/reference.py','continuity/world_loop/harness.py'):
 module='nana_core.'+suffix.removesuffix('.py').replace('/','.');importlib.import_module(module.rpartition('.')[0]);path=Path('/tmp/nana-277-integration-fixtures')/suffix;spec=importlib.util.spec_from_file_location(module,path);item=importlib.util.module_from_spec(spec);sys.modules[module]=item;spec.loader.exec_module(item);fixtures[module]=path
import pytest
code=pytest.main(['-q','-s','tests/open_life/test_meta_learning.py::test_other_domains_do_not_displace_a_verified_learning_strategy_before_later_g','--basetemp=/dev/shm/nq280oldvalid','-o','pythonpath=','-o','cache_dir=/dev/shm/nq280oldvalidcache'])
business=[m.__file__ for n,m in tuple(sys.modules.items()) if n.startswith('nana_core') and n not in fixtures and getattr(m,'__file__',None)];assert business and all(Path(p).is_relative_to(bundle/'src') for p in business);print('FIXED_ORIGINAL_INSTALLED_BUSINESS_MODULES',len(business));raise SystemExit(code)
