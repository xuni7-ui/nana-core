"""Single self-contained operator entry; prepare first, never fake activation.

The original Supervisor API remains the only live version-switch authority.
Installation only creates a sealed slot, without touching canonical home/config.
"""

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docker_api import Docker, DockerError
from integrity import sha


def relative(root, name):
    path = root / name
    if Path(name).is_absolute() or ".." in Path(name).parts or path.resolve() != path:
        raise ValueError("RELEASE_PATH_DENIED")
    return path


def bundle(root, expected):
    path = root / "MANIFEST.json"
    if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024 or sha(path) != expected:
        raise ValueError("RELEASE_MANIFEST_MISMATCH")
    manifest = json.loads(path.read_bytes())
    if (manifest["contract"] != "nana-living-release/v4" or manifest["schema_version"] != 13
            or manifest["plan_contract"] != "PRECISION_V2"):
        raise ValueError("RELEASE_CONTRACT_INCOMPATIBLE")
    errors = []
    for name, row in manifest["files"].items():
        file = relative(root, name)
        if not file.is_file():
            errors.append({"path": name, "reason": "MISSING", "expected_sha256": row["sha256"], "actual_sha256": None})
        elif file.stat().st_size != row["bytes"] or sha(file) != row["sha256"]:
            errors.append({"path": name, "reason": "CONTENT_MISMATCH", "expected_sha256": row["sha256"], "actual_sha256": sha(file)})
    if errors:
        return manifest, errors
    for path in root.rglob("*"):
        if path.is_symlink() or (path.is_file() and path.relative_to(root).as_posix() not in {*manifest["files"], "MANIFEST.json", "SHA256SUMS", "deploy.sh"}):
            errors.append({"path": path.relative_to(root).as_posix(), "reason": "EXTRA_FILE"})
    return manifest, errors


class Parts(io.RawIOBase):
    def __init__(self, paths):
        self.paths, self.stream = iter(paths), None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.stream is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.stream = path.open("rb")
            size = self.stream.readinto(buffer)
            if size:
                return size
            self.stream.close()
            self.stream = None

    def close(self):
        if self.stream:
            self.stream.close()
        super().close()


def load(docker, root, manifest):
    image = manifest["image"]
    try:
        return docker.image(image["id"])
    except DockerError as exc:
        if str(exc) != "DOCKER_HTTP_404":
            raise
    paths = [relative(root, item) for item in image["parts"]]
    combined = hashlib.sha256()
    for path in paths:
        with path.open("rb") as stream:
            while raw := stream.read(1024 * 1024):
                combined.update(raw)
    if combined.hexdigest() != image["gzip_sha256"]:
        raise ValueError("IMAGE_PARTS_COMBINED_MISMATCH")
    with io.BufferedReader(Parts(paths)) as joined, gzip.GzipFile(fileobj=joined) as compressed:
        docker.load(iter(lambda: compressed.read(1024 * 1024), b""))
    return docker.image(image["id"])


def prepare(docker, root, manifest, host_root, mode):
    image = manifest["image"]["id"]
    if mode == "install":
        load(docker, root, manifest)
    else:
        try:
            docker.image(image)
        except DockerError as exc:
            if str(exc) == "DOCKER_HTTP_404":
                return {"state": "IMAGE_NOT_LOADED", "persistent_changes": 0, "next": "deploy.sh --install"}
            raise
    tools = root / "tools"
    files = {name: (tools / name).read_bytes() for name in ("operator_stage.py", "integrity.py", "install_runtime_tree.py", "proposal.py")}
    files["runtime-tree.json"] = (root / "runtime-tree.json").read_bytes()
    files["release.json"] = (root / "release.json").read_bytes()
    arguments = [
        "--source", manifest["source_commit"], "--image", image,
        "--manifest", "/run/nana-operator/runtime-tree.json", "--digest", manifest["runtime_manifest_sha256"],
    ]
    result = docker.operator(image, host_root, mode, files, arguments)
    result["daemon"] = docker.version()
    result["paid_provider_calls"] = 0
    if result["state"] == "RUNTIME_STAGED_VERIFY_REQUIRED" and mode == "install":
        check = docker.create_check(image, runtime=result["target"], core_source=manifest["source_commit"])
        try:
            result["runtime_abi"] = docker.verify_check(check)
        finally:
            docker.remove_check(check)
        if result["runtime_abi"]["exit_code"]:
            result["state"] = "RUNTIME_ABI_FAILED_NOT_SWITCHED"
        else:
            committed = docker.operator(image, host_root, "commit", files, arguments)
            if committed["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED":
                result.update(committed)
            elif committed["state"] != "READY_FOR_SWITCH":
                result["state"] = "STAGE_COMMIT_UNVERIFIED"
            else:
                result["state"] = "READY_FOR_SWITCH"
    return result


def rollback(args):
    """Original authenticated confirmation + rollback transition, no DB restore."""
    if not all((args.base, args.subject_id, args.release_id)) or args.password_fd is None:
        return {"state": "ROLLBACK_AUTHENTICATED_TARGET_REQUIRED", "services_changed": False,
                "next": "Use the original Host Admin confirmation for an already registered compatible release; never overwrite Store."}
    from switch_release import switch
    return switch(args.base, args.subject_id, args.release_id, args.password_fd, operation="ROLLBACK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for mode in ("check", "dry-run", "install", "rollback"):
        group.add_argument("--" + mode, dest="mode", action="store_const", const=mode)
    parser.add_argument("--handoff", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--root", default="/srv/nana-core")
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--base")
    parser.add_argument("--subject-id")
    parser.add_argument("--release-id")
    parser.add_argument("--password-fd", type=int)
    parser.add_argument("--local-dev-vfs-headroom-mib", type=int, default=0,
                        help="Only for a managed DEV vfs daemon sharing this filesystem; bounded pre-create wait, never retry")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"/[A-Za-z0-9/._-]+", args.root) or ".." in Path(args.root).parts:
            raise ValueError("EXPLICIT_OPERATOR_ROOT_REQUIRED")
        manifest, errors = bundle(args.handoff.resolve(), args.manifest_sha256)
        if errors:
            result = {"state": "RELEASE_INTEGRITY_FAILED", "mismatch_count": len(errors), "mismatches": errors[:64]}
        elif args.mode == "rollback":
            result = rollback(args)
        else:
            result = prepare(Docker(local_vfs_headroom_mib=args.local_dev_vfs_headroom_mib),
                             args.handoff.resolve(), manifest, args.root, args.mode)
    except (ValueError, KeyError, OSError, DockerError) as exc:
        code = str(exc) if isinstance(exc, (ValueError, DockerError)) and re.fullmatch(r"[A-Z0-9_]+", str(exc)) else "DEPLOYMENT_CONTEXT_UNAVAILABLE"
        result = {"state": "BLOCKED", "code": code, "services_changed": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    success = result["state"] in {"READY_FOR_SWITCH", "VERIFIED"}
    planned = args.mode == "dry-run" and result["state"] in {"NOT_INSTALLED", "IMAGE_NOT_LOADED"}
    return 0 if success or planned else 2


if __name__ == "__main__":
    raise SystemExit(main())
