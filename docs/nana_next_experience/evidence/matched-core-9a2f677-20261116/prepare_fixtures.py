import ast,hashlib,importlib.util,json,subprocess
from pathlib import Path
repo=Path('/workspace/nana-next-refinement-work');out=Path('/tmp/nana-262-local-qualification');assert not out.exists();out.mkdir(mode=0o700)
sha='9a2f6771979532e8ad2c33db8121dda148b439e8'
selected=['tests/person_self/test_compaction_durability.py','tests/person_self/test_growth_context_compaction.py','tests/person_self/test_growth_context_population.py','tests/person_self/test_growth_attention_visibility.py','tests/person_self/test_growth_assessment_identity.py','tests/person_self/test_growth_inner_choice.py','tests/person_self/test_private_growth_origin.py','tests/person_self/test_tendency_elapsed_context.py','tests/nanalink/test_platform_context_population.py','tests/continuous_self/test_privacy.py','tests/living_release_v4/test_bilibili_frames.py','tests/living_release_v4/test_bilibili_frame_unknown.py']
tree={}
for line in subprocess.check_output(['git','ls-tree','-r',sha],cwd=repo,text=True).splitlines():
 header,name=line.split('\t',1);tree[name]=header.split()[2]
queue=selected[:];seen={};missing=[]
def push_module(name):
 for path in (name.replace('.','/')+'.py',name.replace('.','/')+'/__init__.py'):
  if path in tree and path.startswith(('tests/','tools/')):queue.append(path)
while queue:
 name=queue.pop()
 if name in seen:continue
 p=repo/name;assert p.is_file(),name;raw=p.read_bytes()
 # Match the committed Git blob without requiring a lazy remote blob fetch.
 oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert oid==tree[name],name
 target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);seen[name]=hashlib.sha256(raw).hexdigest()
 parent=Path(name).parent
 while str(parent) not in ('.',''):
  for child in ('__init__.py','conftest.py'):
   dep=(parent/child).as_posix()
   if dep in tree:queue.append(dep)
  parent=parent.parent
 package='.'.join(Path(name).parent.parts)
 for node in ast.walk(ast.parse(raw)):
  if isinstance(node,ast.Import):
   for alias in node.names:push_module(alias.name)
  elif isinstance(node,ast.ImportFrom):
   base=importlib.util.resolve_name('.'*node.level+(node.module or ''),package) if node.level else node.module or ''
   push_module(base)
   for alias in node.names:push_module(base+'.'+alias.name)
old=json.loads(Path('/tmp/nana-8bec-qualification/fixture-source-sha256.json').read_text())
for name in old['file_sha256']:
 if name.startswith('src/'):
  raw=(repo/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==tree[name]
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);seen[name]=hashlib.sha256(raw).hexdigest()
(out/'pytest.ini').write_text('[pytest]\naddopts = -ra --strict-markers\n')
assert not(out/'src/nana_core/__init__.py').exists()
(out/'fixture-source-sha256.json').write_text(json.dumps({'source':sha,'selected_tests':selected,'file_sha256':seen,'runtime_store_copied':False,'local_git_blobs_matched':True,'bulk_archive_lazy_fetch_cancelled':True},indent=2)+'\n')
print(json.dumps({'fixed_fixture_files':len(seen),'selected_test_files':len(selected),'runtime_shadow_package':False}))
