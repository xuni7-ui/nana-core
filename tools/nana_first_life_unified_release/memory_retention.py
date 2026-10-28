"""One-shot numeric storage evidence via original owner IPC, never a memory store.

No init, plaintext memory, SQL writes, checkpoint, pruning, Provider calls or
second Runtime. Run as the existing owner, in its execution namespace. Reports
are host-local observations; byte growth is not accurate personal recall.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time


def growth(previous, current):
    if previous["subject_binding"] != current["subject_binding"]:
        raise ValueError("SUBJECT_BINDING_CHANGED")
    elapsed = current["observed_at_us"] - previous["observed_at_us"]
    if elapsed <= 0:
        raise ValueError("NONPOSITIVE_OBSERVATION_INTERVAL")
    out = {"elapsed_us": elapsed, "basis": "TWO_REAL_OBSERVATIONS_NOT_FORECAST"}
    for key in ("logical_database_bytes", "privacy_anchor_bytes", "family_bytes"):
        delta = current["storage"][key] - previous["storage"][key]
        out[key] = {"net_delta_bytes": delta, "net_bytes_per_hour": delta * 3_600_000_000 / elapsed}
    return out


def sample(home, *, transport=None):
    from nana_core.life.control import request
    from nana_core.life.live_api.supervisor import existing_identity
    from nana_core.life.durability import read_window
    from nana_core.life.config import load_config

    home = Path(home).absolute()
    identity, lineage, _ = existing_identity(home)
    response = (transport or request)(home, {"operation": "view", "view": "storage"})
    if not response.get("ok"):
        raise ValueError("OWNER_STORAGE_OBSERVATION_UNAVAILABLE")
    if existing_identity(home)[:2] != (identity, lineage):
        raise ValueError("SUBJECT_CHANGED_DURING_OBSERVATION")
    raw = response["result"]
    keys = ("logical_database_bytes", "reusable_page_bytes", "privacy_anchor_bytes", "family_bytes")
    storage = {key: raw[key] for key in keys}
    if any(type(v) is not int or v < 0 for v in storage.values()):
        raise ValueError("INVALID_STORAGE_OBSERVATION")
    storage["physical_file_bytes"] = {
        k: raw["physical_file_bytes"][k]
        for k in ("database", "-wal", "-shm", ".privacy.json")
        if k in raw["physical_file_bytes"]
    }
    cfg = load_config(home)
    window = read_window(home / "storage-monitor.json")
    return {
        "schema_version": 1,
        "kind": "HOST_LOCAL_NUMERIC_EVIDENCE_NOT_SUBJECT_MEMORY",
        "subject_binding": {"identity_id": identity, "lineage_binding": lineage},
        "observed_at_us": time.time_ns() // 1000,
        "storage": storage,
        "guard_status": window.status if window else "NOT_OBSERVED",
        "limits": {
            k: getattr(cfg, k)
            for k in (
                "max_state_mb",
                "max_state_growth_mb_per_hour",
                "min_free_disk_mb",
                "storage_growth_grace_seconds",
                "storage_growth_window_seconds",
            )
        },
        "free_disk_bytes": __import__("shutil").disk_usage(home).free,
        "accurate_recall": "NOT_RUN",
        "human_long_term_companionship": "NOT_RUN",
        "automatic_pruning": False,
        "provider_calls": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core-root", required=True, type=Path)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--previous", type=Path)
    a = p.parse_args()
    root = a.core_root.absolute()
    if root.resolve() != root or not (root / "src/nana_core/life/durability.py").is_file():
        p.error("explicit existing Core release required")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / "src"))
    value = sample(a.home)
    if a.previous:
        if a.previous.is_symlink() or a.previous.stat().st_size > 16384:
            raise ValueError("BOUNDED_PREVIOUS_SAMPLE_REQUIRED")
        value["growth"] = growth(json.loads(a.previous.read_text()), value)
    fd = os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print("NUMERIC_OBSERVATION_SAVED; RECALL_NOT_REVIEWED")


if __name__ == "__main__":
    main()
