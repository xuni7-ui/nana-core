"""Exact old pure C decision; all other runtime code is unchanged from cfd11be."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/workspace/nana-next-refinement-work');sys.path.insert(0,str(root/'src'));sys.path.insert(1,str(root))
import nana_core.continuity.subject.policy as policy
import nana_core.continuity.subject.loop as loop
base='cfd11be158a3f0fa36abf93f42d5e4fde1f55bf0'
raw=subprocess.check_output(['git','show',base+':src/nana_core/continuity/subject/policy.py'],cwd=root).decode()
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='decide')
scope=dict(policy.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-cfd11be-decide>','exec'),scope)
policy.decide=scope['decide'];loop.decide=scope['decide']
print(json.dumps({'fixed_baseline':base,'old_decide_sha256':hashlib.sha256(ast.get_source_segment(raw,node).encode()).hexdigest(),
    'scope':'only original pure decide; other Core source matches cfd11be except this decision change','runtime_store_copied':False}))
import pytest
sys.exit(pytest.main(['-q','-s','-o','pythonpath='+str(root/'src'),
    'tests/person_self/test_fresh_social_choice.py::test_normal_self_new_wish_still_obeys_original_busy_recipient_admission']))
