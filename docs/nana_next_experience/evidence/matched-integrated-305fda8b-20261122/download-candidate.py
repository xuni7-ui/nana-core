import hashlib, json, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

root=Path('/tmp/n284remote')
commit='0cfe18dc70610b6b9c9d6e181eac92f6665e643e'
base=f'https://raw.githubusercontent.com/xuni7-ui/nana-core/{commit}/deliveries/nana-space-next/server-305fda8b-candidate/'
with urllib.request.urlopen(base+'SHA256SUMS',timeout=25) as response:
    manifest=response.read(65536)
assert hashlib.sha256(manifest).hexdigest()=='9df3afb5258493590fd417bfd167d3c3b8bda35360b45c78bf24472e9e8f37fa'
(root/'SHA256SUMS').write_bytes(manifest)
entries=[line.split('  ',1) for line in manifest.decode().splitlines()]
assert len(entries)==24

def download(entry):
    expected,name=entry
    target=root/name
    assert target.is_relative_to(root) and '..' not in Path(name).parts
    target.parent.mkdir(exist_ok=True,parents=True)
    request=urllib.request.Request(base+urllib.parse.quote(name))
    digest=hashlib.sha256()
    size=0
    with urllib.request.urlopen(request,timeout=25) as response,target.open('xb') as output:
        for part in iter(lambda:response.read(1024*1024),b''):
            size+=len(part)
            assert size<64*1024*1024
            digest.update(part)
            output.write(part)
    assert digest.hexdigest()==expected,name
    return {'path':name,'bytes':size,'sha256':expected}

with ThreadPoolExecutor(max_workers=4) as executor:
    files=list(executor.map(download,entries))
print(json.dumps({'delivery_commit':commit,'files_sha256_verified':files,'independent_https_raw_download':True},indent=2))
