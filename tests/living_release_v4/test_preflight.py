from types import SimpleNamespace

from nana_core.life.live_api.contracts import Role
from nana_core.life.live_api.preflight import check
from tests.first_life_android_v2.test_supervisor import owned


def test_preflight_reads_existing_subject_without_creating_authority(tmp_path):
    home, binding, _ = owned(tmp_path)
    before = {p.relative_to(home): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    result = check(SimpleNamespace(home=home, binding=binding,
                                   roles=(Role.CONVERSATION,)))
    assert result["state"] == "READ_ONLY_BINDING_CHECKED"
    assert result["subject_id"] == binding.subject_id
    assert result["schema_version"] == 13 and not result["foreign_key_violation"]
    assert result["provider"] == "PROVIDER_UNCONFIGURED"
    assert result["management_entry"] == "NOT_CONFIGURED_NO_ROLE_ESCALATION"
    assert result["runtime_visibility"] == "UNVERIFIED_IN_THIS_CONTEXT"
    assert result["persistent_changes"] == result["provider_calls"] == 0
    after = {p.relative_to(home): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before
