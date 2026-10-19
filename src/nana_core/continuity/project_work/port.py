"""Sealed exact-manifest project adapter; local outputs, no execute/network/send.

Manifest is trusted host configuration, NOT a Grant. Kernel still requires exact
Grant, budget, Manager and current C intention. Output files are user artifacts,
not a second Subject Store. No automatic replay of unknown writes.
"""
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from ...contracts import CoreError, DTO, Receipt, Verification
from ...storage import canonical, digest
from pydantic import Field
from typing import Literal
from .analysis import inventory


class ProjectMaterial(DTO):
    material_id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,47}$')
    relative_path: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    privacy_class: str = 'PROJECT'
    task_type: Literal['PYTHON_API','MARKDOWN_OUTLINE'] = 'PYTHON_API'


def read_material_bytes(root, relative_path, *, task_type="PYTHON_API"):
    """Read one explicit task-typed .py/.md file before computing manifest digest."""
    rel = PurePosixPath(relative_path)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.suffix != {'PYTHON_API':'.py','MARKDOWN_OUTLINE':'.md'}.get(task_type):
        raise CoreError('PROJECT_MANIFEST_DENIED')
    root = Path(root).absolute()
    if root != root.resolve():raise CoreError('PROJECT_ROOT_SYMLINK')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in rel.parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
        filefd = os.open(rel.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        import stat
        with os.fdopen(filefd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise CoreError('PROJECT_REGULAR_FILE_REQUIRED')
            raw = stream.read(6145)
    except OSError:
        raise CoreError('PROJECT_SOURCE_UNAVAILABLE') from None
    finally:
        os.close(fd)
    if not raw or len(raw)>6144:raise CoreError('PROJECT_SOURCE_BOUND')
    return raw


def read_material(root, material):
    if material.privacy_class != 'PROJECT':raise CoreError('PROJECT_MANIFEST_DENIED')
    raw=read_material_bytes(root, material.relative_path,task_type=material.task_type)
    if hashlib.sha256(raw).hexdigest() != material.sha256:raise CoreError('PROJECT_SOURCE_CHANGED')
    return {'filename': material.relative_path, 'sha256': material.sha256, 'source': raw.decode('utf-8')}


class ProjectMaterialPort:
    evidence_namespace = 'recorded.project.local-action'
    def __init__(self, identity_id, root, materials, output_directory):
        self.identity_id = identity_id
        self.root = Path(root).absolute()
        self.output = Path(output_directory).absolute()
        if self.root!=self.root.resolve() or self.output!=self.output.resolve() or self.root.is_symlink() or self.output.is_symlink() or self.root == self.output or self.root in self.output.parents:
            raise CoreError('PROJECT_OUTPUT_MUST_BE_SEPARATE')
        self.output.mkdir(parents=True, mode=0o700, exist_ok=True)
        if self.output.stat().st_mode & 0o077:raise CoreError('PROJECT_PRIVATE_OUTPUT_REQUIRED')
        self.materials = {m.material_id: m.model_copy() for m in materials}
        if not 1 <= len(materials) <= 16 or len(self.materials) != len(materials):raise CoreError('PROJECT_MANIFEST_BOUND')
        self.permitted_privacy = ('PROJECT',)
        for m in self.materials.values():read_material(self.root, m)

    def skill_for(self,method):
        rid=getattr(self,'skill_bindings',{}).get(method)
        if rid:
            self.code_skills.require_current(rid)
        return rid

    def _valid(self, inv):
        from ..open_agency.world import LocalWorldRegistry
        args = LocalWorldRegistry().validate(inv.capability, inv.resource, inv.args)
        match = re.fullmatch(r'project://([a-z][a-z0-9_-]{0,47})/(source|inventory|report)', inv.resource)
        if not match or match[1] not in self.materials:raise CoreError('PROJECT_RESOURCE_DENIED')
        operation = {'source': 'world.observe', 'inventory': 'world.compute', 'report': 'world.publish'}[match[2]]
        if inv.capability != operation and not (match[2]=='inventory' and inv.capability=='world.skill'):raise CoreError('PROJECT_OPERATION_DENIED')
        if 'PROJECT' not in self.permitted_privacy:raise CoreError('PROJECT_PRIVACY_DENIED')
        return match[1], args

    def _result(self, inv):
        key, args = self._valid(inv)
        material = self.materials[key]
        source = read_material(self.root, material)
        if inv.capability == 'world.observe':
            return {'data': source, 'data_privacy': 'PROJECT', 'origin': 'DEVELOPMENT_PROJECT', 'source_digest': material.sha256}
        if args['data_privacy'] != 'PROJECT':raise CoreError('PROJECT_PRIVACY_DOWNGRADE')
        if inv.capability in {'world.compute','world.skill'}:
            if args['data'] != source:raise CoreError('PROJECT_INPUT_SOURCE_MISMATCH')
            if inv.capability=='world.skill':
                controller=getattr(self,'code_skills',None)
                if not controller:raise CoreError('CODE_SKILL_CONTROLLER_UNAVAILABLE')
                binding=getattr(self,'skill_bindings',{})
                method=next((m for m,rid in binding.items() if rid==args['skill_record_id']),None)
                if material.task_type!='MARKDOWN_OUTLINE' or not method:raise CoreError('PROJECT_SKILL_NOT_BOUND')
                data=controller.invoke(args['skill_record_id'],source)
            else:method=args['method'];data=analyze_material(material.task_type,method,source)
            return {'data': data, 'data_privacy': 'PROJECT', 'method': method, **({'skill_record_id':args['skill_record_id']} if inv.capability=='world.skill' else {}), 'origin': 'LOCAL_SOURCE_ANALYSIS', 'source_digest': material.sha256}
        # Publish only a bounded symbol inventory for this exact source. The report
        # cannot contain arbitrary copied source prose or turn into a file writer.
        if args['data'] != expected_material(material.task_type,source):raise CoreError('PROJECT_REPORT_UNVERIFIED')
        stem = hashlib.sha256(inv.idempotency_key.encode()).hexdigest()
        return {'data': args['data'], 'data_privacy': 'PROJECT', 'origin': 'LOCAL_ARTIFACT', 'source_digest': material.sha256, 'source_path': material.relative_path, 'artifact_stem': stem, **({'task_type':material.task_type} if material.task_type!='PYTHON_API' else {})}

    def _documents(self, result):
        rows = result['data']
        if result.get('task_type')=='MARKDOWN_OUTLINE':
            text='# Document navigation audit\n\n'+result['source_path']+'\n\nSHA256: '+result['source_digest']+'\n\n'
            text+='| Level | Title | Source line |\n| --- | --- | --- |\n'
            text+=''.join(f"| {r['level']} | {r['title'].replace('|', '&#124;')} | {r['line']} |\n" for r in rows)
            text+='\nChecked independently using an anchored grammar oracle. Column-zero ATX headings outside triple-backtick fences; not a full CommonMark audit. No links fetched or source executed.\n'
            return {'json':canonical(result).encode(),'md':text.encode()}
        text = '# Source interface inventory\n\n' + result['source_path'] + '\n\nSHA256: ' + result['source_digest'] + '\n\n'
        text += '| Symbol | Kind | Source line |\n| --- | --- | --- |\n'
        text += ''.join(f"| `{r['name']}` | {r['kind']} | {r['line']} |\n" for r in rows)
        text += '\nChecked with independent compiler symbol tables. No source code was executed.\n'
        return {'json': canonical(result).encode(), 'md': text.encode()}

    def execute(self, inv):
        result = self._result(inv)
        if inv.capability == 'world.publish':
            # One private directory FD prevents path substitution during writes.
            directory = os.open(self.output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for suffix, raw in self._documents(result).items():
                    name = result['artifact_stem'] + '.' + suffix
                    try:
                        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
                    except FileExistsError:
                        raise CoreError('PROJECT_ARTIFACT_EXISTS_VERIFY_ONLY') from None
                    with os.fdopen(fd, 'wb') as stream:stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                os.fsync(directory)
            finally:os.close(directory)
        return Receipt(external_id=inv.idempotency_key, result=result)

    def verify(self, inv):
        try:
            result = self._result(inv)
            if inv.capability == 'world.publish':
                docs = self._documents(result)
                present = [self.output / (result['artifact_stem'] + '.' + suffix) for suffix in docs]
                if not any(p.exists() for p in present):return Verification(verdict='FINAL_NO_EFFECT', evidence={})
                directory=os.open(self.output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    import stat
                    for suffix,raw in docs.items():
                        fd=os.open(result['artifact_stem']+'.'+suffix,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
                        with os.fdopen(fd,'rb') as stream:
                            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):return Verification(verdict='INCONCLUSIVE',evidence={})
                            if stream.read(32769)!=raw:return Verification(verdict='EFFECT_MISMATCH',evidence={})
                finally:os.close(directory)
            return Verification(verdict='MATCH', evidence={'result': result, 'digest': digest(result)})
        except (CoreError, OSError, ValueError):
            return Verification(verdict='INCONCLUSIVE', evidence={})


def analyze_material(task_type,method,source):
    if task_type=='PYTHON_API':return inventory(method,source)
    from .documents import outline
    return outline(method,source)


def expected_material(task_type,source):
    if task_type=='PYTHON_API':
        from .oracle import expected_inventory
        return expected_inventory(source)
    from .documents import expected_outline
    return expected_outline(source)
