import ast, hashlib, importlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

repo = Path('/workspace/nana-next-refinement-work')
root = Path('/tmp/nana-284-candidate/installed-qualification')
slot = Path('/tmp/n284slot')
base = root.parent
source = json.loads((slot/'runtime.json').read_text())['source_commit']
assert source == '305fda8b98ae0ae1040301eb758d91a27497f442'
selected = [
    'tests/person_self/test_relational_cognitive_choice.py',
    'tests/open_life/test_meta_learning.py',
    'tests/world_loop/test_perception_reuse.py',
    'tests/world_loop/test_media_stream_binding.py',
]

def blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

tracked = {}
for line in subprocess.check_output(['git','ls-tree','-r',source],cwd=repo,text=True).splitlines():
    header,path = line.split('\t',1)
    tracked[path] = header.split()[2]
manifest = (repo/'packaging/portable/runtime-files.txt').read_bytes()
assert blob(manifest) == tracked['packaging/portable/runtime-files.txt']
runtime_paths = [line for line in manifest.decode().splitlines() if line and not line.startswith('#')]
for path in runtime_paths:
    assert blob((slot/path).read_bytes()) == tracked[path], path

queue = selected[:]
fixture_sources = {}
def follow(module):
    for path in (module.replace('.','/')+'.py', module.replace('.','/')+'/__init__.py'):
        if path in tracked and path.startswith(('tests/','tools/')):
            queue.append(path)
while queue:
    path = queue.pop()
    if path in fixture_sources:
        continue
    data = (repo/path).read_bytes()
    assert blob(data) == tracked[path], path
    dest = root/path
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    fixture_sources[path] = hashlib.sha256(data).hexdigest()
    for parent in Path(path).parents:
        for name in ('__init__.py','conftest.py'):
            candidate = str(parent/name)
            if candidate in tracked:
                queue.append(candidate)
    package = '.'.join(Path(path).parent.parts)
    for node in ast.walk(ast.parse(data)):
        if isinstance(node,ast.Import):
            for alias in node.names:
                follow(alias.name)
        elif isinstance(node,ast.ImportFrom):
            name = importlib.util.resolve_name('.'*node.level+(node.module or ''),package) if node.level else node.module or ''
            follow(name)
            for alias in node.names:
                follow(name+'.'+alias.name)
(root/'pytest.ini').write_text('[pytest]\naddopts = -ra --strict-markers\n')
assert not (root/'src/nana_core').exists()
sys.path[:0] = [str(slot/'src'),str(root)]
sys.path.append('/workspace/nana-test-env/lib/python3.12/site-packages')
os.chdir(root)
import pytest, pydantic, PIL
for package in (pydantic,PIL):
    assert Path(package.__file__).is_relative_to(slot/'.venv')
external = set()
for suffix in ('continuity/open_agency/fixtures.py','continuity/world_loop/reference.py','continuity/world_loop/harness.py'):
    path = base/'qualification'/suffix
    assert blob(path.read_bytes()) == tracked['src/nana_core/'+suffix],suffix
    name = 'nana_core.'+suffix.removesuffix('.py').replace('/','.')
    importlib.import_module(name.rpartition('.')[0])
    spec = importlib.util.spec_from_file_location(name,path)
    item = importlib.util.module_from_spec(spec)
    sys.modules[name] = item
    spec.loader.exec_module(item)
    external.add(name)
print(json.dumps({'source':source,'installed_blobs_verified':len(runtime_paths),'fixed_fixture_files':len(fixture_sources),'external_factories':len(external)}),flush=True)
code = pytest.main(['-q','-s','-c',str(root/'pytest.ini'),*selected,'--basetemp=/dev/shm/n284installed','-o','cache_dir=/dev/shm/n284installedcache'])
modules = [Path(m.__file__) for name,m in tuple(sys.modules.items()) if name.startswith('nana_core') and name not in external and getattr(m,'__file__',None)]
assert modules and all(path.is_relative_to(slot/'src') for path in modules)
(base/'installed-targets.json').write_text(json.dumps({'source_commit':source,'runtime_files':len(runtime_paths),'installed_business_modules':len(modules),'external_factories':sorted(external),'exit_code':int(code),'selected_tests':selected,'fixture_source_sha256':fixture_sources},indent=2)+'\n')
raise SystemExit(code)
