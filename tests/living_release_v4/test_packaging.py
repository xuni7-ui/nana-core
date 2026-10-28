from pathlib import Path

import pytest

from tools.nana_living_release_v4.compact_venv import compact


def test_image_compaction_preserves_the_actual_interpreter_and_rejects_substitution(tmp_path):
    binary = tmp_path / "pinned/.venv/bin/python3.12"
    binary.parent.mkdir(parents=True)
    original = b"TEST_ONLY_NOT_SECRET_IDENTICAL_BINARY"
    for name in ("python", "python3", "python3.12"):
        binary.with_name(name).write_bytes(original)
    assert compact(tmp_path) == 2 * len(original)
    assert compact(tmp_path) == 0
    for name in ("python", "python3"):
        alias = binary.with_name(name)
        assert alias.readlink() == Path("python3.12") and alias.read_bytes() == original
    alias.unlink()
    alias.write_bytes(b"DIFFERENT_INTERPRETER")
    with pytest.raises(ValueError, match="INTERPRETER_ALIAS_CONTENT_MISMATCH"):
        compact(tmp_path)
    assert binary.read_bytes() == original


def test_deploy_wrapper_preserves_stdin_and_checks_tools_before_execution(tmp_path):
    import hashlib
    import json
    import subprocess
    from tools.nana_living_release_v4.package_handoff import WRAPPER

    tool = tmp_path / "tools/deploy.py"
    tool.parent.mkdir()
    tool.write_text("import sys,json;print(json.dumps({'stdin_preserved':sys.stdin.read()=='TEST_ONLY_NOT_SECRET_PIPE'}))")
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(json.dumps({"files": {"tools/deploy.py": {"sha256": hashlib.sha256(tool.read_bytes()).hexdigest()}}}))
    entry = tmp_path / "deploy.sh"
    entry.write_text(WRAPPER.replace("__DIGEST__", hashlib.sha256(manifest.read_bytes()).hexdigest()))
    entry.chmod(0o700)
    result = subprocess.run([str(entry), "--rollback", "--password-fd", "0"],
                            input="TEST_ONLY_NOT_SECRET_PIPE", text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)["stdin_preserved"] is True
    tool.write_text("raise RuntimeError('THIS_TOOL_MUST_NOT_RUN')")
    refused = subprocess.run([str(entry), "--check"], text=True, capture_output=True)
    assert refused.returncode and "RELEASE_FILE_DIGEST_MISMATCH" in refused.stderr
    assert "THIS_TOOL_MUST_NOT_RUN" not in refused.stderr


def test_rollback_never_switches_after_an_unverified_backup(monkeypatch):
    import os
    from types import SimpleNamespace
    from tools.nana_living_release_v4 import switch_release

    calls = []

    class Portal:
        def __init__(self, *args, **kwargs):
            self.jar = SimpleNamespace(clear=lambda: None)
        def verify_endpoint(self):
            pass
        def call(self, path, method, body):
            calls.append((path, method, body.get("operation") if body else None))
            if path == "session":
                return {"subject_id": "DEV_SUBJECT", "data": {"csrf": "TEST_ONLY_NOT_SECRET"}}
            if path == "bootstrap":
                return {"subject_id": "DEV_SUBJECT", "revision": 1, "run_generation": "dev", "owner_epoch": 1,
                        "data": {"roles": ["HOST_ADMIN"]}}
            if path == "host/confirmations":
                return {"data": {"confirmation_id": "dev"}}
            return {"subject_id": "DEV_SUBJECT", "data": {"state": "UNKNOWN", "receipt_id": "original-backup"}}

    monkeypatch.setattr(switch_release, "Portal", Portal)
    fd, writer = os.pipe()
    os.write(writer, b"TEST_ONLY_NOT_SECRET")
    os.close(writer)
    try:
        result = switch_release.switch("https://example.test", "DEV_SUBJECT", "older", fd, operation="ROLLBACK")
    finally:
        os.close(fd)
    assert result["state"] == "BACKUP_NOT_VERIFIED_NO_SWITCH" and result["no_retry"]
    assert [c[2] for c in calls if c[0] == "host/operations"] == ["BACKUP"]


def test_dispatched_switch_timeout_keeps_original_key_and_unknown():
    from tools.nana_living_release_v4.switch_release import one_operation

    calls = []
    class Portal:
        def call(self, path, method, body):
            calls.append(body["client_request_id"])
            raise TimeoutError()

    result = one_operation(Portal(), "DEV_SUBJECT", {"operation": "ROLLBACK", "client_request_id": "original-key"})
    assert calls == ["original-key"]
    assert result["state"] == "UNKNOWN" and result["no_retry"]
    assert result["client_request_id"] == "original-key"
