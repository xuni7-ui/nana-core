"""Isolated installed capability imports and exact sandbox, no Subject creation."""
import argparse
import importlib
import json
from pathlib import Path
import sqlite3
import sys


def run(bundle):
    bundle=Path(bundle).resolve();sys.path.insert(0,str(bundle/'src'))
    import nana_core
    if not Path(nana_core.__file__).resolve().is_relative_to(bundle/'src'):
        raise RuntimeError('REPOSITORY_IMPORT_DETECTED')
    boundary=json.loads((bundle/'runtime-boundary.json').read_text())
    imported=[]
    for name in boundary['runtime_source_assets']:
        if not name.endswith('.py'):continue
        module=name.removeprefix('src/').removesuffix('.py').replace('/','.').removesuffix('.__init__')
        importlib.import_module(module);imported.append(module)
    excluded=['nana_core.fake_world','nana_core.presence.semantic_demo','nana_core.presence.process_qualification','nana_core.continuity.controlled_world.lab']
    for module in excluded:
        try:importlib.import_module(module)
        except ModuleNotFoundError:pass
        else:raise RuntimeError('DEVELOPMENT_CODE_IN_RUNTIME')
    from nana_core.continuity.open_agency.code_skills import IsolatedSkillRunner
    from nana_core.contracts import CoreError
    runner=IsolatedSkillRunner();probe=runner.qualify()
    if probe['state']!='AVAILABLE':raise RuntimeError('ISOLATION_NOT_QUALIFIED')
    result=runner.run('def transform(data):\n return sum(data)\n',[1.25,2.5])
    if result!=3.75:raise RuntimeError('INDEPENDENT_SKILL_RESULT_MISMATCH')
    try:runner.run('def transform(data):\n return open(data).read()\n','/etc/passwd')
    except CoreError:denied=True
    else:raise RuntimeError('SKILL_AST_AUTHORITY_BYPASS')
    return {'execution':'ACTUAL_INSTALLED_MINIMUM_BINDING_OPTIMIZED_ISOLATED','python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'optimize':sys.flags.optimize,'runtime_imports':len(imported),'all_runtime_imports_closed':True,'excluded_modules_unavailable':excluded,'default_demo_started':False,'subject_created_by_probe':False,'sandbox':probe,'actual_pure_skill_result':result,'arbitrary_read_rejected':denied,'new_provider_calls':0,'repository_runtime_imports':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(run(a.bundle),indent=2)+'\n')
