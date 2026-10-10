import ast
from pathlib import Path
import pytest
from pydantic import ValidationError
from nana_core.clock import parse_utc
from nana_core.contracts import Observation, PlanProposal, StrategyRule

pytestmark = pytest.mark.s0


def test_strict_model_cannot_claim_success():
    with pytest.raises(ValidationError):
        PlanProposal.model_validate({"purpose": "help", "steps": [], "success": True})


def test_observation_does_not_coerce_identity():
    with pytest.raises(ValidationError):
        Observation(source_namespace="synthetic", object_id=3, raw_text="x")


def test_learning_cannot_expand_authority():
    with pytest.raises(ValidationError):
        StrategyRule.model_validate({"kind": "GRANT_PERMISSION", "capability": "public.send"})


@pytest.mark.parametrize("value", [None, "invalid", "2026-10-10T00:00:00"])
def test_invalid_or_naive_time_is_unknown(value):
    assert parse_utc(value) is None


def test_utc_offset_preserved():
    assert parse_utc("2026-10-10T08:00:00+08:00") == parse_utc("2026-10-10T00:00:00Z")


def test_no_host_or_production_imports():
    for path in Path("src/nana_core").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            assert not any(n.split(".")[0] in {"astrbot", "iris_memory", "bilibili_api", "openai"} for n in names)
