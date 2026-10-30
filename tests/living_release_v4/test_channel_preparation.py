from argparse import Namespace
from pathlib import Path
from nana_core.life.config import load_config
from nana_core.life.live_api.__main__ import HostConfiguration
from nana_core.life.live_api.supervisor import existing_identity
from tests.first_life_android_v2.test_supervisor import owned
from tools.nana_living_release_v4.prepare_channels import prepare


def test_delivered_operator_channel_plan_is_readonly_and_apply_never_creates_subject(tmp_path):
    home, binding, release = owned(tmp_path)
    cfg = HostConfiguration(
        home=str(home),
        host_state=str(tmp_path / "host"),
        binding=binding,
        releases=(release,),
        active_release=release.release_id,
        public_origin="https://space.test",
        web_root=str(Path(__file__).resolve().parents[2] / "apps/nana-space/dist"),
    )
    host = tmp_path / "host.json"
    host.write_text(cfg.model_dump_json())
    host.chmod(0o600)
    before = load_config(home)
    identity = existing_identity(home)
    args = Namespace(
        host_config=host,
        platform="qq",
        channel="primary",
        account_id="42",
        sender_id="43",
        target_id="43",
        kind="private",
        privacy="PROJECT",
        endpoint="http://127.0.0.1:10042",
        credential_ref="qq.account",
        cookie_ref=None,
        csrf_ref=None,
        expected_revision=before.revision,
        read_authorized=True,
        send_authorized=False,
        private_read_authorized=False,
        exclusive_writer_confirmed=False,
        enabled=True,
        apply=False,
        owned_development=True,
    )
    plan = prepare(args)
    assert plan["state"] == "HOST_CHANNEL_PLAN_NO_RUNTIME_EFFECT" and load_config(home) == before
    args.apply = True
    result = prepare(args)
    assert result["state"] == "HOST_CHANNEL_SAVED_NOT_ACCOUNT_QUALIFIED" and result["restart_required"]
    assert load_config(home).qq_channels[0].enabled
    assert existing_identity(home) == identity and result["grants_created"] is False and result["network_calls"] == 0
