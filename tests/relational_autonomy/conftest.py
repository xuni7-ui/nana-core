import socket
import pytest

@pytest.fixture(autouse=True)
def offline(monkeypatch):
 def denied(*a,**kw):raise AssertionError('NO_REAL_NETWORK')
 monkeypatch.setattr(socket.socket,'connect',denied)
 monkeypatch.setattr(socket,'create_connection',denied)
