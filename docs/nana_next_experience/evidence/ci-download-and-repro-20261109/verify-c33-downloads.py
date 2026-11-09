from pathlib import Path,PurePosixPath
import hashlib,json,zipfile,stat
root=Path('/workspace/scratch/nana-c33-downloaded');root.mkdir(mode=0o700)
items=[('portable',Path('/workspace/attachments/7dcb50d1-aeaa-4edd-a609-f719f8d64de5/nana-c33-portable-candidate.zip'),'bb4c1e627ae63ed1748d15199fe445879849867b0caf585e62611a96ccc57068'),('client',Path('/workspace/attachments/65e97484-4da5-42b9-8cf5-2ca42de40d9b/nana-c33-client-qualified.zip'),'a546cfe78486ffc6bdbd91a75e2caf4062a79d6d1e6a9d76ee6290108af2311b')]
result={}
for name,path,expected in items:
 sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==expected
 dest=root/name;dest.mkdir(mode=0o700);total=0
 with zipfile.ZipFile(path) as z:
  names=set()
  for item in z.infolist():
   p=PurePosixPath(item.filename);total+=item.file_size
   assert not p.is_absolute() and '..' not in p.parts and '\\' not in item.filename and item.filename not in names and not stat.S_ISLNK(item.external_attr>>16)
   names.add(item.filename);assert len(names)<=4096 and total<=64*1024*1024
   target=dest.joinpath(*p.parts)
   if item.is_dir():target.mkdir(parents=True,exist_ok=True,mode=0o700)
   else:target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_bytes(z.read(item));target.chmod(0o600)
 result[name]={'downloaded_zip_sha256':sha,'zip_bytes':path.stat().st_size,'entries':len(names),'uncompressed_bytes':total,'destination':str(dest)}
metadata=json.loads((root/'portable/source-and-build.json').read_text());assert metadata['source_commit']=='c33d94717736f8aeeaef95c341a4cbb7287ad8e1' and metadata['two_builds_match'] is True and metadata['offline_install']=='PASS'
archive=root/'portable/nana-first-life-portable-v1.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==metadata['sha256']
result['bundle']=metadata
(root/'download-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
