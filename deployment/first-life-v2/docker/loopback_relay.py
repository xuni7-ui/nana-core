"""Bounded infrastructure relay; original BFF remains loopback-only.

Production wiring is fixed: container TCP18766 -> loopback TCP18765. This
process owns no Subject, Store, credential, HTTP policy or semantic work.
"""
import select
import signal
import socket
import subprocess
import sys
import threading
import time

LISTEN = ("0.0.0.0", 18766)
UPSTREAM = ("127.0.0.1", 18765)
MAX_CONNECTIONS = 8
MAX_BUFFER = 65536
IDLE_SECONDS = 30
LIFETIME_SECONDS = 120


class FixedRelay:
    def __init__(self, listen=LISTEN, upstream=UPSTREAM):
        self.upstream = upstream
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.sockets = set()
        self.slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(listen)
        self.listener.listen(MAX_CONNECTIONS)
        self.listener.settimeout(.2)
        self.address = self.listener.getsockname()

    def _close(self, sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except (OSError, ValueError):
            pass
        sock.close()
        with self.lock:
            self.sockets.discard(sock)

    def _copy(self, client):
        upstream = None
        try:
            upstream = socket.create_connection(self.upstream, timeout=2)
            with self.lock:
                if self.stop.is_set():
                    upstream.close()
                    return
                self.sockets.add(upstream)
            peers = {client: upstream, upstream: client}
            buffers = {client: bytearray(), upstream: bytearray()}
            reading = {client: True, upstream: True}
            write_closed = set()
            for sock in peers:
                sock.setblocking(False)
            started = active = time.monotonic()
            while not self.stop.is_set() and (any(reading.values()) or any(buffers.values())):
                now = time.monotonic()
                if now - started >= LIFETIME_SECONDS or now - active >= IDLE_SECONDS:
                    return
                reads = [s for s in peers if reading[s] and len(buffers[peers[s]]) < MAX_BUFFER]
                writes = [s for s in peers if buffers[s]]
                ready_read, ready_write, errors = select.select(reads, writes, list(peers), .2)
                if errors:
                    return
                for sock in ready_read:
                    data = sock.recv(MAX_BUFFER - len(buffers[peers[sock]]))
                    if data:
                        buffers[peers[sock]].extend(data)
                        active = time.monotonic()
                    else:
                        reading[sock] = False
                for sock in ready_write:
                    sent = sock.send(buffers[sock])
                    if not sent:
                        return
                    del buffers[sock][:sent]
                    active = time.monotonic()
                for sock in peers:
                    if not reading[peers[sock]] and not buffers[sock] and sock not in write_closed:
                        sock.shutdown(socket.SHUT_WR)
                        write_closed.add(sock)
        except (OSError, ValueError):
            pass
        finally:
            if upstream is not None:
                self._close(upstream)
            self._close(client)
            self.slots.release()

    def serve(self):
        try:
            while not self.stop.is_set():
                try:
                    client, _ = self.listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not self.slots.acquire(blocking=False):
                    client.close()
                    continue
                with self.lock:
                    self.sockets.add(client)
                threading.Thread(target=self._copy, args=(client,), daemon=True).start()
        finally:
            self.stop.set()

    def close(self):
        self.stop.set()
        self.listener.close()
        with self.lock:
            sockets = list(self.sockets)
        for sock in sockets:
            self._close(sock)


def supervise(command):
    if not command:
        return 2
    relay = FixedRelay()
    worker = threading.Thread(target=relay.serve, daemon=True)
    child = None
    previous = {}
    try:
        child = subprocess.Popen(command)
        def stop(signum, frame):
            relay.close()
            if child.poll() is None:
                child.terminate()
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, stop)
        worker.start()
        while child.poll() is None and not relay.stop.wait(.1):
            pass
        if child.poll() is None:
            child.terminate()
        try:
            result = child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            result = child.wait(timeout=2)
        return result if result >= 0 else 128 - result
    finally:
        relay.close()
        if worker.ident is not None:
            worker.join(timeout=1)
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=2)
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(supervise(sys.argv[1:]))
