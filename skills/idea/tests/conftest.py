import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "idea.py"


@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def run(aha_home):
    def _run(*args, expect_code: int = 0):
        env = {**os.environ, "AHA_HOME": str(aha_home)}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == expect_code, (
            f"exit={proc.returncode} expected={expect_code}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
        return proc
    return _run
