"""Explicit branch fixture for isolated developer-only preflight unit tests.

The real First-Life entry remains pinned to its original branch. These tests use
fresh synthetic homes on an independent development worktree, so select its exact
branch as the test policy rather than changing the tool's default or bypassing
the branch comparison. No dispatch authorization is created.
"""

import subprocess

import pytest

from tools.nana_first_life_integration import dev


@pytest.fixture
def approved_dev_branch(monkeypatch):
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=dev.REPO, text=True
    ).strip()
    if not branch.startswith("dev/nana-core-"):
        raise RuntimeError("SYNTHETIC_PREFLIGHT_REQUIRES_DEVELOPMENT_BRANCH")
    monkeypatch.setattr(dev, "BRANCH", branch)
    return branch
