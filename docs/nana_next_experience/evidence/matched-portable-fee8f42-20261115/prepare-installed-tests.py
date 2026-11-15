from pathlib import Path
import shutil,subprocess
root=Path('/tmp/nana-fee8-qualification');root.mkdir(mode=0o700,exist_ok=False)
deps=root/'test-dependencies';deps.mkdir()
site=Path('/workspace/nana-test-env/lib/python3.12/site-packages')
for name in ('pytest','_pytest','pluggy','iniconfig','packaging','py.py','pygments'):
 p=site/name
 if p.is_dir():shutil.copytree(p,deps/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 else:shutil.copyfile(p,deps/name)
files=['tests/person_self/'+name+'.py' for name in ('test_settled_need_choice','test_need_causal_population','test_competence_motive','test_tendency_elapsed_context','test_private_tendency','conftest')]+['tests/controlled_hands/conftest.py','tests/independent_life/test_dialogue.py','tests/independent_life/conftest.py','PROJECT_BRAIN/09_STATE.md']
for name in files:
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(subprocess.check_output(['git','show','fee8f422a667ec42f2dd608472d3617ad2b14e89:'+name]))
for name in ('tests','tests/person_self','tests/controlled_hands','tests/independent_life'):(root/name/'__init__.py').write_text('')
(root/'src').symlink_to('/tmp/nfee8/src',target_is_directory=True)
(root/'pytest.ini').write_text('[pytest]\naddopts = -ra --strict-markers\n')
(root/'run.py').write_text('''import sys,os,json
from pathlib import Path
root=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/nfee8/src',str(root/'test-dependencies'),str(root)]
os.chdir(root)
import pytest,pydantic,nana_core,cryptography,PIL
assert str(pydantic.__file__).startswith('/tmp/nfee8/.venv/')
assert str(cryptography.__file__).startswith('/tmp/nfee8/.venv/')
print('INSTALLED_DEPENDENCIES',pydantic.__file__,cryptography.__file__,PIL.__file__,flush=True)
code=pytest.main(['-q','-c',str(root/'pytest.ini'),'tests/person_self/test_settled_need_choice.py','tests/person_self/test_need_causal_population.py','tests/person_self/test_competence_motive.py','tests/person_self/test_tendency_elapsed_context.py','--basetemp=/tmp/f8q','-o','cache_dir=/tmp/nana-fee8-qualification/pytest-cache'])
core=[(k,v.__file__) for k,v in sys.modules.items() if k.startswith('nana_core') and getattr(v,'__file__',None)]
assert core and all(path.startswith('/tmp/nfee8/src/') for _,path in core),core
print('INSTALLED_CORE_ORIGINS',json.dumps({'modules':len(core),'all_from_installed_bundle':True,'repository_pythonpath':False,'test_tools_are_external':True,'exit_code':code}))
raise SystemExit(code)
''')
print('Standalone qualification fixture files',len(files))
