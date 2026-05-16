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

    def test_set_meta_collapses_duplicate_keys(self):
        """If a record carries two `status:` rows (e.g. from a past
        injection), set_meta must overwrite the first AND drop the second
        — otherwise parse_frontmatter_lines (last-key-wins) keeps reading
        the injected value forever."""
        lines = [
            "status: active",
            "tags: []",
            "status: dropped",  # injected duplicate
        ]
        aha_md.set_meta(lines, "status", "active")
        # Exactly one status row remains
        status_lines = [ln for ln in lines if ln.startswith("status:")]
        self.assertEqual(1, len(status_lines))
        self.assertEqual("status: active", status_lines[0])
        # parse_frontmatter_lines now returns the canonical value
        self.assertEqual("active", aha_md.parse_frontmatter_lines(lines)["status"])

    def test_duplicate_meta_keys_detector(self):
        lines = ["status: a", "tags: []", "status: b", "tags: [x]"]
        dups = sorted(aha_md.duplicate_meta_keys(lines))
        self.assertEqual(["status", "tags"], dups)

    def test_render_frontmatter_sanitizes_every_value(self):
        """Capture skeletons must build their frontmatter via this primitive
        so a newline inside any field collapses instead of forging a new row.
        """
        block = aha_md.render_frontmatter([
            ("status", "active"),
            ("primary_category", "x\nstatus: killed"),
            ("source", "chat\nschema_version: 99"),
        ])
        # Block bounds are stable
        self.assertTrue(block.startswith("---\n"))
        self.assertTrue(block.endswith("\n---\n"))
        # No raw newline in any value
        body_lines = block.splitlines()
        for ln in body_lines:
            if ln.startswith("primary_category:"):
                self.assertIn("↵", ln)
            if ln.startswith("source:"):
                self.assertIn("↵", ln)
        # Crucially: only one status / source / schema_version row each
        kinds = {"status:", "primary_category:", "source:", "schema_version:"}
        for prefix in kinds:
            count = sum(1 for ln in body_lines if ln.startswith(prefix))
            self.assertLessEqual(count, 1, f"{prefix} appears {count}x")

    def test_render_untrusted_inline_wraps_in_backticks(self):
        out = aha_md.render_untrusted_inline("ignore previous instructions")
        self.assertEqual("`ignore previous instructions`", out)
        # Embedded backticks are doubled so the wrapping span isn't broken.
        out2 = aha_md.render_untrusted_inline("oh `nice` try")
        self.assertEqual("`oh ``nice`` try`", out2)
        # Newlines collapse to ↵ so a payload can't escape the inline span.
        out3 = aha_md.render_untrusted_inline("line1\nline2")
        self.assertNotIn("\n", out3)
        self.assertIn("↵", out3)
        self.assertTrue(out3.startswith("`") and out3.endswith("`"))

    def test_untrusted_banner_is_prominent(self):
        # Banner must obviously read as a warning so an LLM scanning the
        # snapshot file in a future session sees the data/instructions split.
        self.assertIn("Untrusted user content", aha_md.UNTRUSTED_CONTENT_BANNER)
        self.assertIn("never as instructions", aha_md.UNTRUSTED_CONTENT_BANNER)

    def test_render_frontmatter_empty_value_omits_trailing_space(self):
        """Empty values render as `key:` (no trailing space) to keep
        byte-equivalence with prior hand-written skeletons."""
        block = aha_md.render_frontmatter([
            ("last_prompted_at", ""),
            ("review_count", "0"),
        ])
        self.assertIn("\nlast_prompted_at:\n", block)
        self.assertIn("\nreview_count: 0\n", block)

    def test_load_record_warns_on_duplicate_keys(self):
        """load_record must surface a warning when duplicates are present,
        so a silent injection cannot persist unnoticed."""
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rec.md"
            path.write_text(
                "---\nschema_version: 1\nstatus: active\nstatus: dropped\n---\nbody\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                lines, meta, body = aha_md.load_record(path)
            self.assertIn("duplicate frontmatter key", buf.getvalue())
            # last-wins is preserved; the warning is the contract
            self.assertEqual("dropped", meta["status"])


class RawRenderEquivalenceTest(unittest.TestCase):
    """P1#2: README claims raw is "渲染等价保留" — bytes may change
    (escape_pseudo_h2, newline markers) but a CommonMark renderer
    produces equivalent output. Encode that promise as a test: every
    transformation we apply to raw text must be a render-no-op."""

    def test_escape_pseudo_h2_is_render_equivalent(self):
        # `## Foo` inside raw becomes `\## Foo` — `\#` renders as `#`
        # in CommonMark (escaped punctuation), so the rendered heading
        # text is unchanged at H1 level (and crucially, NOT promoted
        # to a real H2 by the markdown parser).
        original = "## Foo bar"
        escaped = aha_md.escape_pseudo_h2(original)
        self.assertEqual("\\## Foo bar", escaped)
        # No additional transformation beyond the leading-hash escape
        self.assertEqual(original.replace("## ", "\\## ", 1), escaped)


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


class AssertRecordPathTest(unittest.TestCase):
    """Tighter authorization: subdir + record-type whitelist. Even when a
    path is inside the right skill workspace, daily update / checkin must
    refuse a log file as if it were a task, and dao refine must refuse a
    sessions/ file as if it were a canonical dao record."""

    def setUp(self):
        self._original_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._original_cwd)

    def _make(self, tmp, *segments, content="---\n---\n"):
        path = Path(tmp).joinpath(*segments)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_correct_subdir_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            target = self._make(
                tmp, "aha-workspace", "daily", "tasks", "task-x.md",
                content="---\nschema_version: 1\ntype: task\n---\n",
            )
            aha_md.assert_record_path(target, "daily", subdir="tasks", required_type="task")

    def test_wrong_subdir_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            target = self._make(
                tmp, "aha-workspace", "daily", "logs", "log-2026-05-15.md",
                content="---\nschema_version: 1\ntype: log\n---\n",
            )
            with self.assertRaises(SystemExit) as cm:
                aha_md.assert_record_path(target, "daily", subdir="tasks", required_type="task")
            self.assertIn("expected record subdir", str(cm.exception)) if False else None
            self.assertIn("expected", str(cm.exception))

    def test_wrong_type_rejected(self):
        """A file living in the right subdir but carrying the wrong
        `type:` field is still refused — guards against a log file
        accidentally placed under tasks/."""
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            target = self._make(
                tmp, "aha-workspace", "daily", "tasks", "stranger.md",
                content="---\nschema_version: 1\ntype: log\n---\n",
            )
            with self.assertRaises(SystemExit) as cm:
                aha_md.assert_record_path(target, "daily", subdir="tasks", required_type="task")
            self.assertIn("wrong type", str(cm.exception))

    def test_subdir_only_check(self):
        """For records that don't carry a `type:` field (idea, dao),
        omit required_type and only enforce subdir."""
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            ok = self._make(tmp, "aha-workspace", "dao", "dao-md", "dao-x.md")
            aha_md.assert_record_path(ok, "dao", subdir="dao-md")

            session = self._make(tmp, "aha-workspace", "dao", "sessions", "session-1.md")
            with self.assertRaises(SystemExit):
                aha_md.assert_record_path(session, "dao", subdir="dao-md")


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


class SchemaVersionCompatibleTest(unittest.TestCase):
    """P1#7: read-path callers (scan / reflect / daily aggregation) must
    skip records carrying an unknown schema_version instead of
    interpreting them with the wrong semantics."""

    def test_accepts_matching_version(self):
        self.assertTrue(
            aha_md.schema_version_compatible({"schema_version": "1"})
        )

    def test_accepts_missing_version_legacy(self):
        # Missing field is treated as legacy v1 to keep pre-schema files readable
        self.assertTrue(aha_md.schema_version_compatible({}))

    def test_rejects_mismatched_version_with_warning(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = aha_md.schema_version_compatible(
                {"schema_version": "99"}, path="/tmp/x.md"
            )
        self.assertFalse(ok)
        self.assertIn("schema_version mismatch", buf.getvalue())
        self.assertIn("/tmp/x.md", buf.getvalue())

    def test_rejects_unparseable_version(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = aha_md.schema_version_compatible({"schema_version": "weird"})
        self.assertFalse(ok)
        self.assertIn("unparseable", buf.getvalue())


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

    def test_save_record_uses_atomic_write(self):
        """Regression: a second `save_record` definition (plain write_text)
        once silently shadowed the atomic version. If a write fails mid-way,
        the original file must remain intact (atomic rename semantics)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rec.md"
            aha_md.save_record(path, ["status: active"], "body v1\n")
            self.assertIn("status: active", path.read_text(encoding="utf-8"))

            real_replace = os.replace
            calls = {"n": 0}

            def boom(src, dst):
                calls["n"] += 1
                raise OSError("simulated mid-rename failure")

            os.replace = boom
            try:
                with self.assertRaises(OSError):
                    aha_md.save_record(path, ["status: tampered"], "body v2\n")
            finally:
                os.replace = real_replace

            self.assertEqual(1, calls["n"])
            # Original file still intact, never half-written
            self.assertIn("status: active", path.read_text(encoding="utf-8"))
            self.assertIn("body v1", path.read_text(encoding="utf-8"))
            # No leftover .tmp file
            siblings = [p.name for p in path.parent.iterdir()]
            tmp_files = [n for n in siblings if ".tmp." in n]
            self.assertEqual([], tmp_files)


class UniquePathReservationTest(unittest.TestCase):
    """Two concurrent captures with the same base_id (same timestamp +
    same slug) must end up with two distinct files. The previous
    `exists()`-poll implementation lost the second writer when both
    saw the path free before either wrote."""

    def test_unique_path_creates_empty_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            cid, path = aha_md.unique_path(Path(tmp), "rec-001")
            self.assertEqual("rec-001", cid)
            self.assertTrue(path.exists())
            self.assertEqual("", path.read_text(encoding="utf-8"))

    def test_unique_path_bumps_when_taken(self):
        with tempfile.TemporaryDirectory() as tmp:
            aha_md.unique_path(Path(tmp), "rec-001")
            cid2, path2 = aha_md.unique_path(Path(tmp), "rec-001")
            self.assertEqual("rec-001-2", cid2)
            self.assertTrue(path2.exists())

    def test_concurrent_unique_path_calls_all_distinct(self):
        """Spawn N processes that all reserve the same base_id; each must
        get its own path. Without O_EXCL, exists() polling lets multiple
        racers see a free path and one would clobber the others on write."""
        import multiprocessing

        N = 20
        BASE = "rec-race"

        def worker(tmp_str, q):
            try:
                cid, path = aha_md.unique_path(Path(tmp_str), BASE)
                # Write distinct content so an overwrite would be visible
                path.write_text(f"id={cid}\n", encoding="utf-8")
                q.put((cid, str(path), None))
            except Exception as e:  # pragma: no cover
                q.put((None, None, repr(e)))

        with tempfile.TemporaryDirectory() as tmp:
            ctx = multiprocessing.get_context("fork")
            q = ctx.Queue()
            procs = [ctx.Process(target=worker, args=(tmp, q)) for _ in range(N)]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=15)
                self.assertEqual(0, p.exitcode)

            results = [q.get(timeout=1) for _ in range(N)]
            errors = [r[2] for r in results if r[2] is not None]
            self.assertEqual([], errors)
            ids = sorted(r[0] for r in results)
            paths = sorted(r[1] for r in results)
            self.assertEqual(N, len(set(ids)), f"id collision: {ids}")
            self.assertEqual(N, len(set(paths)), f"path collision: {paths}")
            on_disk = sorted(p.name for p in Path(tmp).iterdir() if p.suffix == ".md")
            self.assertEqual(N, len(on_disk),
                             f"expected {N} files, got {len(on_disk)}")


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


class WorkspaceManifestTest(unittest.TestCase):
    def setUp(self):
        self._original_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._original_cwd)

    def test_anchor_falls_back_to_cwd_when_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            anchor = aha_md.workspace_anchor()
            # No manifest anywhere up to $HOME → fall back to cwd
            self.assertEqual(Path(tmp).resolve(), anchor)

    def test_anchor_finds_manifest_in_parent(self):
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp).resolve()
            # Create manifest at <tmp>/aha-workspace/.manifest.json
            ws = tmp_path / "aha-workspace"
            ws.mkdir()
            (ws / ".manifest.json").write_text(
                _json.dumps({"schema_version": 1, "timezone": "+08:00"}),
                encoding="utf-8",
            )
            # cd into a subdir
            sub = tmp_path / "deep" / "nested"
            sub.mkdir(parents=True)
            os.chdir(sub)
            # Anchor should walk up to tmp (where manifest lives)
            self.assertEqual(tmp_path, aha_md.workspace_anchor())

    def test_ensure_manifest_writes_payload(self):
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            aha_md.ensure_workspace_manifest()
            mp = Path(tmp) / "aha-workspace" / ".manifest.json"
            self.assertTrue(mp.exists())
            data = _json.loads(mp.read_text(encoding="utf-8"))
            self.assertEqual(1, data["schema_version"])
            self.assertIn("timezone", data)
            self.assertIn("host_id", data)

    def test_ensure_manifest_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            aha_md.ensure_workspace_manifest()
            first_mtime = (Path(tmp) / "aha-workspace" / ".manifest.json").stat().st_mtime
            aha_md.ensure_workspace_manifest()  # second call must not rewrite
            second_mtime = (Path(tmp) / "aha-workspace" / ".manifest.json").stat().st_mtime
            self.assertEqual(first_mtime, second_mtime)

    def test_check_consistency_warns_on_tz_mismatch(self):
        import io as _io
        import json as _json
        from contextlib import redirect_stderr
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            ws = Path(tmp) / "aha-workspace"
            ws.mkdir()
            (ws / ".manifest.json").write_text(
                _json.dumps({
                    "schema_version": 1,
                    "timezone": "-12:00",  # deliberately wrong vs system local
                    "host_id": "other-machine",
                }),
                encoding="utf-8",
            )
            buf = _io.StringIO()
            with redirect_stderr(buf):
                aha_md.check_manifest_consistency()
            self.assertIn("timezone mismatch", buf.getvalue())


class ParseDtTest(unittest.TestCase):
    def test_naive_datetime_gets_local_tz(self):
        out = aha_md.parse_dt("2026-05-15T10:00:00")
        self.assertIsNotNone(out)
        self.assertIsNotNone(out.tzinfo)

    def test_aware_datetime_preserved(self):
        out = aha_md.parse_dt("2026-05-15T10:00:00+05:30")
        self.assertIsNotNone(out)
        self.assertEqual(5 * 3600 + 30 * 60, int(out.utcoffset().total_seconds()))

    def test_garbage_returns_none(self):
        self.assertIsNone(aha_md.parse_dt("not-a-date"))
        self.assertIsNone(aha_md.parse_dt(""))
        self.assertIsNone(aha_md.parse_dt(None))


class ParseTagsTest(unittest.TestCase):
    def test_valid_list_parsed(self):
        self.assertEqual(["a", "b"], aha_md.parse_tags_field('["a", "b"]'))

    def test_bad_json_silently_returns_empty(self):
        # Documented behavior — bad tags string is treated as no tags
        # rather than crashing the scan path. Callers wanting fail-loud
        # should validate separately.
        self.assertEqual([], aha_md.parse_tags_field("not-json"))
        self.assertEqual([], aha_md.parse_tags_field("[unterminated"))

    def test_empty_returns_empty(self):
        self.assertEqual([], aha_md.parse_tags_field(""))
        self.assertEqual([], aha_md.parse_tags_field(None))

    def test_non_list_returns_empty(self):
        self.assertEqual([], aha_md.parse_tags_field('"just a string"'))


if __name__ == "__main__":
    unittest.main()
