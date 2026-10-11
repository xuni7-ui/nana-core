"""Dormant CapabilityPort preparation for an isolated engineering workspace.

Reuse Bridge TaskSpec/check_boundaries; never invoke CodexRunner/execute_task,
its shell path or credential/config loaders. Core's closed V1 capability registry
has no engineering.* authorization; this port always refuses execution/receipt.
"""
import importlib.util
from pathlib import Path,PurePosixPath
import sys
from typing import Literal
from pydantic import Field
from ..contracts import DTO,CoreError


class EngineeringTask(DTO):
    operation:Literal['inspect_repository','read_file','patch_file','run_tests','inspect_diff','create_commit']
    path:str|None=None
    new_content:str|None=Field(default=None,max_length=16_384)
    test_id:str|None=None
    branch:str=Field(pattern=r'^dev/[a-zA-Z0-9_/-]+$')
    commit_message:str|None=Field(default=None,max_length=256)


def bridge_contracts():
    name='nana_bridge_preparation_contracts'
    if name in sys.modules:return sys.modules[name]
    path=Path(__file__).resolve().parents[3]/'bridge'/'codex_bridge.py'
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module)
    return module


class EngineeringPreparationPort:
    def __init__(self,workspace,allow_paths,test_targets):
        self.workspace=Path(workspace).resolve()
        live=Path(__file__).resolve().parents[3]
        if self.workspace==live or live in self.workspace.parents:raise CoreError('LIVE_CORE_WORKSPACE_FORBIDDEN')
        if not self.workspace.is_dir():raise CoreError('ISOLATED_WORKSPACE_REQUIRED')
        self.allow_paths=tuple(allow_paths);self.test_targets=dict(test_targets)
        for path in self.allow_paths:self._path(path)
        for argv in self.test_targets.values():
            if (not isinstance(argv,tuple) or len(argv)<4 or argv[:3]!=('python','-m','pytest') or
                any(arg not in self.allow_paths or not arg.startswith('tests/') for arg in argv[3:])):
                raise CoreError('ENGINEERING_TEST_TARGET_REJECTED')
    def _path(self,value):
        if not isinstance(value,str):raise CoreError('ENGINEERING_PATH_REJECTED')
        path=PurePosixPath(value)
        if path.is_absolute() or '..' in path.parts or str(path)!=value or '\\' in value:
            raise CoreError('ENGINEERING_PATH_REJECTED')
        lower=value.casefold()
        if any(s in lower for s in ('.git','.env','secret','credential','token','cookie','password','data_v4','nana_core')):
            raise CoreError('ENGINEERING_SENSITIVE_PATH_REJECTED')
        target=self.workspace/path
        # Refuse symlinks even if they resolve into the same workspace.
        if any(part.is_symlink() for part in (target,*target.parents)):raise CoreError('ENGINEERING_SYMLINK_REJECTED')
        if self.workspace not in target.resolve().parents:raise CoreError('ENGINEERING_PATH_REJECTED')
        return value
    def prepare(self,task):
        task=EngineeringTask.model_validate(task.model_dump())
        paths=[]
        if task.operation in {'read_file','patch_file'}:
            path=self._path(task.path)
            if path not in self.allow_paths:raise CoreError('ENGINEERING_PATH_NOT_ALLOWED')
            paths=[path]
        if task.operation=='patch_file' and task.new_content is None:raise CoreError('PATCH_CONTENT_REQUIRED')
        if task.operation=='run_tests' and task.test_id not in self.test_targets:raise CoreError('ENGINEERING_TEST_NOT_ALLOWED')
        if task.operation=='create_commit' and not task.commit_message:raise CoreError('DEVELOPMENT_COMMIT_MESSAGE_REQUIRED')
        bridge=bridge_contracts()
        spec=bridge.TaskSpec(task_id='synthetic-engineering-preview',goal='Prepare '+task.operation,
            repo=str(self.workspace),allow_paths=list(self.allow_paths),deny_paths=list(bridge.HARD_DENY),test_command=None)
        if bridge.check_boundaries(paths,spec):raise CoreError('BRIDGE_BOUNDARY_REJECTED')
        return {'capability':'engineering.'+task.operation,'workspace_kind':'isolated_development','bridge_task_spec':spec,
            'planned_test_argv':self.test_targets.get(task.test_id),'execution':'NOT_ENABLED','core_authorization':'BLOCKED_UNKNOWN_CAPABILITY',
            'no_shell':True,'no_merge_deploy_push':True}
    def execute(self,invocation):raise CoreError('ENGINEERING_CAPABILITY_NOT_ENABLED')
    def verify(self,invocation):raise CoreError('NO_ENGINEERING_EXECUTION_EVIDENCE')
