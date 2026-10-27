"""Verify delivered image parts, optionally load the exact image. Never run it."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

from stage import DOCKER


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image-dir", type=Path, required=True)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--load", action="store_true")
    a = p.parse_args()
    raw = (a.image_dir / "image.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != a.manifest_sha256:
        raise ValueError("TRUSTED_IMAGE_MANIFEST_DIGEST_MISMATCH")
    subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("verify.py")), str(a.image_dir)], check=True)
    value = json.loads(raw)
    if a.load:
        proc = subprocess.Popen(
            DOCKER + ["load"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            for item in value["parts"]:
                with (a.image_dir / item["file"]).open("rb") as part:
                    while chunk := part.read(1024**2):
                        proc.stdin.write(chunk)
            proc.stdin.close()
            proc.stdin = None
            output, errors = proc.communicate(timeout=180)
            if proc.returncode:
                raise ValueError("DOCKER_LOAD_FAILED")
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        observed = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", value["image_id"]], text=True))[0]
        if (observed["Id"], observed["Os"], observed["Architecture"], observed["Config"]["User"]) != (
            value["image_id"],
            "linux",
            "amd64",
            "999:999",
        ):
            raise ValueError("LOADED_IMAGE_ID_PLATFORM_OR_USER_MISMATCH")
    print(
        json.dumps(
            {
                "state": "IMAGE_LOADED_NOT_STARTED" if a.load else "PARTS_VERIFIED_ONLY",
                "image_id": value["image_id"],
                "subject_created": False,
            }
        )
    )


if __name__ == "__main__":
    main()
