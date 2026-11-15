import json,sys
from pathlib import Path
old=Path('/tmp/nana-replan-source-cc8')
sys.path.insert(0,str(old))
sys.path.insert(1,str(Path.cwd()))  # Original test helpers, never another Core.
import nana_core.continuity.subject.loop
import nana_core.continuity.subject.policy
import nana_core.continuity.world_loop.cognition
import nana_core.presence.living
assert Path(nana_core.continuity.subject.loop.__file__).is_relative_to(old)
import pytest
result=pytest.main(['-q','-s','-o','pythonpath='+str(old),
    'tests/person_self/test_deliberated_replan_choice.py::test_original_self_can_decline_replan_without_a_second_cue_or_model_phase'])
loaded=[Path(m.__file__).resolve() for name,m in tuple(sys.modules.items())
    if name.startswith('nana_core') and getattr(m,'__file__',None)]
assert loaded and all(p.is_relative_to(old) for p in loaded),[str(p) for p in loaded if not p.is_relative_to(old)]
print(json.dumps({'loaded_core_modules':len(loaded),'all_from_exact_cc8_copy':True,'pytest_exit':int(result)}))
sys.exit(result)
