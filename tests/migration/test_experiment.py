import pytest
from nana_core.migration.experiment import run_experiment

pytestmark = pytest.mark.s6


def test_complete_synthetic_migration_across_processes(tmp_path):
    report = run_experiment(tmp_path / "experiment")
    assert all(report["checks"].values())
    assert report["crash"]["returncode"] == -9
    assert report["real_model_calls"] == 0 and report["E12"] == "NOT_RUN"
    assert report["world_counts"]["effects"] == 3
    assert report["owner_after"]["epoch"] == 2
