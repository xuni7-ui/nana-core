from nana_core.life.config import load_config, update_config
from nana_core.life.platform_runtime import QQChannelBinding
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.control import request
from tests.first_life_android_v2.test_http_integration import running, http, login, base


def test_actual_supervisor_platform_fd_does_not_enable_model_calls(tmp_path):
    from tests.first_life_android_v2.test_supervisor import owned, cleanup
    from nana_core.life.live_api.supervisor import Supervisor
    from nana_core.life.secret_binding import MemorySecretResolver

    home, binding, release = owned(tmp_path)
    config = load_config(home)
    update_config(
        home,
        config.model_copy(
            update={
                "revision": config.revision + 1,
                "provider_hosts": ("provider.example",),
                "remote_privacy": ("PROJECT",),
                "provider_cost_ceiling_micro": 1,
            }
        ),
        expected_revision=config.revision,
    )
    resolver = MemorySecretResolver()
    resolver.bind("platform.events", "TEST_ONLY_NOT_SECRET_PLATFORM_KEY")
    owner = Supervisor(
        home,
        tmp_path / "host-platform",
        binding,
        [release],
        active_release=release.release_id,
        provider_binding=resolver.inherited_fd,
        provider_live_authorized=False,
    )
    try:
        owner.start()
        result = request(home, {"operation": "view", "view": "status"})
        assert result["ok"] and result["result"]["provider"] == "OFFLINE_NO_PROVIDER"
    finally:
        cleanup(owner)
        resolver.clear()


def test_actual_owner_config_cas_and_phone_switch_never_mints_grant(running):
    server, service = running
    headers = login(server, service)
    service.allow_provider_configuration = True
    home = service.supervisor.home
    cfg = load_config(home)
    binding = SurfaceBinding(
        binding_id="qq.primary",
        platform="qq.onebot",
        surface="chat.direct",
        adapter="qq.onebot",
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=("PROJECT",),
    )
    channel = QQChannelBinding(
        channel_id="primary",
        binding_id=binding.binding_id,
        endpoint="http://127.0.0.1:10042",
        account_id="42",
        target_id="43",
        sender_id="43",
        read_authorized=True,
    )
    updated = cfg.model_copy(
        update={
            "revision": cfg.revision + 1,
            "surface_bindings": (*cfg.surface_bindings, binding),
            "qq_channels": (channel,),
        }
    )
    update_config(home, updated, expected_revision=cfg.revision)
    assert request(home, {"operation": "platform-refresh"})["ok"]
    code, value, _ = http(server, "platform/status", headers=headers)
    assert code == 200 and value["data"]["channels"][0]["state"] == "NOT_OBSERVED"
    assert not value["data"]["channels"][0]["enabled"]
    body = {
        **base(service, "platform-switch"),
        "platform": "qq",
        "channel_id": "primary",
        "enabled": True,
        "configuration_revision": updated.revision,
    }
    status, result, _ = http(server, "platform/commands", "POST", body, headers)
    assert status == 200 and result["data"]["state"] == "VERIFIED", result
    assert result["data"]["result"]["runtime_applied"] and not result["data"]["result"]["grants_created"]
    assert load_config(home).qq_channels[0].enabled
    assert request(home, {"operation": "platform-status"})["result"]["channels"][0]["enabled"]
    before = load_config(home).revision
    duplicate = http(server, "platform/commands", "POST", body, headers)[1]
    assert duplicate["data"]["receipt_id"] == result["data"]["receipt_id"] and load_config(home).revision == before
    stale = {**body, **base(service, "platform-stale")}
    rejected = http(server, "platform/commands", "POST", stale, headers)[1]["data"]
    assert rejected["state"] == "REJECTED" and rejected["error"] == "PLATFORM_CONFIG_REVISION_CONFLICT"
    denied = {**body, **base(service, "platform-csrf"), "configuration_revision": before, "enabled": False}
    assert (
        http(server, "platform/commands", "POST", denied, {k: v for k, v in headers.items() if k != "X-Nana-CSRF"})[0]
        == 403
    )
