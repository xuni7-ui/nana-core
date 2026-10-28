"""Export one fully pinned, self-contained non-sensitive V4 handoff.

No credentials, host configuration or Subject data are accepted as inputs.
Manifest excludes itself and deploy.sh to avoid digest self-reference; the
wrapper pins its manifest and checks every tool before execution.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from tools.nana_first_life_android_v2.install_runtime_tree import manifest as runtime_manifest
from tools.nana_living_release_v4.docker_api import Docker

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while raw := stream.read(1024 * 1024):
            result.update(raw)
    return result.hexdigest()


WRAPPER = '''#!/bin/sh
set -eu
release_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -I -B - "$release_root" __DIGEST__ "$@" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]);expected=sys.argv[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
p=root/'MANIFEST.json'
if p.is_symlink() or sha(p)!=expected:raise SystemExit('RELEASE_MANIFEST_MISMATCH')
value=json.loads(p.read_bytes())
for name,row in value['files'].items():
 p=root/name
 if Path(name).is_absolute() or '..' in Path(name).parts or p.resolve()!=p or not p.is_file():raise SystemExit('RELEASE_FILE_INVALID: '+name)
 if sha(p)!=row['sha256']:raise SystemExit('RELEASE_FILE_DIGEST_MISMATCH: '+name)
os.execv(sys.executable,[sys.executable,'-I','-B',str(root/'tools/deploy.py'),'--handoff',str(root),'--manifest-sha256',expected,*sys.argv[3:]])
PY
'''


def copy_inputs(root, build, work):
    shutil.copyfile(build["core"]["archive"], root / "core.tar.gz")
    shutil.copyfile(work / "context/web.tar.gz", root / "web.tar.gz")
    shutil.copyfile(ROOT / "apps/nana-space/android/app/build/outputs/apk/debug/app-debug.apk", root / "nana-space-4.0.0-debug.apk")
    tools = root / "tools"
    tools.mkdir()
    for name in ("deploy.py", "docker_api.py", "integrity.py", "operator_stage.py", "proposal.py", "switch_release.py", "host_facts.py"):
        shutil.copyfile(ROOT / "tools/nana_living_release_v4" / name, tools / name)
    for directory, names in (
        ("nana_first_life_android_v2", ("install_runtime_tree.py",)),
        ("nana_first_life_unified_release", ("issue_pairing.py", "container_check.py", "operator_check.py", "patch_operator_flags.py")),
    ):
        for name in names:
            shutil.copyfile(ROOT / "tools" / directory / name, tools / name)
    target = root / "build"
    target.mkdir()
    for path in (work / "context").iterdir():
        # Archives are already delivered once at the root.
        if path.name not in {"core.tar.gz", "web.tar.gz"}:
            shutil.copyfile(path, target / path.name)
    shutil.copyfile(ROOT / "docs/nana_living_release_v4/DEPLOY.md", root / "README.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    build = json.loads((args.build / "build.json").read_bytes())
    root = args.destination.absolute()
    root.mkdir(mode=0o755, parents=True, exist_ok=False)
    copy_inputs(root, build, args.build)
    docker = Docker()
    container = docker.create_check(build["image_id"])
    archive = args.build / "final-runtime.tar"
    try:
        with archive.open("xb") as stream:
            docker.runtime_archive(container, stream)
    finally:
        docker.remove_check(container)
    tree = runtime_manifest(archive, image_id=build["image_id"])
    (root / "runtime-tree.json").write_text(json.dumps(tree, indent=2) + "\n")
    core_root = args.build / "core-first/nana-first-life-portable-v1"
    release = {"core_source": build["source_commit"], "core_sha256": sha(root / "core.tar.gz"),
               "core_integrity_sha256": sha(core_root / "SHA256SUMS"), "web_sha256": sha(root / "web.tar.gz"),
               "image_id": build["image_id"], "runtime_manifest_sha256": sha(root / "runtime-tree.json"),
               "schema_version": 13, "plan_contract": "PRECISION_V2", "real_provider_calls": 0}
    (root / "release.json").write_text(json.dumps(release, indent=2) + "\n")
    subprocess.run([sys.executable, "-m", "tools.nana_first_life_unified_release.export_image",
                    "--image", build["image_id"], "--source", build["source_commit"],
                    "--destination", str(root / "image")], cwd=ROOT, check=True)
    image = json.loads((root / "image/image.json").read_bytes())
    files = {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p)}
             for p in sorted(root.rglob("*")) if p.is_file()}
    manifest = {"contract": "nana-living-release/v4", "source_commit": build["source_commit"],
                "schema_version": 13, "plan_contract": "PRECISION_V2", "runtime_manifest_sha256": release["runtime_manifest_sha256"],
                "image": {"id": image["image_id"], "gzip_sha256": image["gzip_sha256"],
                          "parts": ["image/" + row["file"] for row in image["parts"]]},
                "files": files, "subject_data_included": False, "credentials_included": False,
                "activation": "SEPARATE_ORIGINAL_APPROVAL_REQUIRED"}
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    digest = sha(root / "MANIFEST.json")
    (root / "deploy.sh").write_text(WRAPPER.replace("__DIGEST__", digest))
    (root / "deploy.sh").chmod(0o755)
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    (root / "SHA256SUMS").write_text("".join(sha(p) + "  " + p.relative_to(root).as_posix() + "\n" for p in paths))
    print(json.dumps({"path": str(root), "manifest_sha256": digest, "files": len(paths) + 1,
                      "image_id": image["image_id"], "gzip_sha256": image["gzip_sha256"],
                      "gzip_bytes": image["gzip_bytes"], "runtime_entries": len(tree["entries"])}, indent=2))


if __name__ == "__main__":
    main()
