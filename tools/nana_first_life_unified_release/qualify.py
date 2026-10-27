"""Reuse original isolated DEV lifecycle with an explicit release pin, never genesis."""

import argparse
import importlib.util
from pathlib import Path
import re


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--web-sha256", required=True)
    a = p.parse_args()
    if not re.fullmatch("[a-f0-9]{40}", a.source):
        raise ValueError("EXACT_COMMIT_REQUIRED")
    original = Path(__file__).resolve().parents[1] / "nana_first_life_android_v2/cloud_docker_probe.py"
    spec = importlib.util.spec_from_file_location("original_cloud_probe", original)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOURCE = a.source
    module.BUNDLE = "/opt/nana-core/runtime/core-releases/" + a.source
    module.PYTHON = module.BUNDLE + "/.venv/bin/python"
    import json

    print(json.dumps(module.run(a.image, a.work, a.web_sha256), indent=2))


if __name__ == "__main__":
    main()
