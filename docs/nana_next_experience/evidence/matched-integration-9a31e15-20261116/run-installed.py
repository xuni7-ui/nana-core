import sys,os,json
from pathlib import Path
root=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/n9a/src',str(root/'test-dependencies'),str(root)]
os.chdir(root)
import pytest,pydantic,cryptography,PIL
assert all(str(m.__file__).startswith('/tmp/n9a/.venv/') for m in (pydantic,cryptography,PIL))
print('INSTALLED_RUNTIME_DEPENDENCIES_VERIFIED',flush=True)
code=pytest.main(['-q','-s','-c',str(root/'pytest.ini'),'tests/nanalink/test_platform_context_population.py','--basetemp=/tmp/q9a','-o','cache_dir=/tmp/nana-fee8-qualification/pytest-cache-9a'])
core=[m.__file__ for n,m in sys.modules.items() if n.startswith('nana_core') and getattr(m,'__file__',None)]
assert core and all(p.startswith('/tmp/n9a/src/') for p in core)
print('INSTALLED_ORIGINS',json.dumps({'modules':len(core),'all_from_installed_9a':True,'repo_pythonpath':False,'exit_code':code}))
raise SystemExit(code)
