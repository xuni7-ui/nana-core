import json,os,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/tmp/nana-262-local-qualification');bundle=Path('/tmp/nn262');temporary=Path('/dev/shm/nq262b')
assert not temporary.exists(),'OWNED_TEST_DESTINATION_MUST_BE_FRESH'
sys.path[:0]=[str(bundle/'src'),'/tmp/nana-fee8-qualification/test-dependencies',str(root)];os.chdir(root)
import pytest,pydantic,cryptography,PIL,nana_core
assert all(Path(m.__file__).is_relative_to(bundle/'.venv') for m in (pydantic,cryptography,PIL))
runtime=json.loads((bundle/'runtime.json').read_text());assert runtime['source_commit']=='9a2f6771979532e8ad2c33db8121dda148b439e8'
source=Path('/workspace/nana-next-refinement-work');sha=runtime['source_commit']
selected=subprocess.check_output(['git','show',sha+':packaging/portable/runtime-files.txt'],cwd=source,text=True).splitlines()
for name in selected:
 if name and not name.startswith('#'):assert (bundle/name).read_bytes()==subprocess.check_output(['git','show',sha+':'+name],cwd=source)
# Exact three pre-existing public fixture factories are intentionally excluded
# from the minimal runtime. Load only those external helpers, never Core files.
import importlib,importlib.util
fixture_names={}
for name in ('continuity/open_agency/fixtures.py','continuity/world_loop/reference.py','continuity/world_loop/harness.py'):
    module='nana_core.'+name.removesuffix('.py').replace('/','.')
    importlib.import_module(module.rpartition('.')[0])
    path=root/'public-harness'/name;spec=importlib.util.spec_from_file_location(module,path)
    item=importlib.util.module_from_spec(spec);sys.modules[module]=item;spec.loader.exec_module(item);fixture_names[module]=path
print('ALL_COMMITTED_RUNTIME_FILES_AND_INSTALLED_DEPENDENCIES_VERIFIED',len([x for x in selected if x and not x.startswith('#')]),flush=True)
fixtures=json.loads((root/'fixture-source-sha256.json').read_text())
code=pytest.main(['-q','-s','-c',str(root/'pytest.ini'),'-o','pythonpath=',*fixtures['selected_tests'],'--basetemp='+str(temporary),'-o','cache_dir='+str(root/'pytest-cache')])
core=[m.__file__ for name,m in tuple(sys.modules.items()) if name.startswith('nana_core') and name not in fixture_names and getattr(m,'__file__',None)]
assert core and all(Path(p).is_relative_to(bundle/'src') for p in core)
print('INSTALLED_ORIGINS',json.dumps({'modules':len(core),'all_from_installed_262':True,'repo_pythonpath':False,'test_fixtures_external':True,'explicit_external_fixture_factories':len(fixture_names),'exit_code':int(code)}))
raise SystemExit(code)
