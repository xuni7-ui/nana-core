import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

p=argparse.ArgumentParser()
p.add_argument('commit')
p.add_argument('destination',type=Path)
a=p.parse_args()
assert re.fullmatch(r'[0-9a-f]{40}',a.commit)
a.destination.mkdir()
base=f'https://raw.githubusercontent.com/xuni7-ui/nana-core/{a.commit}/deliveries/nana-space-next/server-3377a5c-candidate/'
with urllib.request.urlopen(base+'SHA256SUMS',timeout=25) as source:
    data=source.read(65537)
assert hashlib.sha256(data).hexdigest()=='9ea60a66912f28fb8a2347eccffb3860391b49b9e7ccddccfd5e150107171b7c'
entries=[line.split('  ',1) for line in data.decode().splitlines()]
assert len(entries)==len({name for _,name in entries})==29
(a.destination/'SHA256SUMS').write_bytes(data)

def download(entry):
    expected,name=entry
    path=PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    target=a.destination/name
    target.parent.mkdir(exist_ok=True,parents=True)
    sha=hashlib.sha256()
    size=0
    with urllib.request.urlopen(base+urllib.parse.quote(name),timeout=25) as source,target.open('xb') as output:
        for block in iter(lambda:source.read(1024*1024),b''):
            size+=len(block)
            assert size<64*1024*1024
            sha.update(block)
            output.write(block)
    assert sha.hexdigest()==expected,name
    return {'path':name,'bytes':size,'sha256':expected}

with ThreadPoolExecutor(max_workers=4) as executor:
    details=list(executor.map(download,entries))
print(json.dumps({'delivery_commit':a.commit,'files_sha256_verified':details,'independent_https_raw_download':True},indent=2))
