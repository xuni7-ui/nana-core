"""Peer-side ABI / original Genesis checker adapter. No Genesis execution mode.

Original checker source+digest and read-only inputs are supplied explicitly by
its operator. This does not replace the checker or reinterpret its gate counts.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys


def normalize_args(args, mode):
    """Choose exactly one original checking mode; never enable creation."""
    if mode not in {"dry-run", "verify-only"}:
        raise ValueError("CHECK_MODE_REQUIRED")
    if any(x in {"--execute", "--create", "--activate", "--force"} for x in args):
        raise ValueError("GENESIS_EFFECT_MODE_DENIED")
    if any(x.startswith(("--dry-run=", "--verify-only=")) for x in args):
        raise ValueError("AMBIGUOUS_CHECK_MODE")
    return [x for x in args if x not in {"--dry-run", "--verify-only"}] + ["--" + mode]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True)
    p.add_argument("--mode", choices=["abi", "dry-run", "verify-only"], required=True)
    p.add_argument("--script")
    p.add_argument("--script-sha256")
    p.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    root = Path("/opt/nana-core/runtime/core-releases") / a.source
    metadata = json.loads((root / "runtime.json").read_text())
    if metadata["source_commit"] != a.source or Path(sys.prefix) != root / ".venv":
        raise ValueError("QUALIFIED_INTERPRETER_BINDING_MISMATCH")
    sys.path.insert(0, str(root / "src"))
    import ssl
    import sqlite3
    import pydantic
    from nana_core.host_requirements import sqlite_runtime_report

    if not sqlite_runtime_report()["supported"]:
        raise ValueError("SQLITE_UNSUPPORTED")
    if a.mode == "abi":
        import subprocess
        import _ssl

        libraries = subprocess.run(["ldd", _ssl.__file__], capture_output=True, text=True, timeout=5, check=True).stdout
        print(
            json.dumps(
                {
                    "status": "ABI_PASS_NOT_GENESIS_13_GATE_RESULT",
                    "python": sys.version.split()[0],
                    "sqlite": sqlite3.sqlite_version,
                    "openssl": ssl.OPENSSL_VERSION,
                    "pydantic": pydantic.__version__,
                    "python_executable": sys.executable,
                    "prefix": sys.prefix,
                    "ssl_extension": _ssl.__file__,
                    "loaded_libraries": libraries,
                    "uid": os.geteuid(),
                    "genesis_executed": False,
                }
            )
        )
        return
    if not a.script or not a.script_sha256:
        raise ValueError("ORIGINAL_CHECKER_REQUIRED")
    script = Path(a.script)
    if script.resolve() != script or not script.is_file() or script.stat().st_size > 1024 * 1024:
        raise ValueError("ORIGINAL_CHECKER_PATH_DENIED")
    if hashlib.sha256(script.read_bytes()).hexdigest() != a.script_sha256:
        raise ValueError("ORIGINAL_CHECKER_DIGEST_MISMATCH")
    original = a.args[1:] if a.args[:1] == ["--"] else a.args
    sys.argv = [str(script), *normalize_args(original, a.mode)]
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
