from pathlib import Path
import hashlib,json,subprocess
repo=Path('/tmp/nana-262-remote.git');out=Path('/tmp/nana-262-downloaded');assert not out.exists();out.mkdir(mode=0o700)
sha='ca76503896f496fd245fb7ac668eaab064b00c4b';prefix='deliveries/nana-space-next/server-9a2f677-candidate/'
assert subprocess.check_output(['git','--git-dir='+str(repo),'rev-parse','HEAD'],text=True).strip()==sha
names=subprocess.check_output(['git','--git-dir='+str(repo),'ls-tree','-r','--name-only',sha,'--',prefix],text=True).splitlines();assert len(names)==11
for name in names:
 rel=name.removeprefix(prefix);assert '/' not in rel and rel not in ('','.','..')
 raw=subprocess.check_output(['git','--git-dir='+str(repo),'show',sha+':'+name],timeout=60);(out/rel).write_bytes(raw);print('DOWNLOADED_FIXED_BLOB',rel,len(raw),flush=True)
entries=(out/'SHA256SUMS').read_text().splitlines()
for line in entries:
 expected,name=line.split('  ',1);assert hashlib.sha256((out/name).read_bytes()).hexdigest()==expected
assert len(entries)==10
Path('/workspace/nana-262-remote-download.json').write_text(json.dumps({'git_clone':'FRESH_REMOTE_BARE_FILTERED_SHALLOW_NO_REFERENCE','fixed_delivery_commit':sha,'source_commit':'9a2f6771979532e8ad2c33db8121dda148b439e8','downloaded_files':11,'verified_sha256_entries':10,'http_anonymous_artifact':'NOT_VERIFIED','independent_install':'PENDING'},indent=2)+'\n')
