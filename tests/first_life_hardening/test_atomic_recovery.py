import errno,json,os,signal,subprocess,sys
from pathlib import Path
import pytest
from nana_core.life.durability import _atomic,read_window,StorageWindow


def test_failed_replace_preserves_guard_and_removes_partial_temp(tmp_path,monkeypatch):
    p=tmp_path/'storage-monitor.json';before=StorageWindow(started_us=1,window_us=1,logical_bytes=12)
    _atomic(p,before.model_dump_json())
    def full(*args):raise OSError(errno.ENOSPC,'synthetic disk full')
    monkeypatch.setattr(os,'replace',full)
    with pytest.raises(OSError):_atomic(p,StorageWindow(started_us=1,window_us=2,logical_bytes=99).model_dump_json())
    assert read_window(p)==before and not list(tmp_path.glob('.storage-*'))


@pytest.mark.parametrize('cut',['BEFORE_REPLACE','AFTER_REPLACE'])
def test_sigkill_guard_is_complete_old_or_new(tmp_path,cut):
    p=tmp_path/'storage-monitor.json';before=StorageWindow(started_us=1,window_us=1,logical_bytes=12)
    after=StorageWindow(started_us=1,window_us=2,logical_bytes=99,status='STATE_SIZE_LIMIT_STOP')
    _atomic(p,before.model_dump_json())
    program='''import os,sys\nfrom pathlib import Path\nfrom nana_core.life.durability import _atomic\noriginal=os.replace\ndef replace(a,b):\n if sys.argv[2]=='AFTER_REPLACE':original(a,b)\n print('CUT',flush=True)\n sys.stdin.buffer.read(1)\n if sys.argv[2]=='BEFORE_REPLACE':original(a,b)\nos.replace=replace\n_atomic(Path(sys.argv[1]),sys.argv[3])\n'''
    proc=subprocess.Popen([sys.executable,'-c',program,str(p),cut,after.model_dump_json()],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:
        import selectors
        with selectors.DefaultSelector() as ready:
            ready.register(proc.stdout,selectors.EVENT_READ)
            assert ready.select(4),'child never reached fsync/replace cut'
        assert proc.stdout.readline()==b'CUT\n'
        proc.kill();proc.wait(3);assert proc.returncode==-signal.SIGKILL
        assert read_window(p)==(before if cut=='BEFORE_REPLACE' else after)
    finally:
        if proc.poll() is None:proc.kill();proc.wait(3)
        proc.stdin.close();proc.stdout.close()
