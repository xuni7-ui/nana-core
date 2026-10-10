"""Optional compact evidence from actual test runs; assertions remain authoritative."""
import json
import os
from pathlib import Path


def record(key, value):
    path = os.environ.get("NANA_DEV_ENGINEERING_PROOF")
    if path:
        target = Path(path)
        data = json.loads(target.read_text()) if target.exists() else {}
        data[key] = value
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
