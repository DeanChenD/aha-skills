#!/usr/bin/env python3
"""Run the full pytest suite for skills/."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    return subprocess.call(
        [sys.executable, "-m", "pytest", "skills", "-v", *sys.argv[1:]],
        cwd=ROOT,
    )


if __name__ == "__main__":
    sys.exit(main())
