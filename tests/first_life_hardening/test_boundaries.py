import json,os,socket,subprocess,sys,time
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.life.durability import read_window
from nana_core.continuity.privacy import _load
from nana_core.continuity.hands.framing import receive_object


def test_special_storage_and_privacy_inputs_do_not_block(tmp_path):
    fifo=tmp_path/'state';os.mkfifo(fifo)
    for function,code in ((read_window,'STORAGE_MONITOR_INVALID'),(_load,'PRIVACY_ANCHOR_INVALID')):
        start=time.monotonic()
        with pytest.raises(CoreError,match=code):function(fifo)
        assert time.monotonic()-start<.5
    link=tmp_path/'link';link.symlink_to(fifo)
    with pytest.raises(CoreError):_load(link)
    with pytest.raises(CoreError):read_window(link)


@pytest.mark.parametrize('raw',[b'{"ok":true,"ok":false}\n',b'[]\n',b'{"ok":true}',b'{}\n{}\n',b'x'*80+b'\n'])
def test_untrusted_ipc_frames_reject_ambiguity(raw):
    a,b=socket.socketpair()
    try:
        b.sendall(raw);b.shutdown(socket.SHUT_WR)
        with pytest.raises(ValueError):receive_object(a,limit=64,seconds=.2)
    finally:a.close();b.close()


def test_total_deadline_is_not_per_receive(monkeypatch):
    import nana_core.continuity.hands.framing as module
    ticks=iter([0,.01,.09,.17,.25]);monkeypatch.setattr(module.time,'monotonic',lambda:next(ticks))
    class Dribbler:
        waits=[]
        def settimeout(self,t):self.waits.append(t)
        def recv(self,n):return b' '
    peer=Dribbler()
    with pytest.raises(TimeoutError):receive_object(peer,limit=64,seconds=.2)
    assert peer.waits==sorted(peer.waits,reverse=True) and len(peer.waits)==3


def test_owned_process_recovers_from_malformed_peer(tmp_path):
    from nana_core.continuity.hands.host import OwnedApplication
    from nana_core.continuity.hands.contracts import ApplicationTask
    from nana_core.continuity.hands.port import OwnedApplicationPort
    with OwnedApplication(tmp_path/'owned',tasks=(ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='approved'),)) as host:
        with socket.socket(socket.AF_UNIX) as s:
            s.settimeout(2);s.connect(str(Path(host.target.workspace)/'query.sock'))
            s.sendall(b'{"x":'+b'['*1500+b'0'+b']'*1500+b'}\n')
            assert json.loads(s.recv(4096))['ok'] is False
        port=OwnedApplicationPort('synthetic-subject',host.target,host_enabled=True)
        assert port.peek('doc')['state']['revision']==1


def test_seeded_finite_frame_roundtrips():
    import random
    rng=random.Random(20261021)
    for i in range(48):
        value={'request':i,'enabled':bool(rng.randrange(2)),'items':[rng.randrange(-99,99) for _ in range(rng.randrange(8))]}
        raw=json.dumps(value).encode()+b'\n';a,b=socket.socketpair()
        try:
            b.sendall(raw)
            assert receive_object(a,limit=512,seconds=.2)==value
        finally:a.close();b.close()
