"""Focused deployment-tool safety checks; actual installation evidence is separate."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools/nana_first_life_unified_release"
sys.path.insert(0, str(TOOLS))
from propose_config import proposal
from stage import metadata


def test_proposal_preserves_binding_and_authority_and_is_explicit_about_capability():
    original = {
        "home": "/opt/nana-core/data/canonical",
        "host_state": "/opt/nana-core/data/host/state",
        "binding": {"subject_id": "unchanged", "lineage_binding": "a" * 64, "realm": "PRODUCTION"},
        "activation": {"approval_digest": "b" * 64},
        "roles": ["READER"],
        "public_origin": "https://example.tailnet.ts.net:8443",
        "active_release": "installed",
        "releases": [{"release_id": "installed", "source_commit": "0" * 40}],
    }
    release = {"core_source": "c" * 40, "web_sha256": "d" * 64, "core_integrity_sha256": "e" * 64}
    result = proposal(original, release)
    for name in ("home", "host_state", "binding", "activation", "roles", "public_origin", "active_release"):
        assert result[name] == original[name]
    assert "allow_provider_configuration" not in result
    assert proposal(original, release, provider_settings=True)["allow_provider_configuration"] is True
    assert result["releases"][0]["python"].endswith("/" + "c" * 40 + "/.venv/bin/python")
    assert original["releases"][0]["source_commit"] == "0" * 40


def test_version_pin_and_duplicate_alias_fail_closed(tmp_path):
    (tmp_path / "release.json").write_text(json.dumps({"image_id": "latest", "core_source": "a" * 40}))
    with pytest.raises(ValueError, match="PINNED_RELEASE"):
        metadata(tmp_path)
    with pytest.raises(ValueError, match="EXISTING_ACTIVE_RELEASE"):
        proposal({"active_release": "installed", "releases": []}, {"core_source": "a" * 40})


def test_runtime_installer_defaults_stay_bound_to_original_seal(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "runtime_installer", TOOLS.parent / "nana_first_life_android_v2/install_runtime_tree.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.IMAGE == "sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee"
    with pytest.raises(ValueError, match="PINNED_IMAGE_REQUIRED"):
        module.manifest(tmp_path / "absent.tar", image_id="latest")
