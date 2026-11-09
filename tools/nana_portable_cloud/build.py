"""Build from an exact committed allowlist, never a workspace/database copy."""

import argparse, hashlib, json, subprocess, tarfile, gzip, io, re, ast, importlib.util
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[2]
DEPENDENCIES = {
    "pydantic": "2.13.4",
    "pydantic-core": "2.46.4",
    "annotated-types": "0.8.0",
    "typing-extensions": "4.16.0",
    "typing-inspection": "0.4.3",
}
FEATURE_DEPENDENCIES = {
    "HOST_VAULT": {"cryptography": "50.0.0", "cffi": "2.1.1", "pycparser": "3.0"},
    "PUBLIC_VIDEO_FRAMES": {"pillow": "12.3.0"},
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO)


def runtime_manifest(commit):
    lines = git("show", commit + ":packaging/portable/runtime-files.txt").decode().splitlines()
    names = [line for line in lines if line and not line.startswith("#")]
    if len(names) != len(set(names)) or any(
        not n.startswith("src/nana_core/") or ".." in Path(n).parts or Path(n).suffix not in {".py", ".sql"}
        for n in names
    ):
        raise ValueError("RUNTIME_MANIFEST_INVALID")
    return names


def verify_runtime_closure(selected, all_names, read):
    """Resolve static internal imports and separately declared dynamic assets."""
    chosen = set(selected)
    available = set(all_names)
    for name in selected:
        if not name.endswith(".py"):
            continue
        module = name.removeprefix("src/").removesuffix(".py").replace("/", ".")
        package = module.removesuffix(".__init__") if module.endswith(".__init__") else module.rpartition(".")[0]
        for node in ast.walk(ast.parse(read(name))):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
                for target in targets:
                    if target == "nana_core" or target.startswith("nana_core."):
                        module_path = "src/" + target.replace(".", "/")
                        if module_path + ".py" not in available:
                            prefix = module_path + "/"
                            if not any(path.startswith(prefix) for path in available):
                                raise ValueError("RUNTIME_IMPORT_MISSING: " + target)
                            if not any(path.startswith(prefix) for path in chosen):
                                raise ValueError("RUNTIME_IMPORT_MISSING: " + target)
            elif isinstance(node, ast.ImportFrom):
                base = (
                    importlib.util.resolve_name("." * node.level + (node.module or ""), package)
                    if node.level
                    else node.module or ""
                )
                targets = [base, *[base + "." + a.name for a in node.names]]
            for target in targets:
                if not target.startswith("nana_core"):
                    continue
                candidates = (
                    "src/" + target.replace(".", "/") + ".py",
                    "src/" + target.replace(".", "/") + "/__init__.py",
                )
                for dep in candidates:
                    if dep in available and dep not in chosen:
                        raise ValueError("RUNTIME_IMPORT_MISSING: " + dep)
    for asset in (
        "continuity/hands/server.py",
        "continuity/hands/browser.py",
        "continuity/open_agency/skill_runner.py",
    ):
        if "src/nana_core/" + asset not in chosen:
            raise ValueError("RUNTIME_DYNAMIC_ASSET_MISSING")


def build(destination, wheels, revision="HEAD", *, features=()):
    if len(set(features)) != len(features) or set(features) - set(FEATURE_DEPENDENCIES):
        raise ValueError("RUNTIME_FEATURE_INVALID")
    dependencies = dict(DEPENDENCIES)
    for feature in sorted(features):
        dependencies.update(FEATURE_DEPENDENCIES[feature])
    destination = Path(destination).absolute()
    if destination.exists() or destination.resolve() != destination:
        raise ValueError("CLEAN_BUILD_DESTINATION_REQUIRED")
    commit = git("rev-parse", revision + "^{commit}").decode().strip()
    epoch = int(git("show", "-s", "--format=%ct", commit))
    files = git("ls-tree", "-r", "--name-only", commit).decode().splitlines()
    selected = runtime_manifest(commit)
    sources = {name: git("show", commit + ":" + name) for name in selected}
    secret_contract = 1
    secret_source = sources.get("src/nana_core/life/secret_binding.py", b"")
    for node in ast.parse(secret_source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SUPPORTED_FD_CONTRACT_VERSION" for t in node.targets):
            secret_contract = ast.literal_eval(node.value)
            if type(secret_contract) is not int or secret_contract not in {1, 2}:
                raise ValueError("SECRET_BINDING_CONTRACT_INVALID")
    verify_runtime_closure(selected, files, lambda name: sources[name].decode())
    root = destination / "nana-first-life-portable-v1"
    root.mkdir(parents=True, mode=0o700)
    for name in files:
        if name in sources:
            target = name
        elif name.startswith("packaging/portable/"):
            target = name.removeprefix("packaging/portable/")
        else:
            continue
        mode = git("ls-tree", commit, "--", name).split()[0]
        if mode not in {b"100644", b"100755"}:
            raise ValueError("SOURCE_SYMLINK_DENIED")
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(git("show", commit + ":" + name))
        path.chmod(0o755 if target == "nana" or target.endswith(".sh") else 0o644)
    lock = []
    wheelroot = root / "wheelhouse"
    wheelroot.mkdir()
    for package, version in dependencies.items():
        candidates = list(Path(wheels).glob(package.replace("-", "_") + "-" + version + "-*.whl"))
        if len(candidates) != 1:
            raise ValueError("EXACT_WHEEL_REQUIRED")
        p = candidates[0]
        raw = p.read_bytes()
        (wheelroot / p.name).write_bytes(raw)
        lock.append(package + "==" + version + " --hash=sha256:" + hashlib.sha256(raw).hexdigest())
    (root / "requirements.lock").write_text("\n".join(lock) + "\n")
    (root / "runtime-boundary.json").write_text(
        json.dumps(
            {
                "format": "REVIEWED_RUNTIME_FILES_V1",
                "runtime_source_assets": selected,
                "static_import_closure": "VERIFIED",
                "dynamic_assets": ["hands.server", "hands.browser", "open_agency.skill_runner"],
                "development_lab_in_runtime": False,
                "demo_default_start": False,
                "optional_capabilities": [
                    "PROVIDER_PORTS",
                    "CONTROLLED_HANDS",
                    "LEARNING",
                    "CODE_SKILL_SANDBOX",
                    "PRECISION_CHECKPOINT",
                ],
                "qualification_tools": "SEPARATE_ARTIFACT",
            },
            indent=2,
        )
        + "\n"
    )
    (root / "runtime.json").write_text(
        json.dumps(
            {
                "bundle_version": 1,
                "source_commit": commit,
                "schema_version": 13,
                "supported_platform": "Linux x86_64 / CPython3.12 / glibc>=" + ("2.34" if "HOST_VAULT" in features else "2.17"),
                "build_timestamp": datetime.fromtimestamp(epoch, timezone.utc).isoformat(),
                "timestamp_policy": "SOURCE_COMMIT_TIMESTAMP_REPRODUCIBLE",
                "dependencies": dependencies,
                "features": sorted(features),
                "secret_binding_contract": secret_contract,
                "archive_ingress_contract": 1 if 'src/nana_core/migration/archive_ingress.py' in sources else 0,
                "bilibili_life_contract": 1 if 'src/nana_core/life/bilibili_life.py' in sources else 0,
                "platform_runtime_contract": 1 if 'src/nana_core/life/platform_runtime.py' in sources else 0,
                "private_context_contract": int(b'PRIVATE_CONTEXT' in sources.get('src/nana_core/life/live_api/contracts.py', b'')),
                "real_provider_calls": 0,
            },
            indent=2,
        )
        + "\n"
    )
    pattern = re.compile(rb"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}")
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError("BUNDLE_SYMLINK_DENIED")
        if p.is_file() and p.suffix != ".whl" and pattern.search(p.read_bytes()):
            raise ValueError("BUNDLE_SECRET_LITERAL")
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    (root / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(root).as_posix() + "\n" for p in paths
        )
    )
    archive = destination / "nana-first-life-portable-v1.tar.gz"
    with (
        archive.open("wb") as stream,
        gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as tar,
    ):
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            raw = p.read_bytes()
            info = tarfile.TarInfo("nana-first-life-portable-v1/" + p.relative_to(root).as_posix())
            info.size = len(raw)
            # Generated metadata/wheels otherwise inherit the host's umask,
            # making identical committed inputs produce different archives.
            relative = p.relative_to(root).as_posix()
            info.mode = 0o755 if relative == "nana" or relative.endswith(".sh") else 0o644
            info.mtime = epoch
            tar.addfile(info, io.BytesIO(raw))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(checksum + "  " + archive.name + "\n")
    unpack = destination / "nana-unpack.py"
    unpack.write_bytes(git("show", commit + ":tools/nana_portable_cloud/unpack.py"))
    return {
        "archive": str(archive),
        "sha256": checksum,
        "source_commit": commit,
        "bundle_files": len(paths) + 1,
        "new_provider_calls": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--wheels", type=Path, required=True)
    p.add_argument("--revision", default="HEAD")
    p.add_argument("--feature", action="append", choices=sorted(FEATURE_DEPENDENCIES), default=[])
    a = p.parse_args()
    print(json.dumps(build(a.output, a.wheels, a.revision, features=a.feature), indent=2))


if __name__ == "__main__":
    main()
