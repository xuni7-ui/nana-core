import json
import pytest
from nana_core.experiment import run_experiment

pytestmark = [pytest.mark.s4, pytest.mark.acceptance]


@pytest.mark.parametrize("seed", [1, 8, 23])
def test_E11_E13_E14_process_restart_and_behavioral_ablation(tmp_path, seed):
    manifest = run_experiment(tmp_path / "experiment", seed=seed)
    assert all(manifest["assertions"].values())
    assert manifest["crash_recovery_passed"]
    report = json.loads((tmp_path / "experiment" / "learning_ablation.json").read_text())
    # Locator comes from the actual external source, varying across unseen fixture data.
    assert report["with_experience"]["card"]["locator"] == f"page {seed * 7 + 3}, paragraph {seed % 4 + 1}"
    assert report["without_experience"]["card"]["locator"] is None
    assert report["with_experience"]["counts"]["locate_calls"] == 1
    assert report["without_experience"]["counts"]["locate_calls"] == 0


@pytest.mark.skip(reason="E12 real dual-model semantics belongs to S5, explicitly excluded this turn")
def test_E12_real_model_migration():
    raise AssertionError("Do not turn this into a fixture-only pass")
