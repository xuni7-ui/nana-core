"""Owned loopback infrastructure only: no Core/Subject/Docker/real credential."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import select
import socket
import socketserver
import subprocess
import sys
import tarfile
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / 'deployment/first-life-v2/docker'


def load(name):
    spec = importlib.util.spec_from_file_location('owned_' + name, DOCKER / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ThreadedServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@pytest.fixture
def relayed():
    resources = []
    def start(handler, module=None):
        module = module or load('loopback_relay')
        server = ThreadedServer(('127.0.0.1', 0), handler)
        server_thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        server_thread.start()
        relay = module.FixedRelay(listen=('127.0.0.1', 0), upstream=server.server_address)
        relay_thread = threading.Thread(target=relay.serve, daemon=True)
        relay_thread.start()
        resources.append((relay, relay_thread, server, server_thread))
        return relay, server
    yield start
    for relay, relay_thread, server, server_thread in resources:
        relay.close()
        relay_thread.join(timeout=2)
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def test_relay_preserves_http_host_origin_and_auth_bytes(relayed):
    seen = []
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            raw = bytearray()
            while b'\r\n\r\n' not in raw:
                raw.extend(self.request.recv(4096))
            seen.append(bytes(raw))
            self.request.sendall(b'HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
    relay, server = relayed(Handler)
    request = (b'GET /api/nana-space/v2/bootstrap HTTP/1.1\r\nHost: space.test\r\n'
               b'Origin: https://space.test\r\nCookie: TEST_ONLY_NOT_SECRET_cookie\r\n\r\n')
    with socket.create_connection(relay.address, timeout=2) as client:
        client.sendall(request)
        assert client.recv(4096).startswith(b'HTTP/1.1 401 ')
    assert seen == [request]


def test_bounded_relay_preserves_large_stream_and_half_close(relayed):
    payload = bytes(range(256)) * 1024
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(3)
            received = bytearray()
            while chunk := self.request.recv(8192):
                received.extend(chunk)
            self.request.sendall(bytes(received)[::-1])
    relay, _ = relayed(Handler)
    with socket.create_connection(relay.address, timeout=3) as client:
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        received = bytearray()
        while chunk := client.recv(8192):
            received.extend(chunk)
    assert bytes(received) == payload[::-1]


def test_connection_limit_closes_excess_without_opening_upstream(relayed, monkeypatch):
    module = load('loopback_relay')
    monkeypatch.setattr(module, 'MAX_CONNECTIONS', 1)
    accepted = threading.Event()
    count = []
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            count.append(1)
            accepted.set()
            self.request.settimeout(2)
            try:
                self.request.recv(1)
            except OSError:
                pass
    relay, _ = relayed(Handler, module)
    with socket.create_connection(relay.address, timeout=2):
        assert accepted.wait(2)
        with socket.create_connection(relay.address, timeout=2) as excess:
            try:
                data = excess.recv(1)
            except ConnectionResetError:
                data = b''
            assert data == b''
        assert len(count) == 1
        relay.close()
        assert not relay.sockets


def test_supervisor_propagates_child_exit_and_cleans_listener(monkeypatch):
    module = load('loopback_relay')
    cls = module.FixedRelay
    relay = cls(listen=('127.0.0.1', 0))
    monkeypatch.setattr(module, 'FixedRelay', lambda: relay)
    assert module.supervise([sys.executable, '-I', '-c', 'raise SystemExit(7)']) == 7
    assert relay.stop.is_set() and relay.listener.fileno() == -1


def test_supervisor_sigterm_terminates_its_owned_child(tmp_path):
    # This owned child is a sleeping stdlib fixture, never a Core runtime.
    script = tmp_path / 'relay_supervisor.py'
    script.write_text(f'''import importlib.util,sys
s=importlib.util.spec_from_file_location('relay',{str(DOCKER / 'loopback_relay.py')!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cls=m.FixedRelay;m.FixedRelay=lambda:cls(listen=('127.0.0.1',0))
raise SystemExit(m.supervise([sys.executable,'-I','-u','-c',"import os,time;print(os.getpid(),flush=True);time.sleep(60)"]))
''')
    process = subprocess.Popen([sys.executable, '-I', str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    child_pid = None
    try:
        assert select.select([process.stdout], [], [], 5)[0]
        child_pid = int(process.stdout.readline())
        process.terminate()
        process.communicate(timeout=5)
        assert process.returncode == 143
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=3)


@pytest.mark.parametrize('operation,tty,allowed', [
    (['serve'], False, True), (['serve', '--password-fd', '0'], False, True),
    (['serve', '--password-fd', '0'], True, False), (['serve', '--password-fd', '3'], False, False)])
def test_entry_only_forwards_explicit_non_tty_stdin_password(tmp_path, monkeypatch, operation, tty, allowed):
    entry = load('container_entry')
    runtime = tmp_path / 'runtime'
    release = runtime / 'core-releases/pinned'
    release.mkdir(parents=True)
    data = tmp_path / 'data'
    (data / 'host').mkdir(parents=True)
    (data / 'host/host.json').write_text('{}')
    monkeypatch.setattr(entry, 'RUNTIME', runtime)
    monkeypatch.setattr(entry, 'DATA', data)
    monkeypatch.setattr(entry, 'verify', lambda: {'state': 'PRIVATE_RUNTIME_COMPATIBLE'})
    monkeypatch.setattr(entry.os, 'geteuid', lambda: 999)
    monkeypatch.setattr(entry.os, 'isatty', lambda fd: tty)
    monkeypatch.setenv('NANA_CORE_RELEASE', str(release))
    monkeypatch.setattr(entry.sys, 'argv', ['container_entry.py', *operation])
    execs = []
    monkeypatch.setattr(entry.os, 'execv', lambda executable, argv: execs.append((executable, argv)))
    result = entry.main()
    assert bool(execs) == allowed
    if allowed:
        command = execs[0][1]
        assert command[:4] == [sys.executable, '-I', '-B', str(DOCKER / 'loopback_relay.py')]
        assert command[4:9] == [str(release / '.venv/bin/python'), '-I', '-B', str(release / 'host_gateway.py'), '--config']
        assert ('--password-fd' in command) == ('--password-fd' in operation)
        if '--password-fd' in command:
            assert command[-2:] == ['--password-fd', '0']
    else:
        assert result == 2


def test_extractor_explicit_sdk_modes_survive_private_umask(tmp_path):
    archive = tmp_path / 'runtime.tgz'
    with tarfile.open(archive, 'w:gz') as tar:
        for path, mode in [('runtime/bin/python3.12', 0o755), ('runtime/lib/public.py', 0o644)]:
            member = tarfile.TarInfo(path)
            member.mode, member.size = mode, len(b'PUBLIC_SYNTHETIC_RUNTIME')
            member.mtime = 1700000000
            tar.addfile(member, io.BytesIO(b'PUBLIC_SYNTHETIC_RUNTIME'))
    target = tmp_path / 'new-target'
    target.mkdir()
    private = tmp_path / 'private-data'
    private.mkdir(mode=0o700)
    previous = os.umask(0o077)
    try:
        (target / 'runtime').mkdir()
        load('extract_runtime').extract(archive, hashlib.sha256(archive.read_bytes()).hexdigest(), target)
    finally:
        os.umask(previous)
    assert (target / 'runtime').stat().st_mode & 0o777 == 0o755
    assert (target / 'runtime/bin').stat().st_mode & 0o777 == 0o755
    assert (target / 'runtime/bin/python3.12').stat().st_mode & 0o777 == 0o755
    assert (target / 'runtime/lib/public.py').stat().st_mode & 0o777 == 0o644
    assert (target / 'runtime/lib/public.py').stat().st_mtime == 1700000000
    assert private.stat().st_mode & 0o777 == 0o700


def test_compose_relay_mapping_keeps_host_listener_private():
    compose = (DOCKER / 'compose.yaml').read_text()
    assert "127.0.0.1:18765:18766" in compose and 'network_mode: host' not in compose
    module = load('loopback_relay')
    assert module.LISTEN == ('0.0.0.0', 18766) and module.UPSTREAM == ('127.0.0.1', 18765)
