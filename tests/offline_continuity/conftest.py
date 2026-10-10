import socket
import pytest
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import GrantSpec
from nana_core.fake_world import CAPABILITIES, VERIFY_CAPABILITY, FakeWorld
from nana_core.storage import Store, digest

SOURCE = "source://synthetic/garden"
CARD = "notebook://synthetic/card-1"
PARAGRAPHS = [{"text": "A quiet fictional garden grows beside a stream.", "locator": "page 7, paragraph 2"}]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline test attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def environment(tmp_path):
    clock = ManualClock()
    store = Store(tmp_path / "nana.db", clock)
    world = FakeWorld(tmp_path / "fake_world.db")
    world.seed_source(SOURCE, PARAGRAPHS)
    authority = OperatorAuthority()
    kernel = ActionKernel(store, world, authority)
    kernel.set_budgets({"write_attempts": 10, "external_requests": 100, "cost_micro_units": 100}, authority)
    yield store, world, kernel, authority, clock
    world.close()
    store.close()


def authorize(kernel, authority, clock, resources=(SOURCE, CARD), capabilities=None, ttl=10_000_000):
    return kernel.grant(GrantSpec(capabilities=tuple(sorted(capabilities or CAPABILITIES | {VERIFY_CAPABILITY})),
        resources=tuple(resources), not_before_us=clock.utc_now_us(), expires_at_us=clock.utc_now_us() + ttl), authority)


def card_args(content="Synthetic reading card", locator=None):
    return {"source_id": SOURCE, "source_digest": digest(PARAGRAPHS[0]["text"].encode()),
            "content": content, "locator": locator}
