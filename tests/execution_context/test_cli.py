"""Execute the real operator CLI so stdlib/module shadowing cannot go unnoticed."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_explicit_local_cli_and_unbound_host_never_write(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    command = [sys.executable, "-B", str(repo / "tools/nana_execution_context/diagnose.py"),
               "--local-target", "core-container", "--path", str(tmp_path)]
    env = {"PATH": os.defpath, "PYTHONPATH": str(repo / "src")}
    local = subprocess.run(command, env=env, capture_output=True, text=True, timeout=5)
    assert local.returncode == 0, local.stderr
    result = json.loads(local.stdout)
    assert result["target_id"] == "core-container" and result["observation"]["actual_path"] == str(tmp_path)
    assert result["source_context"]["scope"] == "UNKNOWN" and result["execution_authority"] is False
    host = subprocess.run([*command, "--target", "host"], env=env, capture_output=True, text=True, timeout=5)
    assert host.returncode == 2
    rejected = json.loads(host.stdout)
    assert rejected["code"] == "EXECUTION_TARGET_UNBOUND"
    assert rejected["source_context"]["target_id"] == "core-container"
    assert rejected["target_id"] == "host" and rejected["requested_path"] == str(tmp_path)
    assert rejected["actual_path"] is rejected["target_context_id"] is rejected["channel_id"] is None
    assert rejected["result"] == "NO_TARGET_CHECK_PERFORMED" and rejected["observed_at_us"] > 0
    assert not list(tmp_path.iterdir())
