#!/bin/sh
set -eu
release_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -I -B -c '
import hashlib,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]);expected=sys.argv[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('"'"'rb'"'"') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
p=root/'"'"'MANIFEST.json'"'"'
if p.is_symlink() or sha(p)!=expected:raise SystemExit('"'"'RELEASE_MANIFEST_MISMATCH'"'"')
value=json.loads(p.read_bytes())
for name,row in value['"'"'files'"'"'].items():
 p=root/name
 if Path(name).is_absolute() or '"'"'..'"'"' in Path(name).parts or p.resolve()!=p or not p.is_file():raise SystemExit('"'"'RELEASE_FILE_INVALID: '"'"'+name)
 if sha(p)!=row['"'"'sha256'"'"']:raise SystemExit('"'"'RELEASE_FILE_DIGEST_MISMATCH: '"'"'+name)
os.execv(sys.executable,[sys.executable,'"'"'-I'"'"','"'"'-B'"'"',str(root/'"'"'tools/deploy.py'"'"'),'"'"'--handoff'"'"',str(root),'"'"'--manifest-sha256'"'"',expected,*sys.argv[3:]])
' "$release_root" 6bd155ad232b4e5741f08dcff47105e54472fd00854b91a35a88280f3cda0d68 "$@"
