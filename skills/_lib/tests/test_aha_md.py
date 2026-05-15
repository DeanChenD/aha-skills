"""Unit tests for skills/_lib/aha_md.py shared primitives."""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / "skills" / "_lib" / "aha_md.py"

SPEC = importlib.util.spec_from_file_location("aha_md", LIB_PATH)
aha_md = importlib.util.module_from_spec(SPEC)
sys.modules["aha_md"] = aha_md
SPEC.loader.exec_module(aha_md)


class SanitizeSingleLineTest(unittest.TestCase):
    def test_none_passthrough(self):
        self.assertIsNone(aha_md.sanitize_single_line(None))

    def test_no_newline_unchanged(self):
        self.assertEqual("hello world", aha_md.sanitize_single_line("hello world"))

    def test_lf_replaced(self):
        result = aha_md.sanitize_single_line("foo\nbar")
        self.assertNotIn("\n", result)
        self.assertIn("↵", result)

    def test_crlf_replaced(self):
        result = aha_md.sanitize_single_line("foo\r\nbar")
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)

    def test_lone_cr_replaced(self):
        result = aha_md.sanitize_single_line("foo\rbar")
        self.assertNotIn("\r", result)

    def test_non_string_coerced(self):
        result = aha_md.sanitize_single_line(42)
        self.assertEqual("42", result)


class SetMetaInjectionTest(unittest.TestCase):
    def test_set_meta_with_newline_keeps_single_line(self):
        lines = ["status: active", "tags: []"]
        # Attempt to inject `status: dropped` via newline in value
        aha_md.set_meta(lines, "primary_category", "innocent\nstatus: dropped")
        # frontmatter must remain three lines (status, tags, new primary_category)
        self.assertEqual(3, len(lines))
        # status is still active — injection failed
        self.assertEqual("status: active", lines[0])
        # category line contains the marker, no literal newline
        cat_line = next(line for line in lines if line.startswith("primary_category:"))
        self.assertNotIn("\n", cat_line)
        self.assertIn("↵", cat_line)

    def test_set_meta_replace_existing_with_newline(self):
        lines = ["status: active", "primary_category: old"]
        aha_md.set_meta(lines, "primary_category", "x\ny")
        self.assertEqual(2, len(lines))
        self.assertNotIn("\n", lines[1])


class AppendToSectionInjectionTest(unittest.TestCase):
    def test_append_with_newline_does_not_split_section(self):
        body = "## Notes\n\n- existing note\n"
        # Attempt to inject a fake section heading
        body2 = aha_md.append_to_section(
            body, "Notes", "- 2026-05-15: foo\n## Raw Idea\nFAKE"
        )
        # No additional `\n## ` introduced beyond the original section marker
        # (i.e. the new appended line is single-line)
        appended_lines = [line for line in body2.splitlines() if "FAKE" in line]
        self.assertEqual(1, len(appended_lines))
        self.assertNotIn("\n## Raw Idea", body2)
        # The original Notes section still resolves correctly
        self.assertIn("↵", appended_lines[0])

    def test_append_normal_text_unchanged(self):
        body = "## Notes\n\n- existing\n"
        body2 = aha_md.append_to_section(body, "Notes", "- 2026-05-15: clean")
        self.assertIn("- 2026-05-15: clean", body2)
        self.assertNotIn("↵", body2)


if __name__ == "__main__":
    unittest.main()
