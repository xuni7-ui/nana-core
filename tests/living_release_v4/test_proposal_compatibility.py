import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# The handoff copies this original installer beside operator_stage.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/nana_first_life_android_v2"))
from tools.nana_living_release_v4 import deploy, operator_stage, proposal


SOURCE = "b" * 40
IMAGE = "sha256:" + "c" * 64
REAL_RUN = subprocess.run


def sealed_release(root, alias, source):
    entry = root / "src/nana_core/life/__main__.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("# Synthetic runtime; never launched.\n")
    python = root / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("# Synthetic interpreter; never launched.\n")
    manifest = root / "runtime.json"
    manifest.write_text(json.dumps({"source_commit": source}))
    sums = root / "SHA256SUMS"
    sums.write_text("".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path.relative_to(root)) + "\n"
                            for path in (entry, python, manifest)))
    return {"release_id": alias, "source_commit": source, "root": str(root), "python": str(python),
            "schema_version": 13, "plan_contract": "PRECISION_V2",
            "integrity_digest": hashlib.sha256(sums.read_bytes()).hexdigest()}


@pytest.fixture
def host(tmp_path, monkeypatch):
    # Execute the production image-side script with the real SDK DTO and Release
    # validator. Only replace the unavailable image interpreter/import prefix.
    repository = Path(__file__).resolve().parents[2]

    def local_sdk(args, **kwargs):
        assert args[1:4] == ["-I", "-B", "-c"]
        # The fixture belongs to this test process; production pins BFF UID999.
        assert args[-1] == "999"
        return REAL_RUN([sys.executable, *args[1:5], str(repository), *args[6:-1], str(os.getuid())], **kwargs)

    monkeypatch.setattr(proposal.subprocess, "run", local_sdk)
    root = tmp_path / "host"
    state_root = root / "data/host"
    state_root.mkdir(parents=True, mode=0o700)
    release = sealed_release(tmp_path / "image/active", "actual-host-alias", "a" * 40)
    configuration = {"home": str(root / "data/home"), "host_state": str(state_root),
                     "binding": {"subject_id": "TEST_SUBJECT", "lineage_binding": "d" * 64},
                     "releases": [release], "active_release": release["release_id"],
                     "public_origin": "https://example.test", "web_root": str(tmp_path / "web")}
    path = state_root / "host.json"
    path.write_text(json.dumps(configuration))
    path.chmod(0o600)
    return root, configuration, path


def persist(root, alias):
    path = root / "data/host/supervisor.json"
    path.write_text(json.dumps({"schema_version": 1, "revision": 7, "active_release": alias,
                                "stop_latch": True, "last_state": "STOP_LATCHED"}))
    path.chmod(0o600)
    return path


@pytest.mark.parametrize("failure,code", [("missing", "RELEASE_PATH_DENIED"),
                                           ("integrity", "RELEASE_INTEGRITY_MISMATCH"),
                                           ("schema", "INCOMPATIBLE_RELEASE_SCHEMA"),
                                           ("plan", "INCOMPATIBLE_PLAN_CONTRACT")])
def test_configured_active_must_be_qualified_in_candidate_image(host, failure, code):
    root, configuration, path = host
    active = configuration["releases"][0]
    if failure == "missing":
        shutil.rmtree(active["root"])
    elif failure == "integrity":
        Path(active["python"]).write_text("modified sealed file")
    elif failure == "schema":
        active["schema_version"] = 12
    else:
        active["plan_contract"] = "UNKNOWN_PLAN"
    path.write_text(json.dumps(configuration))
    before = path.read_bytes()
    result = proposal.inspect_existing(root, SOURCE)
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == code
    assert result["context"]["origin"] == "configured_active_release"
    assert result["context"]["release_id"] == "actual-host-alias"
    assert result["context"]["source_commit"] == "a" * 40
    assert result["context"]["root"] == active["root"]
    assert path.read_bytes() == before
    assert not (root / "data/host/supervisor.json").exists()


def test_persisted_active_is_checked_separately_and_unknown_alias_is_recoverable(host, tmp_path):
    root, configuration, path = host
    previous = sealed_release(tmp_path / "image/previous", "previous-active", "e" * 40)
    configuration["releases"].append(previous)
    path.write_text(json.dumps(configuration))
    state = persist(root, previous["release_id"])
    before = state.read_bytes()
    shutil.rmtree(previous["root"])
    result = proposal.inspect_existing(root, SOURCE)
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == "RELEASE_PATH_DENIED"
    assert result["context"]["origin"] == "persisted_active_release"
    assert result["context"]["release_id"] == "previous-active"
    assert result["context"]["source_commit"] == "e" * 40
    assert state.read_bytes() == before
    persist(root, "unregistered-host-alias")
    before = state.read_bytes()
    unknown = proposal.inspect_existing(root, SOURCE)
    assert unknown["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert unknown["code"] == "ACTIVE_RELEASE_NOT_REGISTERED"
    assert unknown["context"]["origin"] == "persisted_active_release"
    assert unknown["context"]["release_id"] == "unregistered-host-alias"
    assert state.read_bytes() == before


def test_available_configured_and_persisted_active_pass_without_creating_locks(host, tmp_path):
    root, configuration, path = host
    previous = sealed_release(tmp_path / "image/previous", "previous-active", "e" * 40)
    configuration["releases"].append(previous)
    path.write_text(json.dumps(configuration))
    state = persist(root, previous["release_id"])
    before = {file.name: file.read_bytes() for file in state.parent.iterdir()}
    result = proposal.inspect_existing(root, SOURCE)
    assert result["state"] == "ACTIVE_RELEASE_COMPATIBILITY_VERIFIED"
    assert result["configured_active_release"] == "actual-host-alias"
    assert result["persisted_active_release"] == "previous-active"
    assert {file.name: file.read_bytes() for file in state.parent.iterdir()} == before


def test_state_outside_explicit_bind_cannot_be_assumed_absent(host, tmp_path):
    root, configuration, path = host
    configuration["host_state"] = str(tmp_path / "not-mounted-state")
    path.write_text(json.dumps(configuration))
    result = proposal.inspect_existing(root, SOURCE)
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == "SUPERVISOR_STATE_NOT_VISIBLE_IN_HOST_BIND"


def test_nonregular_state_cannot_block_or_pass_preflight(host):
    root, _, _ = host
    state = root / "data/host/supervisor.json"
    os.mkfifo(state, mode=0o600)
    result = proposal.inspect_existing(root, SOURCE)
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == "HOST_METADATA_CORRUPT"


def test_host_configuration_must_belong_to_the_service_uid(host):
    root, configuration, _ = host
    checked = REAL_RUN([sys.executable, "-I", "-B", "-c", proposal.VALIDATE,
                        str(Path(__file__).resolve().parents[2]), SOURCE, str(root), str(os.getuid() + 1)],
                       input=json.dumps({"original": configuration, "candidate": configuration}),
                       text=True, capture_output=True, timeout=5)
    result = json.loads(checked.stdout)
    assert checked.returncode == 2
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == "PRIVATE_HOST_CONFIGURATION_REQUIRED"


@pytest.mark.parametrize("error,code", [(OSError("unavailable"), "CANDIDATE_SDK_PREFLIGHT_UNAVAILABLE"),
                                       (subprocess.TimeoutExpired("private command", 20), "HOST_PREFLIGHT_TIMED_OUT")])
def test_validator_failure_is_recoverable_without_returning_private_command(host, monkeypatch, error, code):
    root, _, _ = host

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(proposal.subprocess, "run", fail)
    result = proposal.inspect_existing(root, SOURCE)
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == code
    assert "private command" not in json.dumps(result)


def test_ready_receipt_cannot_bypass_active_preflight_and_fix_is_recoverable(host, monkeypatch):
    root, configuration, _ = host
    runtime = root / "slots" / SOURCE / "runtime"
    runtime.mkdir(parents=True)
    receipt = runtime.parent / "stage-receipt.json"
    receipt.write_text(json.dumps({"state": "READY_FOR_SWITCH", "source_commit": SOURCE, "image_id": IMAGE}))
    monkeypatch.setattr(operator_stage, "checked_inputs", lambda *args: (root, {"entries": {}}))
    monkeypatch.setattr(operator_stage, "verify_tree", lambda *args: [])
    persist(root, "unknown-active")
    before = receipt.read_bytes()
    for mode in ("check", "install", "commit"):
        blocked = operator_stage.run(mode, root, SOURCE, IMAGE, "unused", "unused")
        assert blocked["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
        assert blocked["code"] == "ACTIVE_RELEASE_NOT_REGISTERED"
        assert blocked["persistent_changes"] == 0
        assert receipt.read_bytes() == before
    persist(root, configuration["active_release"])
    ready = operator_stage.run("check", root, SOURCE, IMAGE, "unused", "unused")
    assert ready["state"] == "READY_FOR_SWITCH"
    assert ready["host_configuration_preflight"]["state"] == "ACTIVE_RELEASE_COMPATIBILITY_VERIFIED"
    assert receipt.read_bytes() == before


def test_no_existing_host_configuration_keeps_dev_ready(host, monkeypatch):
    root, _, path = host
    path.unlink()
    runtime = root / "slots" / SOURCE / "runtime"
    runtime.mkdir(parents=True)
    (runtime.parent / "stage-receipt.json").write_text(json.dumps(
        {"state": "RUNTIME_STAGED_VERIFY_REQUIRED", "source_commit": SOURCE, "image_id": IMAGE}))
    monkeypatch.setattr(operator_stage, "checked_inputs", lambda *args: (root, {"entries": {}}))
    monkeypatch.setattr(operator_stage, "verify_tree", lambda *args: [])
    result = operator_stage.run("commit", root, SOURCE, IMAGE, "unused", "unused")
    assert result["state"] == "READY_FOR_SWITCH"
    assert result["host_configuration_preflight"]["state"] == "NO_EXISTING_HOST_CONFIGURATION"
    assert not path.exists()
    assert not (root / "data/host/supervisor.json").exists()


def test_deploy_preserves_precise_review_result_if_host_changes_before_commit(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("operator_stage.py", "integrity.py", "install_runtime_tree.py", "proposal.py"):
        (tools / name).write_text("# TEST ONLY\n")
    for name in ("runtime-tree.json", "release.json"):
        (tmp_path / name).write_text("{}")
    review = {"state": "HOST_CONFIGURATION_REVIEW_REQUIRED", "code": "ACTIVE_RELEASE_NOT_REGISTERED",
              "context": {"origin": "persisted_active_release", "release_id": "changed-before-commit"},
              "persistent_changes": 0}

    class Docker:
        def image(self, image): return {"id":image,"architecture":"amd64","os":"linux","user":"999:999"}
        def version(self): return {"Version": "TEST_ONLY"}
        def create_check(self, *args, **kwargs): return "isolated-check"
        def verify_check(self, check): return {"exit_code": 0}
        def remove_check(self, check): pass
        def operator(self, image, root, mode, files, arguments):
            return review if mode == "commit" else {"state": "RUNTIME_STAGED_VERIFY_REQUIRED", "target": "/test/runtime"}

    result = deploy.prepare(Docker(), tmp_path,
                            {"image": {"id": IMAGE}, "source_commit": SOURCE, "runtime_manifest_sha256": "d" * 64},
                            "/test/host", "install")
    assert result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED"
    assert result["code"] == review["code"]
    assert result["context"] == review["context"]
