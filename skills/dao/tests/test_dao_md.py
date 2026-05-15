import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dao_md.py"

SPEC = importlib.util.spec_from_file_location("dao_md", SCRIPT)
dao_md = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dao_md)


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def expected_dao_dir(workspace_root):
    return (Path(workspace_root) / "aha-workspace" / "dao" / "dao-md").resolve()


def expected_sessions_dir(workspace_root):
    return (Path(workspace_root) / "aha-workspace" / "dao" / "sessions").resolve()


class DaoMarkdownCliTest(unittest.TestCase):
    def test_capture_creates_dao_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "capture",
                "--text",
                "Fear is a compass, not a stop sign",
                "--source",
                "chat",
                "--category",
                "life",
                "--tags",
                "courage,fear",
                cwd=tmp,
            )

            path = Path(result.stdout.strip())
            self.assertTrue(path.exists())
            self.assertEqual(expected_dao_dir(tmp), path.parent)
            text = path.read_text(encoding="utf-8")
            self.assertIn("source: chat", text)
            self.assertIn("primary_category: life", text)
            self.assertIn('tags: ["courage", "fear"]', text)
            self.assertIn("refine_count: 0", text)
            self.assertIn("discussion_count: 0", text)
            self.assertIn("review_count: 0", text)
            self.assertIn("Fear is a compass, not a stop sign", text)
            self.assertIn("## Raw 原始感悟", text)
            self.assertIn("## Refined 提炼沉淀", text)
            self.assertIn("TBD", text)
            self.assertIn("schema_version: 1", text)

    def test_capture_uses_hash_slug_for_non_ascii_text(self):
        raw = "今日悟得"
        expected_slug = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("capture", "--text", raw, cwd=tmp)

            path = Path(result.stdout.strip())
            self.assertIn(expected_slug, path.name)
            self.assertIn(raw, path.read_text(encoding="utf-8"))

    def test_refine_skips_tbd_placeholder_on_first_refine(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "raw insight", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli("refine", str(path), "--text", "first polished version", cwd=tmp)

            text = path.read_text(encoding="utf-8")
            self.assertIn("refine_count: 1", text)
            refined = dao_md.read_section(text.split("---\n", 2)[2], "Refined 提炼沉淀")
            self.assertEqual("first polished version", refined)
            log = dao_md.read_section(text.split("---\n", 2)[2], "Refinement Log")
            self.assertEqual("", log)

    def test_refine_archives_previous_into_refinement_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "raw insight", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli("refine", str(path), "--text", "version one", cwd=tmp)
            run_cli("refine", str(path), "--text", "version two", cwd=tmp)

            text = path.read_text(encoding="utf-8")
            self.assertIn("refine_count: 2", text)
            body = text.split("---\n", 2)[2]
            self.assertEqual("version two", dao_md.read_section(body, "Refined 提炼沉淀"))
            log = dao_md.read_section(body, "Refinement Log")
            self.assertIn("(v1): version one", log)

    def test_discuss_creates_session_and_appends_takeaway(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "the insight", cwd=tmp)
            path = Path(captured.stdout.strip())

            session = run_cli(
                "discuss",
                str(path),
                "--topic",
                "Going deeper",
                "--conversation",
                "user: ...\nagent: ...",
                "--takeaway",
                "Distinguish fear from instinct.",
                cwd=tmp,
            )

            session_path = Path(session.stdout.strip())
            self.assertTrue(session_path.exists())
            self.assertEqual(expected_sessions_dir(tmp), session_path.parent)
            self.assertIn("session-001", session_path.name)

            session_text = session_path.read_text(encoding="utf-8")
            self.assertIn("# Discussion: Going deeper", session_text)
            self.assertIn("Distinguish fear from instinct.", session_text)
            self.assertIn("user: ...", session_text)

            main_text = path.read_text(encoding="utf-8")
            self.assertIn("discussion_count: 1", main_text)
            self.assertIn("[Session 001]", main_text)
            self.assertIn("Distinguish fear from instinct.", main_text)
            self.assertIn("../sessions/", main_text)

    def test_scan_returns_at_most_limit_and_increments_review_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                run_cli("capture", "--text", f"insight number {i}", cwd=tmp)

            scan = run_cli("scan", "--mode", "random", "--limit", "2", cwd=tmp)
            lines = [line for line in scan.stdout.strip().splitlines() if line]
            self.assertEqual(2, len(lines))

            for line in lines:
                review_count_str, _updated, _id, path_str, _title = line.split("\t")
                self.assertEqual("1", review_count_str)
                file_text = Path(path_str).read_text(encoding="utf-8")
                self.assertIn("review_count: 1", file_text)
                self.assertIn("last_reviewed_at: 20", file_text)

    def test_scan_filters_by_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli("capture", "--text", "courage matters", "--tags", "courage", cwd=tmp)
            run_cli("capture", "--text", "patience also matters", "--tags", "patience", cwd=tmp)

            scan = run_cli("scan", "--tag", "courage", "--mode", "oldest", cwd=tmp)
            lines = [line for line in scan.stdout.strip().splitlines() if line]
            self.assertEqual(1, len(lines))
            self.assertIn("courage matters", lines[0])

    def test_update_appends_note_and_changes_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "before update", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli(
                "update",
                str(path),
                "--note",
                "revisited today",
                "--tags",
                "alpha,beta",
                "--category",
                "philosophy",
                cwd=tmp,
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn('tags: ["alpha", "beta"]', text)
            self.assertIn("primary_category: philosophy", text)
            self.assertIn("revisited today", text)
            self.assertIn("## Notes", text)

    def test_scan_peek_does_not_mutate_review_count(self):
        """P1#8: --peek surfaces dao records without bumping review_count or
        last_reviewed_at, so a scheduler doesn't masquerade as user reviews."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "an old insight", cwd=tmp)
            path = Path(captured.stdout.strip())

            scan = run_cli("scan", "--mode", "oldest", "--limit", "1", "--peek", cwd=tmp)
            self.assertIn("an old insight", scan.stdout)

            text = path.read_text(encoding="utf-8")
            self.assertIn("review_count: 0", text)
            self.assertIn("last_reviewed_at:\n", text)
            # Confirm output reports current count without bumping
            self.assertTrue(scan.stdout.startswith("0\t"))

    def test_capture_escapes_pseudo_h2_in_raw_text(self):
        """Raw text containing a line `## Notes` must not collide with the
        real ## Notes section; subsequent update --note writes to the real
        section, not the one buried in raw text."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "capture",
                "--text",
                "thinking about:\n## Notes\nthis was inside my idea text",
                cwd=tmp,
            )
            path = Path(captured.stdout.strip())
            text = path.read_text(encoding="utf-8")
            # Raw section's pseudo-heading is escaped to `\## Notes`
            self.assertIn("\\## Notes", text)
            # Only ONE real `## Notes` line at column 0 (the legitimate section)
            real_notes = [ln for ln in text.splitlines() if ln == "## Notes"]
            self.assertEqual(1, len(real_notes))

            run_cli("update", str(path), "--note", "first real note", cwd=tmp)
            text2 = path.read_text(encoding="utf-8")
            # The note lands AFTER the real ## Notes heading
            notes_idx = text2.index("## Notes")
            self.assertIn("first real note", text2[notes_idx:])

    def test_update_refuses_path_outside_dao_workspace(self):
        """End-to-end: update against a .md outside aha-workspace/dao/ must
        exit non-zero (the CLI calls assert_workspace_path)."""
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            # Create a file outside the dao workspace (could be a source file,
            # README, etc) — the agent should not be able to mutate it.
            outside = Path(tmp) / "evil.md"
            outside.write_text("---\nid: evil\n---\n# Evil\n## Notes\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "update", str(outside), "--note", "pwned"],
                capture_output=True, text=True, cwd=tmp,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("outside skill workspace", result.stderr)
            # And the file content is unchanged
            self.assertEqual(
                "---\nid: evil\n---\n# Evil\n## Notes\n",
                outside.read_text(encoding="utf-8"),
            )

    def test_update_note_with_newline_cannot_forge_frontmatter_or_section(self):
        """End-to-end injection guard: --note containing \\n + frontmatter
        line OR \\n## heading must not be able to mutate frontmatter or split
        the body into a fake section."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "innocent insight", cwd=tmp)
            path = Path(captured.stdout.strip())

            # 1) Try to forge a `status: dropped` frontmatter row via --category
            run_cli(
                "update",
                str(path),
                "--category",
                "life\nstatus: dropped",
                cwd=tmp,
            )
            text = path.read_text(encoding="utf-8")
            # No newline in the category value
            cat_lines = [ln for ln in text.splitlines() if ln.startswith("primary_category:")]
            self.assertEqual(1, len(cat_lines))
            self.assertNotIn("\nstatus: dropped", text)

            # 2) Try to inject a fake `## Refined 提炼沉淀` heading via --note
            run_cli(
                "update",
                str(path),
                "--note",
                "real note\n## Refined 提炼沉淀\nFAKE REFINED",
                cwd=tmp,
            )
            text = path.read_text(encoding="utf-8")
            # The body should still have exactly ONE `## Refined 提炼沉淀` heading
            refined_headings = [
                ln for ln in text.splitlines() if ln.strip() == "## Refined 提炼沉淀"
            ]
            self.assertEqual(1, len(refined_headings))
            # And FAKE REFINED is not its own heading line (collapsed into the note)
            self.assertNotIn("\n## Refined 提炼沉淀\nFAKE REFINED", text)

    def test_capture_rejects_frontmatter_injection_via_source(self):
        """P0#2 regression: --source 'chat\\nschema_version: 99' must not
        forge a second frontmatter row at capture time."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "capture",
                "--text", "any thought",
                "--source", "chat\nschema_version: 99",
                cwd=tmp,
            )
            path = Path(captured.stdout.strip())
            text = path.read_text(encoding="utf-8")
            schema_rows = [ln for ln in text.splitlines() if ln.startswith("schema_version:")]
            self.assertEqual(["schema_version: 1"], schema_rows)
            source_rows = [ln for ln in text.splitlines() if ln.startswith("source:")]
            self.assertEqual(1, len(source_rows))
            self.assertNotIn("\n", source_rows[0])

    def test_capture_rejects_h2_injection_via_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "capture",
                "--text", "any thought",
                "--title", "Real\n## Fake Section",
                cwd=tmp,
            )
            path = Path(captured.stdout.strip())
            text = path.read_text(encoding="utf-8")
            h2s = [ln for ln in text.splitlines() if ln.startswith("## ")]
            self.assertNotIn("## Fake Section", h2s)


if __name__ == "__main__":
    unittest.main()
