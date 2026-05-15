import hashlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "idea_md.py"

SPEC = importlib.util.spec_from_file_location("idea_md", SCRIPT)
idea_md = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(idea_md)


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def expected_idea_dir(workspace_root):
    return (Path(workspace_root) / "aha-workspace" / "idea" / "idea-md").resolve()


class IdeaMarkdownCliTest(unittest.TestCase):
    def test_capture_creates_markdown_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "capture",
                "--text",
                "Build a tiny idea inbox",
                "--source",
                "chat",
                "--status",
                "researching",
                "--category",
                "product",
                "--tags",
                "idea,research",
                "--next-review-at",
                "2026-05-13",
                cwd=tmp,
            )

            path = Path(result.stdout.strip())
            self.assertTrue(path.exists())
            self.assertEqual(expected_idea_dir(tmp), path.parent)
            text = path.read_text(encoding="utf-8")
            self.assertIn("status: researching", text)
            self.assertIn("source: chat", text)
            self.assertIn('tags: ["idea", "research"]', text)
            self.assertIn("next_review_at: 2026-05-13T00:00:00", text)
            self.assertIn("Build a tiny idea inbox", text)
            self.assertIn("schema_version: 1", text)

    def test_capture_uses_hash_slug_when_text_has_no_ascii_words(self):
        raw = "灵感捕获"
        expected_slug = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("capture", "--text", raw, cwd=tmp)

            path = Path(result.stdout.strip())
            self.assertIn(expected_slug, path.name)
            self.assertIn(raw, path.read_text(encoding="utf-8"))

    def test_capture_never_overwrites_existing_idea_file(self):
        fixed_now = datetime(2026, 5, 12, 14, 30, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(
                text="Same idea",
                title=None,
                status="inbox",
                source="manual",
                priority="medium",
                category=None,
                tags=None,
                next_review_at=None,
            )
            fixed_dir = expected_idea_dir(tmp)
            with mock.patch.object(idea_md, "local_now", return_value=fixed_now):
                with mock.patch.object(idea_md, "default_idea_dir", return_value=fixed_dir):
                    with redirect_stdout(io.StringIO()):
                        idea_md.capture(args)
                        idea_md.capture(args)

            paths = sorted(fixed_dir.glob("*.md"))
            self.assertEqual(2, len(paths))
            self.assertCountEqual(
                [
                    "idea-20260512-143000-same-idea.md",
                    "idea-20260512-143000-same-idea-2.md",
                ],
                [path.name for path in paths],
            )

    def test_update_appends_decision_and_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "Turn idea into task", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli(
                "update",
                str(path),
                "--status",
                "planning",
                "--decision",
                "Ready for a concrete plan.",
                "--note",
                "CLI update works.",
                "--bump-review",
                "--prompted",
                "--next-review-at",
                "",
                cwd=tmp,
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn("status: planning", text)
            self.assertIn("next_review_at: ", text)
            self.assertIn("last_prompted_at: ", text)
            self.assertIn("review_count: 1", text)
            self.assertIn("Ready for a concrete plan.", text)
            self.assertIn("CLI update works.", text)

    def test_scan_lists_due_active_ideas(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "capture",
                "--text",
                "Review this idea",
                "--status",
                "researching",
                "--next-review-at",
                "2000-01-01",
                cwd=tmp,
            )
            path = Path(captured.stdout.strip())

            scan = run_cli("scan", "--stale-days", "7", cwd=tmp)

            self.assertIn("researching", scan.stdout)
            self.assertIn(str(path), scan.stdout)

    def test_scan_creates_default_idea_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            scan = run_cli("scan", cwd=tmp)

            self.assertEqual("", scan.stdout)
            self.assertTrue(expected_idea_dir(tmp).is_dir())


if __name__ == "__main__":
    unittest.main()
