"""Prepare one exact existing-account channel; no genesis/secret/Grant/network.

Run with the delivered SDK Python. Default is read-only plan. --apply is a
separate host-configuration write after the operator's real account/cutover
approval. Production activation is checked using the ORIGINAL canonical receipt.
"""

import argparse
import json
import re
from pathlib import Path

from nana_core.contracts import CoreError
from nana_core.life.config import load_config, update_config
from nana_core.life.control import request
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.platform_runtime import QQChannelBinding
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.life.platform_authority import CanonicalActivation, PlatformActivation
from nana_core.life.live_api.__main__ import read_private
from nana_core.life.live_api.canonical import verify_activation
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.life.live_api.contracts import ApiError, Realm


def _channel(args, common):
    if args.platform == "qq":
        if not args.endpoint or not args.credential_ref:
            raise CoreError("QQ_ENDPOINT_AND_REFERENCE_REQUIRED")
        from nana_core.life.platform_bridge import OneBotHTTPTransport

        OneBotHTTPTransport(args.endpoint, args.account_id, authorized=True, realm="AUTHENTICATED_PLATFORM")
        channel = QQChannelBinding(
            **common,
            endpoint=args.endpoint,
            account_id=args.account_id,
            sender_id=args.sender_id,
            target_id=args.target_id,
            target_kind=args.kind,
            privacy_class=args.privacy,
            credential_ref=args.credential_ref,
        )
        field = "qq_channels"
    else:
        if not args.cookie_ref or not args.csrf_ref or args.kind not in {"dm", "comment"}:
            raise CoreError("BILIBILI_KIND_AND_REFERENCES_REQUIRED")
        if args.privacy != ("PERSONAL" if args.kind == "dm" else "PUBLIC"):
            raise CoreError("BILIBILI_CHANNEL_PRIVACY_MISMATCH")
        channel = BilibiliChannelBinding(
            **common,
            account_id=int(args.account_id),
            sender_id=int(args.sender_id),
            target_id=int(args.target_id),
            kind=args.kind,
            cookie_ref=args.cookie_ref,
            csrf_ref=args.csrf_ref,
        )
        field = "bilibili_channels"
    return field, channel


def prepare(args):
    host = read_private(args.host_config)
    home = Path(host.home).absolute()
    identity, lineage, _ = existing_identity(home)
    if (identity, lineage) != (host.binding.subject_id, host.binding.lineage_binding):
        raise CoreError("PLATFORM_CANONICAL_IDENTITY_MISMATCH")
    if host.binding.realm == Realm.PRODUCTION:
        verify_activation(home, host.activation)
        canonical = CanonicalActivation.model_validate(host.activation)
    elif args.owned_development:
        canonical = None
    else:
        raise CoreError("OWNED_DEVELOPMENT_OPT_IN_REQUIRED")
    config = load_config(home)
    if config.revision != args.expected_revision:
        raise CoreError("LIFE_CONFIG_REVISION_CONFLICT")
    binding_id = args.platform + "." + args.channel
    platform = "qq.onebot" if args.platform == "qq" else "bilibili.account"
    original = next((b for b in config.surface_bindings if b.binding_id == binding_id), None)
    if original and (original.platform != platform or original.mode != "PLATFORM_ADAPTER_NO_SEND"):
        raise CoreError("EXISTING_SURFACE_BINDING_MISMATCH")
    binding = original or SurfaceBinding(
        binding_id=binding_id,
        platform=platform,
        surface="chat.direct",
        adapter=platform,
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=(args.privacy,),
    )
    if args.privacy not in binding.permitted_privacy:
        raise CoreError("SURFACE_PRIVACY_NOT_BOUND")
    activation = (
        PlatformActivation(
            canonical=canonical,
            binding_id=binding_id,
            account_id=args.account_id,
            exclusive_writer_confirmed=args.exclusive_writer_confirmed,
        )
        if canonical
        else None
    )
    common = {
        "channel_id": args.channel,
        "binding_id": binding_id,
        "enabled": args.enabled,
        "read_authorized": args.read_authorized,
        "send_authorized": args.send_authorized,
        "private_read_authorized": args.private_read_authorized,
        "activation": activation,
    }
    if args.send_authorized and not args.exclusive_writer_confirmed:
        raise CoreError("PLATFORM_EXCLUSIVE_WRITER_SCOPE_REQUIRED")
    field, channel = _channel(args, common)
    channels = tuple(c for c in getattr(config, field) if c.channel_id != args.channel) + (channel,)
    updated = config.model_copy(
        update={
            "revision": config.revision + 1,
            field: channels,
            "surface_bindings": config.surface_bindings if original else (*config.surface_bindings, binding),
        }
    )
    updated = type(config).model_validate_json(updated.model_dump_json())
    report = {
        "state": "HOST_CHANNEL_PLAN_NO_RUNTIME_EFFECT",
        "platform": args.platform,
        "channel_id": args.channel,
        "expected_revision": config.revision,
        "next_revision": updated.revision,
        "private_retention": False,
        "activation_configured": activation is not None,
        "grants_created": False,
        "network_calls": 0,
        "subject_created": False,
    }
    if args.apply:
        update_config(home, updated, expected_revision=config.revision)
        try:
            refreshed = request(home, {"operation": "platform-refresh"}, timeout=2).get("ok") is True
        except (OSError, CoreError):
            refreshed = False
        report.update(
            state="HOST_CHANNEL_SAVED_NOT_ACCOUNT_QUALIFIED",
            runtime_applied=refreshed,
            restart_required=not refreshed,
            credential_binding="SEPARATE_NATIVE_OR_EXPLICIT_HOST_VAULT",
        )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host-config", type=Path, required=True)
    p.add_argument("--platform", choices=("qq", "bilibili"), required=True)
    p.add_argument("--channel", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--sender-id", required=True)
    p.add_argument("--target-id", required=True)
    p.add_argument("--kind", choices=("private", "group", "dm", "comment"), required=True)
    p.add_argument("--privacy", choices=("PUBLIC", "PROJECT", "PERSONAL"), required=True)
    p.add_argument("--endpoint")
    p.add_argument("--credential-ref")
    p.add_argument("--cookie-ref")
    p.add_argument("--csrf-ref")
    p.add_argument("--expected-revision", type=int, required=True)
    for flag in (
        "read-authorized",
        "send-authorized",
        "private-read-authorized",
        "exclusive-writer-confirmed",
        "enabled",
        "apply",
        "owned-development",
    ):
        p.add_argument("--" + flag, action="store_true")
    args = p.parse_args()
    try:
        if not all(re.fullmatch(r"[0-9]{1,20}", v) for v in (args.account_id, args.sender_id, args.target_id)):
            raise CoreError("PLATFORM_NUMERIC_ACCOUNT_SCOPE_REQUIRED")
        print(json.dumps(prepare(args)), flush=True)
    except (ApiError, CoreError, OSError, ValueError, TypeError) as exc:
        code = exc.code if isinstance(exc, (CoreError, ApiError)) else "HOST_CHANNEL_CONFIGURATION_INVALID"
        print(json.dumps({"state": "BLOCKED", "code": code, "subject_created": False}), flush=True)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
