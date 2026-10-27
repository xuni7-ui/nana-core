"""Bounded offline legacy hash planning, no private DB reader or import command.

Accept only explicit existing exporter hash-only envelopes. A plan is linked to
one supplied canonical identity/lineage but creates no identity, memory or Grant.
"""

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from nana_core.life.live_api.adapters import reconcile_legacy
from nana_core.life.live_api.contracts import Binding
from nana_core.continuity.privacy import _json_object


def prepare(bundles, binding):
    binding = Binding.model_validate(binding)
    result = reconcile_legacy(bundles)
    hashes = [b["manifest_hash"] for b in bundles]
    value = {
        "schema_version": 1,
        "mode": "HASH_ONLY_ISOLATED_REVIEW_NOT_IMPORT",
        "subject_id": binding.subject_id,
        "lineage_binding": binding.lineage_binding,
        "input_manifest_hashes": hashes,
        "reconciliation": result,
        "rollback": "DISCARD_PLAN_NO_SUBJECT_WRITES",
        "private_import_authorized": False,
        "live_experience_created": False,
    }
    value["plan_digest"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return value


def read_explicit(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise ValueError("REGULAR_FILE_REQUIRED")
        raw = f.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("LEGACY_INPUT_BOUND")
    return json.loads(raw, object_pairs_hook=_json_object)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundles", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = prepare(read_explicit(a.bundles), read_explicit(a.binding))
        fd = os.open(a.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(result, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        print(json.dumps({"state": "BLOCKED_LEGACY_PLAN", "imported": False}))
        raise SystemExit(2) from None
    print(
        json.dumps(
            {"state": result["reconciliation"]["state"], "plan_digest": result["plan_digest"], "imported": False}
        )
    )


if __name__ == "__main__":
    main()
