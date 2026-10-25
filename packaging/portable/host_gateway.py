"""Integrity-checked isolated entry for the versioned host BFF.

Separate from old v1/Demo. Run with this bundle's installed .venv Python -I.
Paths are derived from this immutable release, never ambient PYTHONPATH.
"""

import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def main():
    runpy.run_path(str(ROOT / "bootstrap.py"), run_name="nana_integrity")["verify"](ROOT)
    if sys.prefix == sys.base_prefix:
        raise ValueError("INSTALL_REQUIRED")
    sys.path.insert(0, str(ROOT / "src"))
    from nana_core.host_requirements import require_sqlite_runtime, python_runtime_report

    require_sqlite_runtime()
    if sys.version_info[:2] != (3, 12) or not python_runtime_report()["supported"]:
        raise ValueError("QUALIFIED_PYTHON_REQUIRED")
    from nana_core.life.live_api.__main__ import main as run

    run()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, ImportError):
        print(json.dumps({"state": "BLOCKED", "code": "HOST_GATEWAY_INTEGRITY_OR_INSTALL_FAILED"}))
        raise SystemExit(2) from None
