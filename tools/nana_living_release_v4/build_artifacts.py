"""Build a committed Core twice and an offline matched image; never host data.

The exact qualified Debian13 SDK is reused unmodified. Web must already be
built from the same clean source. This builder does not initialize a Subject.
"""

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from tools.nana_portable_cloud.build import build

ROOT = Path(__file__).resolve().parents[2]
BASE = "sha256:6581d9e0cb7e686511aa704f77546cae508fc2911792753ed3a9bd3bf3cdb18b"
BASE_TAG = "nana-first-life/unified:v3-3665"
COMPATIBLE_CORES = (
    ("compat-13.tar.gz", "435ca7a819847fc7d8a60dd6088f0e712ecbf965", "NANA_CORE_LIVING_V4_RELEASE/core.tar.gz", "728ef440fc34ab5c1b821814fae93408ee0b7384c5bad6959d274cb9ec5e5347"),
    ("compat-af.tar.gz", None, "tools/nana_living_release_v4/compatibility/af584900.core.tar.gz", "c091d70574911bb61bd401879300703df178f885ed7bc64cec2283247661acf3"),
    ("compat-c8.tar.gz", "153196b1c39f41de0a20e7ac8cb1787cdf2bca80", "NANA_CORE_LIVING_V4_RELEASE/core.tar.gz", "c562b41aada49a48736269e29c8f07487f07b7b15c2694d75356541562c7d92c"),
)
DOCKER = ["env", "-u", "DOCKER_HOST", "-u", "DOCKER_CONTEXT", "-u", "DOCKER_TLS",
          "-u", "DOCKER_TLS_VERIFY", "-u", "DOCKER_CERT_PATH", "docker", "--host=unix:///var/run/docker.sock"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def web_archive(destination, epoch):
    root = ROOT / "apps/nana-space/dist"
    if not (root / "index.html").is_file():
        raise ValueError("LIVE_WEB_BUILD_REQUIRED")
    with destination.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for file in sorted(root.rglob("*")):
                if file.is_symlink():
                    raise ValueError("WEB_SYMLINK_DENIED")
                if not file.is_file():
                    continue
                data = file.read_bytes()
                info = tarfile.TarInfo("nana-space-web/" + file.relative_to(root).as_posix())
                info.size, info.mtime, info.mode = len(data), epoch, 0o644
                archive.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--wheels", type=Path, required=True)
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "rev-parse", args.source + "^{commit}"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "diff", "--quiet", commit, "--", "apps/nana-space", "src", "packaging", "tools/nana_living_release_v4"], cwd=ROOT, check=True)
    args.work.mkdir(mode=0o700, parents=True, exist_ok=False)
    first = build(args.work / "core-first", args.wheels, commit, features=("HOST_VAULT", "PUBLIC_VIDEO_FRAMES"))
    second = build(args.work / "core-repeat", args.wheels, commit, features=("HOST_VAULT", "PUBLIC_VIDEO_FRAMES"))
    if first["sha256"] != second["sha256"]:
        raise ValueError("CORE_REBUILD_MISMATCH")
    context = args.work / "context"
    context.mkdir()
    for filename, pinned, name, expected in COMPATIBLE_CORES:
        raw = subprocess.check_output(["git", "show", (pinned or commit) + ":" + name], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("COMPATIBLE_CORE_ARCHIVE_MISMATCH")
        (context / filename).write_bytes(raw)
    shutil.copyfile(first["archive"], context / "core.tar.gz")
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", commit], cwd=ROOT))
    web_archive(context / "web.tar.gz", epoch)
    paths = {"Dockerfile": "tools/nana_living_release_v4/Dockerfile", "unpack.py": "tools/nana_portable_cloud/unpack.py",
             "extract_web.py": "deployment/first-life-v2/docker/extract_web.py",
             "container_entry.py": "deployment/first-life-v2/docker/container_entry.py",
             "loopback_relay.py": "deployment/first-life-v2/docker/loopback_relay.py",
             "compact_venv.py": "tools/nana_living_release_v4/compact_venv.py"}
    for name, source in paths.items():
        (context / name).write_bytes(subprocess.check_output(["git", "show", commit + ":" + source], cwd=ROOT))
    metadata = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", BASE_TAG], text=True))[0]
    if (metadata["Id"], metadata["Os"], metadata["Architecture"], metadata["Config"]["User"]) != (BASE, "linux", "amd64", "999:999"):
        raise ValueError("QUALIFIED_BASE_MISMATCH")
    tag = "nana-first-life/living:v4-" + commit[:12]
    command = DOCKER + ["build", "--network=none", "--pull=false", "--build-arg", "BASE_IMAGE=" + BASE_TAG,
                       "--build-arg", "CORE_SOURCE_COMMIT=" + commit, "--build-arg", "CORE_SHA256=" + first["sha256"],
                       "--build-arg", "WEB_SHA256=" + sha(context / "web.tar.gz"), "-t", tag, str(context)]
    with (args.work / "image-build.log").open("w") as output:
        subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True, cwd=ROOT)
    image = subprocess.check_output(DOCKER + ["image", "inspect", "--format", "{{.Id}}", tag], text=True).strip()
    report = {"source_commit": commit, "base_image": BASE, "image_id": image, "image_tag": tag,
              "core": first, "core_repeat_sha256": second["sha256"], "core_reproducible": True,
              "web_sha256": sha(context / "web.tar.gz"), "real_provider_calls": 0,
              "formal_subject_created": False}
    (args.work / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
