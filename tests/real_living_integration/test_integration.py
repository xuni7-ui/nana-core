"""Synthetic-only data through actual original Core/BFF, never formal genesis."""

import hashlib
import json
import sqlite3
import pytest
from nana_core.integration.exporter import bundle
from nana_core.life.live_api.contracts import ApiError
from nana_core.life.live_api.adapters import reconcile_legacy
from tests.first_life_android_v2.test_http_integration import running, http, login, base
from tests.first_life_android_v2.test_supervisor import owned
from tools.nana_first_life_android_v2.living_preflight import inspect_existing
from tools.nana_first_life_android_v2.legacy_plan import prepare, read_explicit
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.storage import digest


def config_body(service, key, revision=0):
    return {
        **base(service, key),
        "command": {
            "operation": "UPSERT_PROVIDER",
            "expected_revision": revision,
            "provider": {
                "provider_profile_id": "fixture.live",
                "display_name": "TEST_ONLY_LOCAL",
                "protocol": "LOCAL",
                "locality": "LOCAL_FIXTURE",
            },
        },
    }


def test_real_http_host_opt_in_cas_no_network_no_subject_events(running):
    server, service = running
    headers = login(server, service)
    body = config_body(service, "provider-1")
    assert http(server, "providers/commands", "POST", body, headers)[0] == 403
    service.allow_provider_configuration = True
    before = existing_identity(service.supervisor.home)
    code, response, _ = http(server, "providers/commands", "POST", body, headers)
    assert code == 200 and response["data"]["state"] == "VERIFIED", response
    assert response["data"]["result"]["network_calls"] == 0
    assert http(server, "providers/commands", "POST", body, headers)[1]["data"]["receipt_id"] == "provider-1"
    stale = config_body(service, "provider-2")
    response = http(server, "providers/commands", "POST", stale, headers)[1]
    assert response["data"]["state"] == "REJECTED" and not response["data"]["dispatch_happened"]
    assert existing_identity(service.supervisor.home) == before
    assert http(server, "views/settings", headers=headers)[1]["data"]["provider_settings"]["revision"] == 1
    missing = {k: v for k, v in headers.items() if k != "X-Nana-CSRF"}
    assert http(server, "providers/commands", "POST", config_body(service, "no-csrf", 1), missing)[0] == 403
    bad = config_body(service, "no-key", 1)
    bad["command"]["provider"]["api_key"] = "TEST_ONLY_NOT_SECRET"
    assert http(server, "providers/commands", "POST", bad, headers)[0] == 400
    text = (service.supervisor.home / "providers.json").read_text()
    assert "TEST_ONLY_NOT_SECRET" not in text


def test_provider_reader_not_configuration_authority(running):
    server, service = running
    service.allow_provider_configuration = True
    from nana_core.life.live_api.auth import Principal
    from nana_core.life.live_api.contracts import Role
    from nana_core.life.live_api.provider_settings import ProviderConfigurationRequest, configure

    reader = Principal("read", (Role.READER, Role.CONVERSATION), "CONNECTOR", None, service.auth.generation)
    with pytest.raises(ApiError):
        configure(service, reader, ProviderConfigurationRequest(**config_body(service, "reader")))


def test_existing_home_preflight_never_genesis(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(ApiError):
        inspect_existing(missing, subject_id="none", lineage_binding="a" * 64)
    assert not missing.exists()
    home, binding, release = owned(tmp_path)
    before = hashlib.sha256((home / "subject/self.db").read_bytes()).hexdigest()
    report = inspect_existing(home, subject_id=binding.subject_id, lineage_binding=binding.lineage_binding)
    assert report["state"] == "OFFLINE_PASS_EXISTING_HOME_ONLY" and not report["first_life_ready"]
    assert report["real_provider_pass"] == "NOT_RUN" and not report["new_subject_created"]
    assert hashlib.sha256((home / "subject/self.db").read_bytes()).hexdigest() == before
    with pytest.raises(ValueError):
        inspect_existing(home, subject_id="wrong", lineage_binding=binding.lineage_binding)


def test_hash_plan_is_repeatable_bound_not_import_and_cross_source_ids(tmp_path):
    from nana_core.life.live_api.contracts import Binding

    b = bundle(
        [("l1", "one", {"content": "SYNTHETIC PUBLIC PROJECT", "timestamp": "2026-10-26T00:00:00Z"})], "fixture.a"
    )
    binding = Binding(subject_id="existing-only", lineage_binding="a" * 64)
    first = prepare([b, b], binding)
    assert first == prepare([b, b], binding)
    assert first["reconciliation"]["duplicate_rows"] == 1
    assert not first["private_import_authorized"] and not first["live_experience_created"]
    other = json.loads(json.dumps(b))
    other["source_identity"] = "fixture.b"
    other["records"][0]["source_identity"] = "fixture.b"
    # Aggregator must namespace even when an independent exporter reuses a key.
    other["manifest_hash"] = digest({k: v for k, v in other.items() if k != "manifest_hash"})
    assert reconcile_legacy([b, other])["unique_records"] == 2
    bad = json.loads(json.dumps(b))
    bad["records"][0]["payload_hash"] = "f" * 64
    bad["manifest_hash"] = digest({k: v for k, v in bad.items() if k != "manifest_hash"})
    assert prepare([b, bad], binding)["reconciliation"]["state"] == "CONFLICT_REVIEW_REQUIRED"
    with pytest.raises(ApiError):
        prepare([bundle([("l1", "x", {"content": "SYNTHETIC"})], "fixture", mode="include")], binding)
    file = tmp_path / "bundle.json"
    file.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError):
        read_explicit(file)


def test_backup_projection_is_authenticated_and_never_promotes_local_to_dr(running):
    server, service = running
    assert http(server, "backup/status")[0] == 401
    headers = login(server, service)
    response = http(server, "backup/status", headers=headers)[1]
    assert response["data"]["offsite_state"] == "STATUS_NOT_EXPOSED"
    assert response["data"]["local_receipts"] == [] and not response["data"]["runnable_clone"]
    assert "backup_status" in response["capabilities"]
