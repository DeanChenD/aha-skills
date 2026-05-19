import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path
