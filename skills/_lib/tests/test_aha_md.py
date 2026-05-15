"""Unit tests for skills/_lib/aha_md.py shared primitives."""

import importlib.util
import os
import sys
import tempfile
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


class SectionFinderTest(unittest.TestCase):
    def test_section_inside_code_fence_not_a_real_heading(self):
        body = (
            "## Raw\n\n"
            "user typed:\n"
            "```\n"
            "## Notes\n"
            "this looks like a heading but is in a code block\n"
            "```\n\n"
            "## Notes\n\n"
            "real notes here\n"
        )
        # find the real ## Notes (the second one), not the fenced one
        offsets = aha_md._section_offsets(body)
        headings = [h for _, _, h in offsets]
        self.assertEqual(["Raw", "Notes"], headings)

    def test_h3_not_treated_as_h2(self):
        body = "## Real\ncontent\n### Subheading\nstuff\n"
        offsets = aha_md._section_offsets(body)
        self.assertEqual(["Real"], [h for _, _, h in offsets])

    def test_append_skips_pseudo_heading_in_raw(self):
        body = (
            "## Raw\n\n"
            "## Notes\n"  # pseudo-heading inside Raw — line-aware finder still
            "user accidentally typed this\n\n"
            "## Notes\n\n"
            "real\n"
        )
        # Two real Notes headings; finder picks the first match.
        # NOTE: this test documents that without escape_pseudo_h2 at write time,
        # bare "## Notes" in raw IS structurally a heading. Capture-time escape
        # is the defense against that — see test_capture_escapes_pseudo_h2.
        offsets = aha_md._section_offsets(body)
        self.assertEqual(["Raw", "Notes", "Notes"], [h for _, _, h in offsets])

    def test_escape_pseudo_h2_neutralizes_h2(self):
        text = "line one\n## Notes\nline three\n### still h3\n"
        out = aha_md.escape_pseudo_h2(text)
        # h2 line escaped, h3 untouched
        self.assertIn("\\## Notes", out)
        self.assertNotIn("\n## Notes", out)
        self.assertIn("### still h3", out)

    def test_read_section_returns_only_target_section_content(self):
        body = (
            "## A\n\nalpha\n\n"
            "## B\n\nbeta\n\n"
            "## C\n\ngamma\n"
        )
        self.assertEqual("alpha", aha_md.read_section(body, "A"))
        self.assertEqual("beta", aha_md.read_section(body, "B"))
        self.assertEqual("gamma", aha_md.read_section(body, "C"))

    def test_replace_section_preserves_neighbors(self):
        body = "## A\n\nalpha\n\n## B\n\nbeta\n"
        out = aha_md.replace_section(body, "A", "ALPHA-NEW")
        self.assertIn("ALPHA-NEW", out)
        self.assertIn("## B", out)
        self.assertIn("beta", out)
        self.assertNotIn("alpha", out)

    def test_replace_section_escapes_h2_in_new_content(self):
        body = "## Refined\n\nold\n\n## Notes\n\nstuff\n"
        # Caller passes new content that contains a literal `## Notes` line
        out = aha_md.replace_section(body, "Refined", "para\n## Notes\nfaux")
        # The new content's pseudo-heading is escaped — Notes heading count == 1
        notes_heads = [
            ln for ln in out.splitlines() if ln.strip() == "## Notes"
        ]
        self.assertEqual(1, len(notes_heads))


class AssertWorkspacePathTest(unittest.TestCase):
    def _with_cwd(self, new_cwd):
        self._original_cwd = os.getcwd()
        os.chdir(new_cwd)

    def tearDown(self):
        if hasattr(self, "_original_cwd"):
            os.chdir(self._original_cwd)

    def test_path_inside_workspace_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_cwd(tmp)
            target = Path(tmp) / "aha-workspace" / "dao" / "dao-md" / "x.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
            # Should not raise
            aha_md.assert_workspace_path(target, "dao")

    def test_path_in_wrong_skill_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_cwd(tmp)
            target = Path(tmp) / "aha-workspace" / "idea" / "idea-md" / "x.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                aha_md.assert_workspace_path(target, "dao")
            self.assertIn("outside skill workspace", str(cm.exception))

    def test_arbitrary_path_outside_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_cwd(tmp)
            outside = Path(tmp) / "evil.md"
            outside.write_text("attacker", encoding="utf-8")
            with self.assertRaises(SystemExit):
                aha_md.assert_workspace_path(outside, "daily")

    def test_relative_path_resolved_against_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_cwd(tmp)
            target = Path("aha-workspace") / "daily" / "tasks" / "task-x.md"
            (Path(tmp) / target.parent).mkdir(parents=True, exist_ok=True)
            (Path(tmp) / target).write_text("ok", encoding="utf-8")
            # Relative path must still be accepted when it resolves under workspace
            aha_md.assert_workspace_path(target, "daily")


class SchemaVersionTest(unittest.TestCase):
    def test_assert_v1_passes(self):
        aha_md.assert_schema_version({"schema_version": "1"})

    def test_assert_unsupported_raises(self):
        with self.assertRaises(SystemExit) as cm:
            aha_md.assert_schema_version({"schema_version": "999"})
        self.assertIn("Unsupported schema_version", str(cm.exception))

    def test_assert_unparseable_raises(self):
        with self.assertRaises(SystemExit) as cm:
            aha_md.assert_schema_version({"schema_version": "abc"})
        self.assertIn("Unparseable schema_version", str(cm.exception))

    def test_assert_missing_warns_but_passes(self):
        # No raise — legacy file path is tolerated with a stderr warning
        aha_md.assert_schema_version({})

    def test_load_record_strict_on_unsupported_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.md"
            path.write_text(
                "---\nid: x\nschema_version: 99\n---\n# X\n", encoding="utf-8"
            )
            with self.assertRaises(SystemExit):
                aha_md.load_record(path)

    def test_load_record_accepts_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.md"
            path.write_text(
                "---\nid: x\nschema_version: 1\n---\n# X\n", encoding="utf-8"
            )
            lines, meta, body = aha_md.load_record(path)
            self.assertEqual("1", meta["schema_version"])


class AtomicWriteTest(unittest.TestCase):
    def test_atomic_write_replaces_completely(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.md"
            aha_md.atomic_write(path, "first\n")
            aha_md.atomic_write(path, "second\n")
            self.assertEqual("second\n", path.read_text(encoding="utf-8"))

    def test_atomic_write_no_tmp_leftover(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.md"
            aha_md.atomic_write(path, "ok\n")
            siblings = [p.name for p in path.parent.iterdir()]
            # Only the final file (and any lock files), no `.x.md.tmp.*`
            tmp_files = [n for n in siblings if ".tmp." in n]
            self.assertEqual([], tmp_files)


class LockedRecordConcurrencyTest(unittest.TestCase):
    """Two threads simultaneously appending to the same daily log file —
    without locking, they race and one entry is silently dropped. With
    locking, both entries land."""

    def test_concurrent_log_appends_both_entries_land(self):
        import subprocess
        import threading

        REPO = Path(__file__).resolve().parents[3]
        DAILY_SCRIPT = REPO / "skills" / "daily" / "scripts" / "daily_md.py"

        with tempfile.TemporaryDirectory() as tmp:
            errors = []

            def append_log(text, time_str):
                try:
                    subprocess.run(
                        [sys.executable, str(DAILY_SCRIPT), "log",
                         "--text", text, "--time", time_str,
                         "--title", text],
                        check=True, capture_output=True, text=True, cwd=tmp,
                    )
                except subprocess.CalledProcessError as e:
                    errors.append((e.returncode, e.stderr))

            t1 = threading.Thread(target=append_log, args=("entry-A", "08:00"))
            t2 = threading.Thread(target=append_log, args=("entry-B", "09:00"))
            t1.start(); t2.start()
            t1.join(); t2.join()

            self.assertEqual([], errors)

            log_dir = Path(tmp) / "aha-workspace" / "daily" / "logs"
            log_files = list(log_dir.glob("log-*.md"))
            self.assertEqual(1, len(log_files))
            content = log_files[0].read_text(encoding="utf-8")
            self.assertIn("entry-A", content)
            self.assertIn("entry-B", content)
            # entry_count must reflect both appends (not 1 due to lost write)
            self.assertIn("entry_count: 2", content)


if __name__ == "__main__":
    unittest.main()
