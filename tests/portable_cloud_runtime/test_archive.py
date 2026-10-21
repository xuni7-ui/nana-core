import hashlib,io,tarfile,json,importlib.util
from pathlib import Path
import pytest
from tools.nana_portable_cloud.unpack import unpack

@pytest.mark.parametrize('kind',['traversal','absolute','symlink','hardlink','duplicate','oversize'])
def test_archive_rejects_before_creating_destination(tmp_path,kind):
 p=tmp_path/'bad.tar.gz'
 with tarfile.open(p,'w:gz') as tar:
  name={'traversal':'nana-first-life-portable-v1/../../escape','absolute':'/escape'}.get(kind,'nana-first-life-portable-v1/file')
  info=tarfile.TarInfo(name);info.size=0
  if kind in {'symlink','hardlink'}:info.type=tarfile.SYMTYPE if kind=='symlink' else tarfile.LNKTYPE;info.linkname='/etc/passwd'
  if kind=='oversize':
   info.size=65*1024*1024
   class Zeros:
    def read(self,n):return b'\0'*n
   tar.addfile(info,Zeros())
  else:tar.addfile(info)
  if kind=='duplicate':tar.addfile(info)
 dest=tmp_path/'dest'
 with pytest.raises(ValueError):unpack(p,dest,hashlib.sha256(p.read_bytes()).hexdigest())
 assert not dest.exists()


def test_valid_archive_checksum_occupied_and_permissions(tmp_path):
 p=tmp_path/'good.tar.gz'
 with tarfile.open(p,'w:gz') as tar:
  info=tarfile.TarInfo('nana-first-life-portable-v1/nana');info.size=3;info.mode=0o755;tar.addfile(info,io.BytesIO(b'abc'))
 sha=hashlib.sha256(p.read_bytes()).hexdigest();dest=tmp_path/'dest'
 with pytest.raises(ValueError):unpack(p,dest,'0'*64)
 unpack(p,dest,sha);assert (dest/'nana').read_bytes()==b'abc' and dest.stat().st_mode&0o077==0
 with pytest.raises(ValueError):unpack(p,dest,sha)


def test_bootstrap_manifest_detects_file_and_symlink_tamper(tmp_path):
 source=Path(__file__).resolve().parents[2]/'packaging/portable/bootstrap.py'
 spec=importlib.util.spec_from_file_location('portable_bootstrap',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 p=tmp_path/'a';p.write_text('source');(tmp_path/'SHA256SUMS').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  a\n');m.verify(tmp_path)
 p.write_text('changed')
 with pytest.raises(ValueError):m.verify(tmp_path)
 p.unlink();p.symlink_to(source)
 with pytest.raises(ValueError):m.verify(tmp_path)


def test_member_count_rejected_before_destination_creation(tmp_path):
 p=tmp_path/'headers.tar.gz'
 with tarfile.open(p,'w:gz') as tar:
  for i in range(4097):tar.addfile(tarfile.TarInfo('nana-first-life-portable-v1/file-'+str(i)))
 dest=tmp_path/'dest'
 with pytest.raises(ValueError,match='ARCHIVE_MEMBERS_DENIED'):unpack(p,dest,hashlib.sha256(p.read_bytes()).hexdigest())
 assert not dest.exists()


def test_total_decompression_bound_covers_hidden_metadata(tmp_path):
 import gzip
 p=tmp_path/'bomb.tar.gz'
 with gzip.open(p,'wb') as f:
  for _ in range(69):f.write(b'\0'*(1024*1024))
 dest=tmp_path/'dest'
 with pytest.raises(ValueError,match='ARCHIVE_DECOMPRESSION_BOUND'):unpack(p,dest,hashlib.sha256(p.read_bytes()).hexdigest())
 assert not dest.exists()
