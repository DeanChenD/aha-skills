#!/usr/bin/env python3
"""Run the full aha-skills unittest suite from the repository root."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_DIRS = [
    ROOT / "skills" / "_lib" / "tests",
    ROOT / "skills" / "idea" / "tests",
    ROOT / "skills" / "dao" / "tests",
    ROOT / "skills" / "daily" / "tests",
    ROOT / "skills" / "reflect" / "tests",
]


def main():
    verbosity = 2 if "-v" in sys.argv or "--verbose" in sys.argv else 1
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_dir in TEST_DIRS:
        suite.addTests(loader.discover(str(test_dir), pattern="test_*.py"))

    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
