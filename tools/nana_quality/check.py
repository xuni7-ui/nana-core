"""Read-only delivery verification. No Store, authority, secrets or network."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/nana_engineering_quality_portable_v2_evidence"


def load(name):
    return json.loads((EVIDENCE / name).read_text())


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(archive=None):
    manifest = load("manifest.json")
    for name, digest in manifest["files"].items():
        path = Path(name)
        require(not path.is_absolute() and ".." not in path.parts and name != "manifest.json", "MANIFEST_PATH_INVALID")
        require(sha(EVIDENCE / path) == digest, "EVIDENCE_DIGEST_MISMATCH")
    q = load("qualification.json")
    reg = load("regression.json")
    portable = load("portable.json")
    require(
        reg["final"]["failed"] == reg["final"]["errors"] == 0 and reg["final"]["passed"] >= 1528,
        "FINAL_REGRESSION_NOT_PASSED",
    )
    require(q["new_provider_calls"] == 0 and q["frontend_contract_changed"] is False, "UNEXPECTED_SCOPE_CHANGE")
    require(
        q["human_naturalness"] == "NOT_RUN" and q["first_life"] == "NOT_READY" and q["beta"] == "NO",
        "UNSUPPORTED_READINESS_UPGRADE",
    )
    require(
        q["historical_residency"] == "PARTIAL_EXTERNAL_LIMIT" and q["long_residency"] == "PENDING_EXTERNAL_STABLE_ENV",
        "RESIDENCY_REWRITTEN",
    )
    require(portable["release"]["sha256"] == portable["rebuild"]["sha256"], "NONREPRODUCIBLE_RUNTIME")
    require(
        portable["qualification_release"]["sha256"] == portable["qualification_rebuild"]["sha256"],
        "NONREPRODUCIBLE_QUALIFICATION",
    )
    require(
        portable["installed_optional"]["sqlite"] == "3.51.3"
        and portable["installed_optional"]["all_runtime_imports_closed"],
        "MINIMUM_BINDING_NOT_QUALIFIED",
    )
    require(
        portable["installed_optional"]["optimize"] == 1 and portable["installed_precision"]["file_move_count"] == 1,
        "INSTALLED_RECOVERY_NOT_QUALIFIED",
    )
    sql = load("sqlite.json")
    require(
        sql["unsupported"]["report"]["code"] == "SQLITE_VERSION_UNSUPPORTED"
        and not sql["unsupported"]["subject_created"],
        "OLD_SQLITE_NOT_REJECTED",
    )
    require(
        sql["missing_native"]["report"]["code"] == "PYTHON_NATIVE_MODULES_MISSING"
        and not sql["missing_native"]["subject_created"],
        "MISSING_NATIVE_NOT_REJECTED",
    )
    require(
        sha(ROOT / "PROJECT_BRAIN/00_MASTER_FRAMEWORK.md")
        == "fe6efe121a05145b44178d5ec26b99430a28e873fca8d1b80f16671c65e5133c",
        "MASTER_CHANGED",
    )
    require(
        not subprocess.check_output(
            [
                "git",
                "diff",
                "87f73d2",
                "--",
                "docs/nana_precision_v2_evidence",
                "docs/nana_real_world_controlled_expansion_v1_evidence",
            ],
            cwd=ROOT,
        ),
        "HISTORICAL_EVIDENCE_CHANGED",
    )
    for name, digest in load("source_fingerprints.json")["files"].items():
        path = Path(name)
        require(
            not path.is_absolute()
            and ".." not in path.parts
            and path.parts[0] in {"src", "tools", "packaging", "tests", "pyproject.toml", "requirements-quality.lock"},
            "SOURCE_PATH_INVALID",
        )
        require(sha(ROOT / path) == digest, "SOURCE_NOT_QUALIFIED_BYTES")
    if archive:
        require(sha(archive) == portable["release"]["sha256"], "ARCHIVE_HASH_MISMATCH")
    return {
        "status": "PASS_READ_ONLY_QUALITY_DELIVERY_CHECK",
        "runtime_source": portable["release"]["source_commit"],
        "manifest_files": len(manifest["files"]),
        "archive_rehashed": bool(archive),
        "store_opened": False,
        "network_calls": 0,
        "first_life": "NOT_READY",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path)
    a = p.parse_args()
    print(json.dumps(check(a.archive), indent=2))
