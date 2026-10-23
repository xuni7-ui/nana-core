import tempfile
from pathlib import Path
import pytest
@pytest.fixture
def owned_root():
    with tempfile.TemporaryDirectory(prefix='nana-cw-') as root:
        yield Path(root)
