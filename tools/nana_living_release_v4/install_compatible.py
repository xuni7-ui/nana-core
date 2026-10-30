"""Fresh image only: install/compact each SDK before the next to bound disk peak."""

import os
from pathlib import Path
import runpy
import subprocess

ROOT = Path("/opt/nana-core/runtime/core-releases")
COMPATIBLE = (
    "13ddd484156f8216dabd1d339f0bba696f801dab",
    "af58490070cef26237bf81052d1939e5ce40ac46",
    "c8aa8c986219199d0d027ccce0791788516e9d85",
)


def main():
    if os.getuid() != 0 or not Path("/build/compact_venv.py").is_file():
        raise SystemExit("FRESH_IMAGE_BUILD_CONTEXT_REQUIRED")
    helpers = runpy.run_path("/build/compact_venv.py", run_name="fresh_image_helpers")
    for source in COMPATIBLE:
        release = ROOT / source
        print(
            {
                "installing_compatible_source": source,
                "free_bytes_before": os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize,
            },
            flush=True,
        )
        subprocess.run(
            ["/opt/nana-core/runtime/bin/python3", "-I", "-B", str(release / "bootstrap.py"), "install"],
            user=999,
            group=999,
            check=True,
        )
        helpers["compact"](ROOT, only=(source,))
        helpers["discard_build_caches"](release)


if __name__ == "__main__":
    main()
