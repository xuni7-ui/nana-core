"""Exact runtime packaging and optional readiness, not new behavior authority."""
from pathlib import Path
import ast
import json
import pytest
from tools.nana_portable_cloud.build import verify_runtime_closure

ROOT=Path(__file__).resolve().parents[2]


def test_reviewed_manifest_closes_imports_and_keeps_dynamic_assets():
    names=[n for n in (ROOT/'packaging/portable/runtime-files.txt').read_text().splitlines() if n and not n.startswith('#')]
    all_names=[p.relative_to(ROOT).as_posix() for p in (ROOT/'src/nana_core').rglob('*.py')]
    read=lambda name:(ROOT/name).read_text()
    for name in names:
        if name.endswith('.py'):
            assert not any(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(read(name))))
    verify_runtime_closure(names,all_names,read)
    for name in ('src/nana_core/presence/semantic_demo.py','src/nana_core/continuity/controlled_world/lab.py','src/nana_core/fake_world.py'):
        assert name not in names
    for name in ('continuity/open_agency/code_skills.py','continuity/open_agency/checkpoints.py','continuity/provider_routing.py','life/portable_runtime.py'):
        assert 'src/nana_core/'+name in names
    with pytest.raises(ValueError,match='RUNTIME_IMPORT_MISSING'):
        verify_runtime_closure([n for n in names if n!='src/nana_core/host_requirements.py'],all_names,read)
    with pytest.raises(ValueError,match='RUNTIME_DYNAMIC_ASSET_MISSING'):
        verify_runtime_closure([n for n in names if not n.endswith('skill_runner.py')],all_names,read)


def test_missing_optional_sandbox_does_not_falsely_block_base_runtime(tmp_path,monkeypatch):
    from nana_core.continuity.open_agency.code_skills import IsolatedSkillRunner
    from nana_core.life.portable_runtime import preflight
    monkeypatch.setattr(IsolatedSkillRunner,'qualify',lambda self:{'state':'UNAVAILABLE','code':'BWRAP_NOT_FOUND','execution_authority':False})
    (tmp_path/'runtime.json').write_text(json.dumps({'dependencies':{}}))
    home=tmp_path/'absent'
    view=preflight(tmp_path,home)
    assert view['state']=='PREFLIGHT_PASS' and view['optional_capabilities']['generated_python_skill']['state']=='UNAVAILABLE'
    assert not home.exists()
