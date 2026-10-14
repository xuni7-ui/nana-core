import socket

import pytest

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.contracts import EvidenceInput, Provenance
from nana_core.continuity.memory import MemoryService


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("continuous-self tests must not use network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def cognitive(tmp_path):
    authority = OperatorAuthority()
    with ContinuityStore(tmp_path / "self.db", ManualClock()) as store:
        IdentityService(store, authority)
        memory = MemoryService(store)
        memory.entity("synthetic-sister", "PERSON")
        yield store, memory, authority


def evidence(memory, key, text, *, when=100, kind="USER_STATEMENT", privacy="PERSONAL"):
    return memory.capture(EvidenceInput(provenance=Provenance(
        source_namespace="synthetic.continuity", source_reference=key, source_kind=kind),
        text=text, event_time_us=when, observed_time_us=when + 1, privacy_class=privacy))
