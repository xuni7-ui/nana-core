"""B1 encrypted backup preparation/transport, not Subject activation or live copy.

Only explicit frozen Core-backup bundles may be input. GPG uses a PC-owned
public recipient and an explicit keyring directory, never the default keyring.
PC private keys stay on PC. A transfer acknowledgement is NOT restore evidence.
"""

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path

LIMIT = 1024**3


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while b := f.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()


def freeze(snapshot, privacy_anchor, output):
    """Package an original registered quarantine copy plus its privacy snapshot.

    Does not back up a live DB or start/open a Subject. Changes during copying
    reject the bundle; later withdrawals still require reconciliation on restore.
    """
    snapshot, privacy_anchor, output = Path(snapshot).absolute(), Path(privacy_anchor).absolute(), Path(output)
    if snapshot.resolve() != snapshot or privacy_anchor.resolve() != privacy_anchor:
        raise ValueError("EXPLICIT_REGULAR_BACKUP_INPUTS_REQUIRED")
    sidecar = Path(str(snapshot) + ".privacy.json")
    if sidecar.is_symlink() or sidecar.stat().st_size > 65536 or privacy_anchor.stat().st_size > 16 * 1024**2:
        raise ValueError("CORE_PRIVACY_METADATA_BOUND")
    if Path(json.loads(sidecar.read_bytes())["anchor_path"]).resolve() != privacy_anchor:
        raise ValueError("EXPLICIT_PRIVACY_ANCHOR_MISMATCH")
    before = privacy_anchor.read_bytes()
    privacy = json.loads(before)
    if str(snapshot) not in privacy.get("backups", []):
        raise ValueError("ORIGINAL_CORE_REGISTERED_COPY_REQUIRED")
    if output.exists() or output.is_symlink():
        raise ValueError("FRESH_BACKUP_BUNDLE_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="nana-b1-frozen-") as temporary:
        root = Path(temporary)
        for source, name in ((snapshot, "snapshot.db"), (sidecar, "snapshot.db.privacy.json")):
            with source.open("rb") as inp, (root / name).open("xb") as out:
                os.fchmod(out.fileno(), 0o600)
                total = 0
                while b := inp.read(1024 * 1024):
                    total += len(b)
                    if total > LIMIT:
                        raise ValueError("BACKUP_FILE_BOUND")
                    out.write(b)
        (root / "privacy-intents.json").write_bytes(before)
        if before != privacy_anchor.read_bytes():
            raise ValueError("PRIVACY_CHANGED_DURING_FREEZE_NO_AUTOMATIC_RETRY")
        names = ("snapshot.db", "snapshot.db.privacy.json", "privacy-intents.json")
        manifest = {
            "kind": "ORIGINAL_CORE_QUARANTINED_BACKUP",
            "identity_sha256": hashlib.sha256(privacy["identity_id"].encode()).hexdigest(),
            "evidence_scope": "OPERATOR_FROZEN_CORE_BACKUP_NOT_YET_OFFSITE",
            "files": {n: sha(root / n) for n in names},
        }
        (root / "manifest.json").write_text(json.dumps(manifest))
        with output.open("xb") as out:
            os.fchmod(out.fileno(), 0o600)
            with tarfile.open(fileobj=out, mode="w") as tar:
                for name in (*names, "manifest.json"):
                    tar.add(root / name, arcname=name)
            out.flush()
            os.fsync(out.fileno())
    result = validate_bundle(output, sha(output))
    result["state"] = "FROZEN_LOCAL_COPY_NOT_OFFSITE"
    return result


def validate_bundle(path, expected):
    """Inspect only an explicit frozen review backup; no active Store is opened."""
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > LIMIT or sha(path) != expected:
        raise ValueError("FROZEN_BACKUP_DIGEST_REQUIRED")
    with tarfile.open(path, "r:") as t:
        members = {}
        for m in t:
            if (
                not m.isfile()
                or Path(m.name).name != m.name
                or m.name in members
                or m.size > LIMIT
                or len(members) >= 16
            ):
                raise ValueError("BACKUP_MEMBER_DENIED")
            if m.name not in {"manifest.json", "snapshot.db", "privacy-intents.json", "snapshot.db.privacy.json"}:
                raise ValueError("BACKUP_NOT_EXPLICIT_CORE_SNAPSHOT")
            members[m.name] = m
        if set(members) != {"manifest.json", "snapshot.db", "privacy-intents.json", "snapshot.db.privacy.json"}:
            raise ValueError("CORE_BACKUP_PRIVACY_FAMILY_REQUIRED")
        if members["manifest.json"].size > 65536:
            raise ValueError("BACKUP_MANIFEST_BOUND")
        if any(m.size > 16 * 1024**2 for n, m in members.items() if n.endswith(".json")):
            raise ValueError("BACKUP_PRIVACY_METADATA_BOUND")
        manifest = json.load(t.extractfile(members["manifest.json"]))
        if manifest.get("kind") != "ORIGINAL_CORE_QUARANTINED_BACKUP" or set(manifest["files"]) != set(members) - {
            "manifest.json"
        }:
            raise ValueError("CORE_REVIEW_BACKUP_REQUIRED")
        with tempfile.TemporaryDirectory(prefix="nana-b1-review-") as tmp:
            for name in members:
                if name == "manifest.json":
                    continue
                h = hashlib.sha256()
                # No general archive extraction; only fixed filenames in a private temp.
                p = Path(tmp) / name
                with p.open("xb") as out, t.extractfile(members[name]) as source:
                    os.fchmod(out.fileno(), 0o600)
                    while b := source.read(1024 * 1024):
                        h.update(b)
                        out.write(b)
                if h.hexdigest() != manifest["files"][name]:
                    raise ValueError("CORE_BACKUP_FILE_MISMATCH")
            dbpath = Path(tmp) / "snapshot.db"
            with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
                if (
                    db.execute("pragma quick_check").fetchone()[0] != "ok"
                    or db.execute("pragma foreign_key_check").fetchone()
                ):
                    raise ValueError("RESTORE_DATABASE_INTEGRITY")
                if (
                    db.execute("select value_json from core_meta where key='recovery_quarantine'").fetchone()[0]
                    != "true"
                ):
                    raise ValueError("RESTORE_MUST_REMAIN_QUARANTINED")
                rows = db.execute("select identity_id from identities").fetchall()
                if len(rows) != 1 or hashlib.sha256(rows[0][0].encode()).hexdigest() != manifest["identity_sha256"]:
                    raise ValueError("RESTORE_SUBJECT_BINDING_MISMATCH")
            privacy = json.loads((Path(tmp) / "privacy-intents.json").read_bytes())
            if privacy.get("identity_id") != rows[0][0] or not isinstance(privacy.get("intents"), list):
                raise ValueError("RESTORE_PRIVACY_BINDING_MISMATCH")
        return {
            "state": "QUARANTINED_RESTORE_BYTES_VERIFIED_NOT_ACTIVATED",
            "bundle_sha256": expected,
            "identity_sha256": manifest["identity_sha256"],
            "evidence_scope": manifest["evidence_scope"],
            "active_restore": False,
            "b1_real_pc_qualified": False,
        }


def encrypt(bundle, expected, public_key, fingerprint, output):
    checked = validate_bundle(bundle, expected)
    if not re.fullmatch(r"[A-Fa-f0-9]{40}", fingerprint):
        raise ValueError("PINNED_PC_KEY_FINGERPRINT_REQUIRED")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("FRESH_ENCRYPTED_OUTPUT_REQUIRED")
    if Path(public_key).is_symlink() or Path(public_key).stat().st_size > 1024 * 1024:
        raise ValueError("PUBLIC_RECIPIENT_KEY_BOUND")
    with tempfile.TemporaryDirectory(prefix="nana-b1-public-keyring-") as home:
        gpg = ["gpg", "--no-options", "--homedir", home, "--batch", "--no-tty"]
        metadata = subprocess.run(
            [*gpg, "--with-colons", "--show-keys", str(public_key)],
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        ).stdout
        first = next((line.split(":")[9] for line in metadata.splitlines() if line.startswith("fpr:")), None)
        if first != fingerprint.upper() or "sec:" in metadata:
            raise ValueError("PC_PUBLIC_KEY_IDENTITY_MISMATCH")
        # Reject any secret-key export packet, not merely a label in a file name.
        packets = subprocess.run(
            [*gpg, "--list-packets", str(public_key)], capture_output=True, check=True, timeout=10
        ).stdout
        if b":secret key packet:" in packets or b":secret sub key packet:" in packets:
            raise ValueError("PC_PRIVATE_KEY_MUST_NOT_LEAVE_PC")
        subprocess.run(
            [*gpg, "--import", str(public_key)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=10,
        )
        partial = output.with_name(output.name + ".partial")
        with partial.open("xb") as out:
            os.fchmod(out.fileno(), 0o600)
            subprocess.run(
                [
                    *gpg,
                    "--output",
                    "-",
                    "--trust-model",
                    "always",
                    "--cipher-algo",
                    "AES256",
                    "--compress-algo",
                    "none",
                    "--recipient",
                    fingerprint.upper(),
                    "--encrypt",
                    str(bundle),
                ],
                stdout=out,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=60,
            )
            out.flush()
            os.fsync(out.fileno())
        os.link(partial, output)
        partial.unlink()
    return {
        "state": "ENCRYPTED_LOCALLY_NOT_OFFSITE",
        "ciphertext_sha256": sha(output),
        "bytes": output.stat().st_size,
        "snapshot_evidence_scope": checked["evidence_scope"],
        "b1_real_pc_qualified": False,
    }


def receive(root, source, sink):
    """Install on the PC as the dedicated SSH forced command nana-b1-receiver."""
    root = Path(root).absolute()
    if root.resolve() != root or not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError("PRIVATE_PC_BACKUP_DIRECTORY_REQUIRED")
    line = source.readline(4097)
    if len(line) > 4096 or not line.endswith(b"\n"):
        raise ValueError("BACKUP_HEADER_BOUND")
    v = json.loads(line)
    if (
        set(v) != {"sha256", "bytes"}
        or not re.fullmatch(r"[a-f0-9]{64}", v["sha256"])
        or type(v["bytes"]) is not int
        or not 0 < v["bytes"] <= LIMIT
    ):
        raise ValueError("BACKUP_HEADER_INVALID")
    destination = root / (v["sha256"] + ".gpg")
    partial = root / (v["sha256"] + ".partial")
    with partial.open("xb") as out:
        os.fchmod(out.fileno(), 0o600)
        h = hashlib.sha256()
        total = 0
        while total < v["bytes"]:
            b = source.read(min(1024 * 1024, v["bytes"] - total))
            if not b:
                raise ValueError("INCOMPLETE_BACKUP_TRANSFER")
            h.update(b)
            out.write(b)
            total += len(b)
        if h.hexdigest() != v["sha256"]:
            raise ValueError("BACKUP_CIPHERTEXT_MISMATCH")
        out.flush()
        os.fsync(out.fileno())
    os.link(partial, destination)
    partial.unlink()
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    sink.write((json.dumps({"state": "RECEIVED_ENCRYPTED_ONLY", **v, "restored": False}) + "\n").encode())


def send(ciphertext, host, user, known_hosts, agent, tailscale, socket):
    # Explicit target only. Never scan peers or discover historical credentials.
    try:
        permitted = ipaddress.ip_address(host) in ipaddress.ip_network("100.64.0.0/10")
    except ValueError:
        permitted = bool(re.fullmatch(r"[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+\.ts\.net", host))
    if not permitted or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_-]*", user):
        raise ValueError("EXPLICIT_TAILNET_PC_REQUIRED")
    if (
        not stat.S_ISSOCK(Path(agent).stat().st_mode)
        or not stat.S_ISSOCK(Path(socket).stat().st_mode)
        or not Path(known_hosts).is_file()
    ):
        raise ValueError("EXPLICIT_SSH_AGENT_AND_PINNED_HOST_KEYS_REQUIRED")
    import shlex

    proxy = " ".join(shlex.quote(str(x)) for x in (tailscale, "--socket", socket, "nc")) + " %h %p"
    command = [
        "ssh",
        "-F",
        "/dev/null",
        "-oBatchMode=yes",
        "-oStrictHostKeyChecking=yes",
        "-oConnectTimeout=5",
        "-oServerAliveInterval=5",
        "-oServerAliveCountMax=1",
        "-oIdentityFile=none",
        "-oPreferredAuthentications=publickey",
        "-oGlobalKnownHostsFile=/dev/null",
        "-oIdentityAgent=" + str(agent),
        "-oUserKnownHostsFile=" + str(known_hosts),
        "-oProxyCommand=" + proxy,
        "-l",
        user,
        host,
        "nana-b1-receiver",
    ]
    path = Path(ciphertext)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError("REGULAR_BOUNDED_ENCRYPTED_BACKUP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="nana-b1-packet-check-") as home:
        result = subprocess.run(
            [
                "gpg",
                "--no-options",
                "--homedir",
                home,
                "--batch",
                "--no-tty",
                "--list-only",
                "--list-packets",
                str(path),
            ],
            capture_output=True,
            timeout=10,
        )
        if b":pubkey enc packet:" not in result.stdout or b":encrypted data packet:" not in result.stdout:
            raise ValueError("ONLY_PUBLIC_KEY_ENCRYPTED_BACKUP_MAY_LEAVE_HOST")
    v = {"sha256": sha(path), "bytes": path.stat().st_size}
    if v["bytes"] > LIMIT:
        raise ValueError("BACKUP_TRANSFER_BOUND")
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    timer = threading.Timer(60, process.kill)
    timer.start()
    try:
        process.stdin.write((json.dumps(v) + "\n").encode())
        with path.open("rb") as source:
            while b := source.read(1024 * 1024):
                process.stdin.write(b)
        process.stdin.close()
        reply = process.stdout.read(4097)
        code = process.wait(timeout=65)
        if code or len(reply) > 4096:
            raise ValueError("PC_TRANSFER_UNCONFIRMED_NO_RETRY")
        ack = json.loads(reply)
        if (
            ack.get("sha256") != v["sha256"]
            or ack.get("bytes") != v["bytes"]
            or ack.get("state") != "RECEIVED_ENCRYPTED_ONLY"
        ):
            raise ValueError("PC_RECEIPT_MISMATCH_NO_RETRY")
        return {"state": "PC_RECEIVED_RESTORE_STILL_REQUIRED", "sha256": v["sha256"], "b1_real_pc_qualified": False}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {
            "state": "PC_OFFLINE_OR_TRANSFER_UNKNOWN",
            "backup_completed": False,
            "retry": 0,
            "fallback": 0,
            "b1_real_pc_qualified": False,
        }
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    import sys

    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="op", required=True)
    f = sub.add_parser("freeze")
    for n in ("snapshot", "privacy-anchor", "output"):
        f.add_argument("--" + n, type=Path, required=True)
    e = sub.add_parser("encrypt")
    for n in ("bundle", "public-key", "output"):
        e.add_argument("--" + n, type=Path, required=True)
    e.add_argument("--bundle-sha256", required=True)
    e.add_argument("--recipient-fingerprint", required=True)
    v = sub.add_parser("verify-restored")
    v.add_argument("--bundle", type=Path, required=True)
    v.add_argument("--bundle-sha256", required=True)
    r = sub.add_parser("receive")
    r.add_argument("--root", type=Path, required=True)
    s = sub.add_parser("send")
    for n in ("ciphertext", "known-hosts", "agent", "tailscale", "socket"):
        s.add_argument("--" + n, type=Path, required=True)
    s.add_argument("--host", required=True)
    s.add_argument("--user", required=True)
    a = p.parse_args()
    if a.op == "receive":
        receive(a.root, sys.stdin.buffer, sys.stdout.buffer)
    else:
        if a.op == "freeze":
            result = freeze(a.snapshot, a.privacy_anchor, a.output)
        elif a.op == "encrypt":
            result = encrypt(a.bundle, a.bundle_sha256, a.public_key, a.recipient_fingerprint, a.output)
        elif a.op == "verify-restored":
            result = validate_bundle(a.bundle, a.bundle_sha256)
        else:
            result = send(a.ciphertext, a.host, a.user, a.known_hosts, a.agent, a.tailscale, a.socket)
        print(json.dumps(result, indent=2))
