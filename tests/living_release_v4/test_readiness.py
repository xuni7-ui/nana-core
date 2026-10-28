import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.provider_config import ProviderProfile
from nana_core.continuity.provider_routing import RouteRequest, RoutingPolicy
from tests.provider_routing.helpers import fixture_router, model, update
from tests.world_loop.helpers import policy
from tests.first_life_android_v2.test_http_integration import running as running, http, login, base


def test_inspection_uses_same_policy_without_resolving_credentials(tmp_path):
    router, config, authority, _, ports = fixture_router(tmp_path)
    remote = ProviderProfile(
        provider_profile_id="remote.main", display_name="Remote", protocol="OPENAI_COMPATIBLE_CHAT",
        base_url="https://example.test/v1", secret_ref="remote.default", locality="REMOTE",
    )
    update(config, authority, "UPSERT_PROVIDER", provider=remote)
    update(config, authority, "UPSERT_MODEL", model=model("model.remote", "remote.main"))
    resolver = router.factory._RuntimeProviderFactory__resolver
    resolver.refs.add("remote.default")
    router.factory.policy = RoutingPolicy(allow_remote=True, allowed_remote_hosts=("example.test",))
    req = RouteRequest(operation="COGNITION", exact_provider_profile_id="remote.main", exact_model_profile_id="model.remote")
    snapshot = router.inspect(req, policy())
    assert snapshot.provider_profile_id == "remote.main" and snapshot.selection == "EXACT_MODEL"
    assert resolver.resolved == 0 and all(p.calls == 0 for p in ports)
    with pytest.raises(CoreError, match="PRIVACY_DENIED"):
        router.inspect(req.model_copy(update={"privacy_class": "SECRET"}), policy())
    update(config, authority, "DISABLE_PROVIDER", target_id="remote.main")
    with pytest.raises(CoreError, match="PROFILE_DISABLED"):
        router.inspect(req, policy())
    assert resolver.resolved == 0


def test_actual_bff_missing_provider_rejects_before_message_dispatch(running, monkeypatch):  # noqa: F811
    server, service = running
    headers = login(server, service)
    import nana_core.life.live_api.bridge as bridge
    original = bridge.core_request
    observed = []

    def track(home, command, **kwargs):
        observed.append(command["operation"])
        return original(home, command, **kwargs)

    monkeypatch.setattr(bridge, "core_request", track)
    row = http(server, "providers/status", headers=headers)[1]
    assert row["data"]["readiness"]["state"] == "PROVIDER_UNCONFIGURED"
    assert row["data"]["readiness"]["network_calls"] == 0
    request = {**base(service, "no-model"), "text": "PROJECT: test", "require_model": True}
    code, value, _ = http(server, "messages", "POST", request, headers)
    assert code == 200 and value["data"]["state"] == "REJECTED"
    assert value["data"]["error"] == "PROVIDER_UNCONFIGURED"
    assert value["data"]["dispatch_happened"] is False
    assert "surface" not in observed
    same = http(server, "messages", "POST", request, headers)[1]
    assert same["data"]["state"] == "REJECTED"
    assert observed.count("provider-readiness") == 1
    assert request["text"] not in service.ledger.document.path.read_text()


def test_budget_two_phase_check_uses_original_reservations(tmp_path):
    from types import SimpleNamespace
    from nana_core.life.readiness import budget
    from nana_core.life.application import LifeApplication
    from tests.first_life_android_v2.test_supervisor import owned
    from nana_core.life.config import load_config

    home, _, _ = owned(tmp_path)
    cfg = load_config(home).model_copy(update={"provider_total_calls_limit": 1,
         "provider_calls_per_hour": 2, "provider_calls_per_day": 2, "per_provider_calls_per_day": 2})
    with LifeApplication(home) as life:
        app = SimpleNamespace(config=cfg, runtime=life.runtime)
        snapshot = SimpleNamespace(provider_profile_id="provider.test")
        assert budget(app, snapshot, calls=1)["reserved_calls_total"] == 0
        with pytest.raises(CoreError, match="PROVIDER_TOTAL_CALL_BUDGET"):
            budget(app, snapshot, calls=2)
        assert not life.runtime.store.all("cognitive_requests")
