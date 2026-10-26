"""Explain both plan digests using the existing Core DTO; never create a Subject."""

import argparse
import hashlib
import json
from pathlib import Path


def binding(path):
    from nana_core.life.live_api.canonical import CanonicalPlan

    raw = Path(path).read_bytes()
    plan = CanonicalPlan.model_validate_json(raw)
    return {
        "schema_version": 1,
        "plan_file_sha256": hashlib.sha256(raw).hexdigest(),
        "plan_dto_sha256": hashlib.sha256(plan.model_dump_json().encode()).hexdigest(),
        "file_hash_format": "EXACT_UTF8_FILE_BYTES_INCLUDING_WHITESPACE_AND_FINAL_NEWLINE",
        "dto_hash_format": "EXISTING_CORE_CanonicalPlan.model_dump_json_UTF8_V1",
        "genesis_approval_plan_digest_uses": "plan_dto_sha256",
        "inventory_digest": plan.inventory_digest,
        "state": "PREPARED_ONLY_GENESIS_DEFERRED",
        "approved": False,
        "subject_created": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    print(json.dumps(binding(p.parse_args().plan), indent=2))
