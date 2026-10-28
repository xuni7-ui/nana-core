import json
import pytest
from tools.nana_first_life_unified_release.memory_retention import sample, growth
from nana_core.life.control import dispatch
from nana_core.life.durability import StorageGuard
from tests.cloud_life.conftest import initialize
from nana_core.life.application import LifeApplication


def test_sample_uses_existing_projection_without_mutating_history(tmp_path):
    home = tmp_path / "life"
    initialize(home, max_autonomous_materials=0)
    with LifeApplication(home) as app:
        app.pause()
        StorageGuard(app).observe(force=True)
        before = app.runtime.store.db.execute("SELECT count(*) FROM events").fetchone()[0]
        transport = lambda home, data: {"ok": True, "result": dispatch(app, data)}
        first = sample(home, transport=transport)
        second = sample(home, transport=transport)
        assert first["guard_status"] == "OBSERVING"
        assert first["storage"]["family_bytes"] > 0
        assert first["accurate_recall"] == "NOT_RUN"
        assert "event_kinds" not in json.dumps(first)
        assert app.runtime.store.db.execute("SELECT count(*) FROM events").fetchone()[0] == before
        assert growth(first, second)["elapsed_us"] > 0
        with pytest.raises(ValueError, match="SUBJECT_BINDING_CHANGED"):
            growth(first, {**second, "subject_binding": {}})
        with pytest.raises(ValueError, match="NONPOSITIVE"):
            growth(first, first)
