"""Boundary tests, not substitutes for the cloud's original thirteen predicates."""

import importlib.util
from pathlib import Path
import hashlib
import pytest

ROOT = Path(__file__).resolve().parents[2] / "tools/nana_first_life_unified_release"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode", ["dry-run", "verify-only"])
def test_exactly_one_check_flag(mode):
    result = load("container_check").normalize_args(["--plan", "/explicit.json", "--dry-run", "--verify-only"], mode)
    assert result == ["--plan", "/explicit.json", "--" + mode]


@pytest.mark.parametrize("args", [["--execute"], ["--activate"], ["--dry-run=true"]])
def test_effect_flags_refused(args):
    with pytest.raises(ValueError):
        load("container_check").normalize_args(args, "dry-run")


def test_host_command_uses_private_container_python_and_read_only_original(tmp_path):
    script = tmp_path / "original.py"
    script.write_text('print("synthetic checker")')
    args = load("operator_check").command(
        "sha256:" + "a" * 64,
        "b" * 40,
        "dry-run",
        [str(tmp_path)],
        str(script),
        hashlib.sha256(script.read_bytes()).hexdigest(),
        ["--dry-run", "--verify-only"],
    )
    assert "--read-only" in args and args[args.index("--user") + 1] == "999:999"
    assert args[args.index("--entrypoint") + 1].endswith("/" + "b" * 40 + "/.venv/bin/python")
    assert all("readonly" in args[i + 1] for i, x in enumerate(args) if x == "--mount")
    with pytest.raises(ValueError):
        load("operator_check").command("latest", "b" * 40, "abi", [])
    with pytest.raises(ValueError):
        load("operator_check").command("sha256:" + "a" * 64, "b" * 40, "abi", ["/"])


def test_literal_operator_patch_is_digest_bound_and_keeps_original_approval_arguments():
    module = load("patch_operator_flags")
    source = b'cmd = [python, script, "--plan", plan, "--approval", approval, "--dry-run", "--verify-only"]\n'
    result = module.patch(source, hashlib.sha256(source).hexdigest())
    assert b"--verify-only" not in result and b"--dry-run" in result and b"approval" in result and b"--plan" in result
    with pytest.raises(ValueError):
        module.patch(source, "0" * 64)
    with pytest.raises(ValueError):
        module.patch(b"cmd=[]", hashlib.sha256(b"cmd=[]").hexdigest())
