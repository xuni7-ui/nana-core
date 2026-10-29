import pytest

from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.platform_authority import CanonicalActivation, PlatformActivation, require_platform_authority
from nana_core.life.live_api.contracts import ApiError
from tests.first_life_android_v2.test_supervisor import owned


def test_arbitrary_host_boolean_or_dict_does_not_authorize_a_platform():
    for value in (True, {"approved": True}, {"exclusive_writer_confirmed": True}):
        with pytest.raises(CoreError, match="PLATFORM_CANONICAL_ACTIVATION_REQUIRED"):
            require_platform_authority(None, value, channel="qq", exclusive_writer=True)


def test_development_subject_cannot_gain_real_platform_authority_from_typed_descriptor(tmp_path):
    home, binding, _ = owned(tmp_path)
    canonical = CanonicalActivation(subject_id=binding.subject_id, lineage_binding=binding.lineage_binding,
        old_writer_fence_digest="a"*64, approval_digest="b"*64, genesis_receipt_digest="c"*64,
        realm="PRODUCTION_SINGLE_SUBJECT")
    with LifeApplication(home) as app:
        activation = PlatformActivation(canonical=canonical, binding_id="qq.fixture", account_id="42", exclusive_writer_confirmed=True)
        with pytest.raises(ApiError, match="DEVELOPMENT_SUBJECT_CANNOT_BECOME_PRODUCTION"):
            require_platform_authority(app, activation, channel="qq", exclusive_writer=True, account_id="42")
        assert not app.runtime.store.all("grants") and not app.runtime.store.all("actions")
    assert not (home / "activation").exists()
