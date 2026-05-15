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


if __name__ == "__main__":
    unittest.main()
