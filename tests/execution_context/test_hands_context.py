"""Original real local Hands remains the executor, with namespace-bound checks."""
import json
from pathlib import Path

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.port import OwnedApplicationPort


def test_original_hands_context_pin_prevents_namespace_substitution(tmp_path, monkeypatch):
    with OwnedApplication(tmp_path / "owned", tasks=(ApplicationTask(task_id="doc", kind="DOCUMENT", wanted="finite"),)) as host:
        port = OwnedApplicationPort("test-identity", host.target, host_enabled=True)
        view = port.execution_evidence()
        root = Path(host.target.workspace)
        assert view["directory_device"] == root.stat().st_dev
        assert view["source_context_id"] == view["target_context_id"]
        assert view["host_identity"] == "UNKNOWN" and view["execution_authority"] is False
        original = port._execution_probe.capture
        monkeypatch.setattr(port._execution_probe, "capture", lambda: original().model_copy(update={"context_id": "f" * 64}))
        with pytest.raises(CoreError, match="HANDS_EXECUTION_CONTEXT_CHANGED"):
            port.peek("doc")
        assert not json.loads((root / "application-state.json").read_text())["effects"]


def test_original_hands_peer_user_namespace_must_match(tmp_path, monkeypatch):
    import os
    with OwnedApplication(tmp_path / "owned", tasks=(ApplicationTask(task_id="doc", kind="DOCUMENT", wanted="finite"),)) as host:
        port = OwnedApplicationPort("test-identity", host.target, host_enabled=True)
        actual = os.readlink
        def different_peer(path):
            if str(path) == f"/proc/{host.target.pid}/ns/user":
                return "user:[999999999]"
            return actual(path)
        monkeypatch.setattr(os, "readlink", different_peer)
        with pytest.raises(CoreError, match="HANDS_TARGET_NAMESPACE_MISMATCH"):
            port.peek("doc")
