"""User-owned release signing, explicit password FDs only; no default key.

Run on the trusted signer's host. This tool never generates a production key,
prints a password, changes a debug app into a fake release or uploads an APK.
"""

import argparse
import os
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apksigner", type=Path, required=True)
    p.add_argument("--unsigned", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--keystore", type=Path, required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--store-password-fd", type=int, required=True)
    p.add_argument("--key-password-fd", type=int, required=True)
    a = p.parse_args()
    if a.output.exists() or a.keystore.is_symlink() or not a.keystore.is_file() or a.keystore.stat().st_mode & 0o077:
        raise SystemExit("PRIVATE_USER_KEY_AND_FRESH_OUTPUT_REQUIRED")
    # apksigner's documented stdin password source. Password bytes are never
    # command arguments/environment; stdout/stderr are suppressed on failure.
    values = []
    for fd in (a.store_password_fd, a.key_password_fd):
        raw = os.read(fd, 1025)
        os.close(fd)
        if len(raw) > 1024 or not raw.rstrip(b"\r\n") or b"\n" in raw.rstrip(b"\r\n"):
            raise SystemExit("PASSWORD_FD_INVALID")
        values.append(raw.rstrip(b"\r\n"))
    result = subprocess.run(
        [
            str(a.apksigner),
            "sign",
            "--ks",
            str(a.keystore),
            "--ks-key-alias",
            a.alias,
            "--ks-pass",
            "stdin",
            "--key-pass",
            "stdin",
            "--out",
            str(a.output),
            str(a.unsigned),
        ],
        input=b"\n".join(values) + b"\n",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    values.clear()
    if result.returncode:
        raise SystemExit("SIGNING_FAILED_NO_SECRET_OUTPUT")
    subprocess.run([str(a.apksigner), "verify", str(a.output)], check=True)
    print("USER_OWNED_RELEASE_SIGNED_AND_VERIFIED")


if __name__ == "__main__":
    main()
