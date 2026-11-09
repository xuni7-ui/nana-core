"""Descriptor/ownership/inode/sidecar fence adversaries. Synthetic paths only."""
import asyncio
import json
import os
from pathlib import Path
import socket
import pytest
from test_r041_bridge import fixture,ready
from tools.nana_astrbot_shadow.bridge_wire import DirectoryFence,load_config,validate_socket,canonical
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore

@pytest.mark.parametrize('attack',['symlink','hardlink','fifo','mode','directory','duplicate','truncated','oversize','utf8'])
def test_configuration_rejects_non_owned_or_corrupt_files(tmp_path,attack):
    d=tmp_path/'private';d.mkdir(mode=0o700);p=d/'client.json'
    p.write_text('{}\n');p.chmod(0o600)
    if attack=='symlink':
        p.unlink();target=tmp_path/'other';target.write_text('PRIVATE-SYNTHETIC-CANARY');p.symlink_to(target)
    elif attack=='hardlink':os.link(p,d/'other')
    elif attack=='fifo':p.unlink();os.mkfifo(p,0o600)
    elif attack=='mode':p.chmod(0o644)
    elif attack=='directory':p.unlink();p.mkdir(mode=0o700)
    elif attack=='duplicate':p.write_bytes(b'{"schema_version":1,"schema_version":1}\n')
    elif attack=='truncated':p.write_bytes(b'{"')
    elif attack=='oversize':p.write_bytes(b'x'*8193)
    elif attack=='utf8':p.write_bytes(b'\xff\xfe')
    with pytest.raises((ValueError,OSError)):load_config(p)


def test_directory_descriptor_detects_rename_chmod_and_symlink(tmp_path):
    d=tmp_path/'private';d.mkdir(mode=0o700)
    with DirectoryFence(d) as fence:
        fence.write('test.json',{'scope':'synthetic'})
        d.chmod(0o755)
        with pytest.raises(ValueError):fence.read('test.json')
        d.chmod(0o700);old=d.with_name('old');d.rename(old);d.mkdir(mode=0o700)
        with pytest.raises(ValueError,match='DIRECTORY_DRIFT'):fence.read('test.json')
        # Cleanup follows the retained fd into the original directory, not new path.
        fence.unlink_owned('test.json',anchored=True)
        assert not (old/'test.json').exists() and not list(d.iterdir())


def test_unlink_race_never_deletes_replacement_inode(tmp_path,monkeypatch):
    d=tmp_path/'private';d.mkdir(mode=0o700)
    with DirectoryFence(d) as fence:
        expected=fence.write('test.json',{'original':True})
        real=os.rename;once=False
        def swap(src,dst,*args,**kwargs):
            nonlocal once
            if src=='test.json' and not once:
                once=True
                os.rename(d/'test.json',d/'original.json')
                (d/'test.json').write_text('FOREIGN-SYNTHETIC-CANARY');(d/'test.json').chmod(0o600)
            return real(src,dst,*args,**kwargs)
        monkeypatch.setattr(os,'rename',swap)
        with pytest.raises(ValueError,match='ENTRY_DRIFT'):fence.unlink_owned('test.json',expected)
        assert (d/'test.json').read_text()=='FOREIGN-SYNTHETIC-CANARY'
        assert (d/'original.json').exists()


def test_atomic_write_does_not_follow_symlink_or_overwrite_foreign_file(tmp_path):
    d=tmp_path/'private';d.mkdir(mode=0o700);other=tmp_path/'other';other.write_text('UNCHANGED')
    with DirectoryFence(d) as fence:
        fence.write('test.json',{'original':True})
        (d/'test.json').unlink();(d/'test.json').symlink_to(other)
        with pytest.raises(ValueError,match='ENTRY_DRIFT'):fence.write('test.json',{'changed':True},replace=True)
        assert other.read_text()=='UNCHANGED' and (d/'test.json').is_symlink()
        with pytest.raises(OSError):fence.write('test.json',{},replace=False)

@pytest.mark.parametrize('name',['../outside','/absolute','..','.','a/b','a\0b','a\nb','a'*101])
def test_directory_operations_have_no_path_traversal(tmp_path,name):
    d=tmp_path/'private';d.mkdir(mode=0o700)
    with DirectoryFence(d) as fence:
        with pytest.raises(ValueError):fence.write(name,{})
        assert not list(d.iterdir())


def test_socket_replacement_is_not_deleted_or_accepted(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.2,trust=FixtureTrustStore())
        task,c=await ready(w)
        p=ipc/'bridge.sock';p.rename(ipc/'original.sock')
        foreign=socket.socket(socket.AF_UNIX);foreign.bind(str(p));p.chmod(0o600)
        try:
            with pytest.raises(ValueError,match='SOCKET_FINGERPRINT'):validate_socket(c)
            w.stop_event.set();await task
            assert p.exists()  # unrelated replacement deliberately preserved
            assert not (ipc/'client.json').exists()
        finally:foreign.close()
    asyncio.run(run())


def test_live_directory_swap_blocks_ingress_and_cleans_original_cap(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.2,trust=FixtureTrustStore())
        task,c=await ready(w)
        old=ipc.with_name('old');ipc.rename(old);ipc.mkdir(mode=0o700)
        w.stop_event.set();await task
        assert not list(ipc.iterdir())
        assert not (old/'bridge.sock').exists() and not (old/'client.json').exists()
        assert not w.observer.active
    asyncio.run(run())


def test_long_socket_path_blocks_before_session_consumption(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    long=tmp_path/('i'*80);long.mkdir(mode=0o700)
    with pytest.raises(ValueError,match='SOCKET_PATH_LENGTH'):
        ShortLivedWorker(root,long,r.receipt_id,client_pid=os.getpid(),trust=FixtureTrustStore())


def test_fence_releases_validated_and_replaced_file_descriptors(tmp_path):
    # Repeated writes must pin removed inodes against ABA only for this fence's
    # lifetime. Exercise both successful reads and failed foreign replacements.
    d=tmp_path/'private';d.mkdir(mode=0o700)
    before=len(list(Path('/proc/self/fd').iterdir()))
    for cycle in range(3):
        with DirectoryFence(d) as fence:
            for version in range(12):
                fence.write('test.json',{'version':version},replace=version>0)
                assert json.loads(fence.read('test.json'))=={'version':version}
            fence.unlink_owned('test.json')
            foreign=d/'test.json';foreign.write_text('FOREIGN');foreign.chmod(0o600)
            with pytest.raises(ValueError,match='ENTRY_NOT_OWNED'):
                fence.write('test.json',{},replace=True)
            assert foreign.read_text()=='FOREIGN'
            foreign.unlink()
        assert not list(d.iterdir())
        assert len(list(Path('/proc/self/fd').iterdir()))==before
