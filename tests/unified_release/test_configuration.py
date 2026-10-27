from tests.first_life_android_v2.test_http_integration import running as running, http, login, base
from nana_core.life.live_api.provider_settings import projection


def test_missing_config_read_is_explicit_empty_and_never_creates_file(tmp_path):
    report = projection(tmp_path)
    assert report["revision"] == 0 and report["configured"] is False
    assert report["providers"] == [] and not (tmp_path / "providers.json").exists()


def test_new_v3_commands_real_http_revision_roles_and_receipts(running):  # noqa: F811 - pytest fixture injection
    server, service = running
    headers = login(server, service)
    service.allow_provider_configuration = True

    def send(key, command):
        return http(server, "providers/commands", "POST", {**base(service, key), "command": command}, headers)[1][
            "data"
        ]

    p = {
        "provider_profile_id": "provider.v3",
        "display_name": "SYNTHETIC_DECLARED_ONLY",
        "protocol": "OPENAI_COMPATIBLE_CHAT",
        "base_url": "https://provider.example/v1",
        "locality": "REMOTE",
        "permitted_privacy": ["PUBLIC", "PROJECT"],
    }
    row = send("v3-p", {"operation": "UPSERT_PROVIDER", "expected_revision": 0, "provider": p})
    assert row["state"] == "VERIFIED" and row["result"]["configuration_revision"] == 1
    model = {
        "model_profile_id": "model.v3",
        "provider_profile_id": "provider.v3",
        "remote_model_id": "same.model",
        "model_version": "user-configured",
        "operations": ["COGNITION"],
        "input_modalities": ["TEXT"],
        "output_modalities": ["TEXT"],
        "context_limit": 8192,
        "output_limit": 1024,
    }
    row = send("v3-m", {"operation": "UPSERT_MODEL", "expected_revision": 1, "model": model})
    assert row["state"] == "VERIFIED" and row["result"]["configuration_revision"] == 2
    row = send(
        "v3-r",
        {
            "operation": "SET_CAPABILITY_ROUTE",
            "expected_revision": 2,
            "route": {
                "operation": "COGNITION",
                "primary_model_profile_id": "model.v3",
                "permitted_privacy": ["PUBLIC", "PROJECT"],
            },
        },
    )
    assert row["state"] == "VERIFIED" and not row["result"]["live_permission_granted"]
    stale = send("v3-conflict", {"operation": "DISABLE_PROVIDER", "expected_revision": 2, "target_id": "provider.v3"})
    assert (
        stale["state"] == "REJECTED"
        and stale["error"] == "PROVIDER_CONFIG_REVISION_CONFLICT"
        and not stale["dispatch_happened"]
    )
    assert http(server, "receipts/v3-conflict", headers=headers)[1]["data"]["state"] == "REJECTED"
    view = http(server, "views/settings", headers=headers)[1]["data"]["provider_settings"]
    assert view["revision"] == 3 and "secret_ref" not in str(view)
    assert http(server, "backup/status", headers=headers)[1]["data"]["pc_delivery"] == "NOT_OBSERVED"
