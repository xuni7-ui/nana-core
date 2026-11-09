"""Only new rev3 operator tools; no production, old-service or Provider access."""

import hashlib
import io
import json
import sqlite3
import socket
import subprocess
import tarfile
from pathlib import Path

import pytest

from tools.nana_first_life_android_v2 import b1_backup, install_runtime_tree, plan_binding

ROOT = Path(__file__).resolve().parents[2]


def test_plan_file_hash_and_original_core_dto_hash_are_distinct(tmp_path):
    original = ROOT / "deployment/first-life-v2/canonical-plan.json"
    result = plan_binding.binding(original)
    assert result["plan_file_sha256"] == "41c343bc4423606a48a52da5fa10c8ccb1a6d31af5931d56ebbe9c5771567304"
    assert result["plan_dto_sha256"] == "e3e2a1fd51b9473d7982980aa1f3d78a498a2f7878e7ae5c3051451a8b5d1527"
    reformatted = tmp_path / "plan.json"
    reformatted.write_text(json.dumps(json.loads(original.read_text()), indent=4))
    other = plan_binding.binding(reformatted)
    assert result["plan_file_sha256"] != other["plan_file_sha256"]
    assert result["plan_dto_sha256"] == other["plan_dto_sha256"]
    assert result["approved"] is result["subject_created"] is False


@pytest.mark.parametrize("name,target", [("../escape", None), ("/absolute", None), ("bin/python3", "/etc/passwd")])
def test_runtime_tree_rejects_path_and_virtual_link_escape(tmp_path, name, target):
    path = tmp_path / "tree.tar"
    with tarfile.open(path, "w") as t:
        m = tarfile.TarInfo(name)
        if target:
            m.type, m.linkname = tarfile.SYMTYPE, target
        t.addfile(m, None if target else io.BytesIO(b""))
    with pytest.raises(ValueError):
        install_runtime_tree.manifest(path)


def fixture_bundle(root):
    identity = "TEST_ONLY_NOT_SECRET_SYNTHETIC_B1_IDENTITY"
    db = root / "snapshot.db"
    with sqlite3.connect(db) as c:
        c.execute("create table core_meta(key text,value_json text)")
        c.execute("insert into core_meta values('recovery_quarantine','true')")
        c.execute("create table identities(identity_id text)")
        c.execute("insert into identities values(?)", (identity,))
    (root / "privacy-intents.json").write_text(json.dumps({"identity_id": identity, "intents": []}))
    (root / "snapshot.db.privacy.json").write_text(
        json.dumps({"anchor_path": "/TEST_ONLY_NOT_SECRET/deletion-intents.json"})
    )
    names = ("snapshot.db", "privacy-intents.json", "snapshot.db.privacy.json")
    manifest = {
        "kind": "ORIGINAL_CORE_QUARANTINED_BACKUP",
        "identity_sha256": hashlib.sha256(identity.encode()).hexdigest(),
        "evidence_scope": "SYNTHETIC_CRYPTO_FIXTURE_NOT_REAL_SUBJECT_OR_PC",
        "files": {n: b1_backup.sha(root / n) for n in names},
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    bundle = root / "backup.tar"
    with tarfile.open(bundle, "w") as t:
        for n in (*names, "manifest.json"):
            t.add(root / n, arcname=n)
    return bundle


def test_public_key_backup_packet_check_accepts_aead_but_rejects_symmetric_session():
    assert b1_backup._public_key_encrypted_packet_listing(
        b":pubkey enc packet:\n:encrypted data packet:\n"
    )
    assert b1_backup._public_key_encrypted_packet_listing(
        b":pubkey enc packet:\n:aead encrypted packet: cipher=9 aead=2\n"
    )
    assert not b1_backup._public_key_encrypted_packet_listing(
        b":pubkey enc packet:\n:symkey enc packet:\n:aead encrypted packet:\n"
    )
    assert not b1_backup._public_key_encrypted_packet_listing(b":pubkey enc packet:\n")


def test_b1_actual_openpgp_roundtrip_and_pc_receive_are_not_real_dr(tmp_path, monkeypatch):
    home = tmp_path / "pc-private-keyring"
    home.mkdir(mode=0o700)
    gpg = ["gpg", "--no-options", "--homedir", str(home), "--batch", "--no-tty"]
    try:
        subprocess.run(
            [
                *gpg,
                "--pinentry-mode",
                "loopback",
                "--passphrase",
                "",
                "--quick-generate-key",
                "TEST_ONLY_NOT_SECRET_B1",
                "future-default",
                "default",
                "0",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        metadata = subprocess.check_output([*gpg, "--with-colons", "--list-keys"], stderr=subprocess.DEVNULL, text=True)
        fingerprint = next(line.split(":")[9] for line in metadata.splitlines() if line.startswith("fpr:"))
        public = tmp_path / "pc-public.gpg"
        public.write_bytes(subprocess.check_output([*gpg, "--export", fingerprint]))
        bundle = fixture_bundle(tmp_path)
        encrypted = tmp_path / "encrypted.gpg"
        with pytest.raises(ValueError, match="PC_PUBLIC_KEY_IDENTITY_MISMATCH"):
            b1_backup.encrypt(bundle, b1_backup.sha(bundle), public, "0" * 40, encrypted)
        receipt = b1_backup.encrypt(bundle, b1_backup.sha(bundle), public, fingerprint, encrypted)
        assert receipt["state"] == "ENCRYPTED_LOCALLY_NOT_OFFSITE" and not receipt["b1_real_pc_qualified"]
        restored = tmp_path / "restored.tar"
        with restored.open("wb") as out:
            subprocess.run(
                [*gpg, "--decrypt", str(encrypted)], stdout=out, stderr=subprocess.DEVNULL, check=True, timeout=10
            )
        assert restored.read_bytes() == bundle.read_bytes()
        review = b1_backup.validate_bundle(restored, b1_backup.sha(bundle))
        assert not review["active_restore"] and not review["b1_real_pc_qualified"]
        pc = tmp_path / "synthetic-pc-directory"
        pc.mkdir(mode=0o700)
        header = {"sha256": b1_backup.sha(encrypted), "bytes": encrypted.stat().st_size}
        stream = io.BytesIO((json.dumps(header) + "\n").encode() + encrypted.read_bytes())
        response = io.BytesIO()
        b1_backup.receive(pc, stream, response)
        assert json.loads(response.getvalue())["state"] == "RECEIVED_ENCRYPTED_ONLY"
        assert not json.loads(response.getvalue())["restored"]
        assert (pc / (header["sha256"] + ".gpg")).read_bytes() == encrypted.read_bytes()
        # Actual ciphertext, explicit local socket handles, simulated offline
        # SSH ONLY: never a real PC connection or offsite qualification.
        agent = socket.socket(socket.AF_UNIX)
        tail = socket.socket(socket.AF_UNIX)
        agent_path, tail_path = tmp_path / "agent.sock", tmp_path / "tailscaled.sock"
        agent.bind(str(agent_path))
        tail.bind(str(tail_path))
        known = tmp_path / "known-hosts"
        known.write_text("TEST_ONLY_NOT_SECRET_PIN")
        original_popen = subprocess.Popen
        attempts = []

        class OfflineSSH:
            def __init__(self):
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO(b"")

            def wait(self, timeout=None):
                return 255

            def poll(self):
                return 255

            def kill(self):
                pass

        def process(args, *a, **kw):
            if args[0] == "ssh":
                attempts.append(args)
                return OfflineSSH()
            return original_popen(args, *a, **kw)

        monkeypatch.setattr(subprocess, "Popen", process)
        try:
            result = b1_backup.send(
                encrypted, "pc.example.ts.net", "backup", known, agent_path, "/root/tailscale/tailscale", tail_path
            )
            assert result["state"] == "PC_OFFLINE_OR_TRANSFER_UNKNOWN"
            assert not result["backup_completed"] and result["retry"] == result["fallback"] == 0
            assert len(attempts) == 1 and "-oIdentityFile=none" in attempts[0]
        finally:
            agent.close()
            tail.close()
    finally:
        subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "all"], capture_output=True, timeout=5)


def test_b1_refuses_live_or_tampered_backup_before_encryption(tmp_path):
    bundle = fixture_bundle(tmp_path)
    with pytest.raises(ValueError, match="FROZEN_BACKUP_DIGEST_REQUIRED"):
        b1_backup.validate_bundle(bundle, "0" * 64)
    with sqlite3.connect(tmp_path / "snapshot.db") as c:
        c.execute("update core_meta set value_json='false'")
    # Hash mismatch prevents an apparently valid manifest from hiding a changed DB.
    with tarfile.open(tmp_path / "tampered.tar", "w") as t:
        for n in ("snapshot.db", "privacy-intents.json", "snapshot.db.privacy.json", "manifest.json"):
            t.add(tmp_path / n, arcname=n)
    with pytest.raises(ValueError, match="CORE_BACKUP_FILE_MISMATCH"):
        b1_backup.validate_bundle(tmp_path / "tampered.tar", b1_backup.sha(tmp_path / "tampered.tar"))


def test_b1_never_sends_to_public_or_guessed_pc(tmp_path):
    with pytest.raises(ValueError, match="EXPLICIT_TAILNET_PC_REQUIRED"):
        b1_backup.send(tmp_path / "none", "example.com", "test", tmp_path / "none", tmp_path / "none", "/none", "/none")


def test_freeze_requires_original_registered_copy_and_preserves_quarantine(tmp_path):
    fixture_bundle(tmp_path)
    snapshot = tmp_path / "snapshot.db"
    anchor = tmp_path / "anchor.json"
    privacy = json.loads((tmp_path / "privacy-intents.json").read_text())
    privacy["backups"] = [str(snapshot)]
    anchor.write_text(json.dumps(privacy))
    (tmp_path / "snapshot.db.privacy.json").write_text(json.dumps({"anchor_path": str(anchor)}))
    frozen = tmp_path / "frozen.tar"
    result = b1_backup.freeze(snapshot, anchor, frozen)
    assert result["state"] == "FROZEN_LOCAL_COPY_NOT_OFFSITE"
    assert not result["active_restore"] and not result["b1_real_pc_qualified"]
    privacy["backups"] = []
    anchor.write_text(json.dumps(privacy))
    with pytest.raises(ValueError, match="ORIGINAL_CORE_REGISTERED_COPY_REQUIRED"):
        b1_backup.freeze(snapshot, anchor, tmp_path / "unregistered.tar")


def test_pc_partial_transfer_never_emits_success_receipt(tmp_path):
    header = {"sha256": hashlib.sha256(b"longer ciphertext").hexdigest(), "bytes": 100}
    response = io.BytesIO()
    with pytest.raises(ValueError, match="INCOMPLETE_BACKUP_TRANSFER"):
        b1_backup.receive(tmp_path, io.BytesIO((json.dumps(header) + "\n").encode() + b"short"), response)
    assert response.getvalue() == b""
    assert not (tmp_path / (header["sha256"] + ".gpg")).exists()
