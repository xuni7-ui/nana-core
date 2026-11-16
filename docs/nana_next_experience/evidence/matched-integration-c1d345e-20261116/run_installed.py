import json,os,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/tmp/nana-8bec-qualification');bundle=Path('/tmp/nc1');temporary=Path('/dev/shm/nct')
assert not temporary.exists(),'OWNED_TEST_DESTINATION_MUST_BE_FRESH'
sys.path[:0]=[str(bundle/'src'),'/tmp/nana-fee8-qualification/test-dependencies',str(root)]
os.chdir(root)
import pytest,pydantic,cryptography,PIL,nana_core
assert all(Path(m.__file__).is_relative_to(bundle/'.venv') for m in (pydantic,cryptography,PIL))
assert json.loads((bundle/'runtime.json').read_text())['source_commit']=='c1d345eca827c226dd1d38e4bb19f8661dbf3abd'
print('INSTALLED_RUNTIME_DEPENDENCIES_AND_SOURCE_VERIFIED',flush=True)
code=pytest.main(['-q','-s','-c',str(root/'pytest.ini'),'-o','pythonpath=',
    'tests/person_self/test_memory_review_choice.py','tests/person_self/test_memory_review_condition.py',
    'tests/person_self/test_deliberated_replan_choice.py','tests/person_self/test_fresh_social_choice.py',
    'tests/person_self/test_expression_lesson_population.py','tests/living_release_v4/test_bilibili_frames.py',
    'tests/living_release_v4/test_bilibili_frame_unknown.py','tests/nanalink/test_platform_context_population.py',
    '--basetemp='+str(temporary),'-o','cache_dir='+str(root/'pytest-cache')])
core=[m.__file__ for name,m in tuple(sys.modules.items()) if name.startswith('nana_core') and getattr(m,'__file__',None)]
assert core and all(Path(p).is_relative_to(bundle/'src') for p in core),[p for p in core if not Path(p).is_relative_to(bundle/'src')]
print('INSTALLED_ORIGINS',json.dumps({'modules':len(core),'all_from_installed_c1d':True,'repo_pythonpath':False,'test_tools_are_external':True,'exit_code':int(code)}))
raise SystemExit(code)
