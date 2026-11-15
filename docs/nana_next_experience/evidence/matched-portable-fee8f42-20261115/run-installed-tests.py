import sys,os,json
from pathlib import Path
root=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/nfee8/src',str(root/'test-dependencies'),str(root)]
os.chdir(root)
import pytest,pydantic,nana_core,cryptography,PIL
assert str(pydantic.__file__).startswith('/tmp/nfee8/.venv/')
assert str(cryptography.__file__).startswith('/tmp/nfee8/.venv/')
print('INSTALLED_DEPENDENCIES',pydantic.__file__,cryptography.__file__,PIL.__file__,flush=True)
code=pytest.main(['-q','-c',str(root/'pytest.ini'),'tests/person_self/test_settled_need_choice.py','tests/person_self/test_need_causal_population.py','tests/person_self/test_competence_motive.py','tests/person_self/test_tendency_elapsed_context.py','--basetemp=/tmp/f8q2','-o','cache_dir=/tmp/nana-fee8-qualification/pytest-cache'])
core=[(k,v.__file__) for k,v in sys.modules.items() if k.startswith('nana_core') and getattr(v,'__file__',None)]
assert core and all(path.startswith('/tmp/nfee8/src/') for _,path in core),core
print('INSTALLED_CORE_ORIGINS',json.dumps({'modules':len(core),'all_from_installed_bundle':True,'repository_pythonpath':False,'test_tools_are_external':True,'exit_code':code}))
raise SystemExit(code)
