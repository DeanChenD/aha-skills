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


def run_cli(*args, cwd=None, input_stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
        input=input_stdin,
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
            # P2#10: capture stamps a workspace manifest
            manifest = Path(tmp) / "aha-workspace" / ".manifest.json"
            self.assertTrue(manifest.exists())

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
            # Cleared next_review_at renders as `key:` (no trailing space),
            # matching the byte-shape of a freshly-captured empty field
            # (P1#15 unified set_meta with render_frontmatter).
            self.assertIn("\nnext_review_at:\n", text)
            self.assertRegex(text, r"last_prompted_at: \d{4}-\d{2}-\d{2}T")
            self.assertIn("review_count: 1", text)
            self.assertIn("Ready for a concrete plan.", text)
            self.assertIn("CLI update works.", text)

    def test_update_decision_and_note_via_stdin(self):
        # R3#5: --decision and --note are user-derived free-text fields.
        # Mirror --text's stdin/file entry points so agents assembling
        # bash for chat-derived decisions/notes don't have to inline
        # untrusted text into shell quotes (which would execute $(...) /
        # backticks).
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "raw idea", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli(
                "update", str(path), "--decision-stdin",
                cwd=tmp, input_stdin="$(whoami) wants to ship this.",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("$(whoami) wants to ship this.", text)

            run_cli(
                "update", str(path), "--note-stdin",
                cwd=tmp, input_stdin="follow-up: `rm -rf /` not sanitized.",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("follow-up: `rm -rf /` not sanitized.", text)

    def test_enrich_replaces_body_sections_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "Build an idea inbox", cwd=tmp)
            path = Path(captured.stdout.strip())

            tmp_path = Path(tmp)
            summary = tmp_path / "summary.txt"
            classification = tmp_path / "classification.txt"
            research_task = tmp_path / "research_task.txt"
            plan = tmp_path / "plan.txt"
            questions = tmp_path / "questions.txt"
            summary.write_text("A compact inbox for turning sparks into plans.\n## Fake", encoding="utf-8")
            classification.write_text(
                "- Primary category: product\n- Tags: idea, workflow\n- Confidence: medium\n",
                encoding="utf-8",
            )
            research_task.write_text("Clarify the smallest useful capture loop.", encoding="utf-8")
            plan.write_text("- [ ] Draft UX\n- [ ] Validate with one user\n", encoding="utf-8")
            questions.write_text("1. Who uses it first?\n2. What counts as done?\n", encoding="utf-8")

            run_cli(
                "enrich",
                str(path),
                "--summary-file", str(summary),
                "--classification-file", str(classification),
                "--research-task-file", str(research_task),
                "--plan-file", str(plan),
                "--questions-file", str(questions),
                "--status", "researching",
                "--category", "product",
                "--tags", "idea,workflow",
                "--next-review-at", "2030-01-02",
                cwd=tmp,
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn("status: researching", text)
            self.assertIn("primary_category: product", text)
            self.assertIn('tags: ["idea", "workflow"]', text)
            self.assertIn("next_review_at: 2030-01-02T00:00:00", text)
            self.assertIn("A compact inbox for turning sparks into plans.", text)
            self.assertIn("- Primary category: product", text)
            self.assertIn("Clarify the smallest useful capture loop.", text)
            self.assertIn("- [ ] Draft UX", text)
            self.assertIn("1. Who uses it first?", text)
            h2s = [ln for ln in text.splitlines() if ln.startswith("## ")]
            self.assertNotIn("## Fake", h2s)

    def test_enrich_rejects_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("capture", "--text", "No-op idea", cwd=tmp)
            path = Path(captured.stdout.strip())

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "enrich", str(path)],
                capture_output=True,
                text=True,
                cwd=tmp,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("Nothing to enrich", result.stderr)

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

    def test_scan_with_mark_prompted_then_cooldown_skips(self):
        """P1#16: scan is read-only by default; the scheduler opts into
        last_prompted_at stamping with --mark-prompted. Subsequent scan
        within the cooldown window then skips the same idea."""
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "capture", "--text", "Cron should not spam this",
                "--status", "researching",
                "--next-review-at", "2000-01-01",
                cwd=tmp,
            )
            # Cron-style scan: explicit --mark-prompted marks last_prompted_at = now
            scan1 = run_cli("scan", "--stale-days", "7", "--mark-prompted", cwd=tmp)
            self.assertIn("researching", scan1.stdout)

            # Second scan with mark within cooldown skips the idea
            scan2 = run_cli("scan", "--stale-days", "7", "--mark-prompted", cwd=tmp)
            self.assertEqual("", scan2.stdout.strip())

            # Read-only default surfaces the idea regardless (a human is browsing)
            scan3 = run_cli(
                "scan", "--stale-days", "7", "--cooldown-hours", "0",
                cwd=tmp,
            )
            self.assertIn("researching", scan3.stdout)

    def test_scan_default_is_readonly(self):
        """P1#16: by default scan does NOT stamp last_prompted_at, so a
        curious terminal `scan` doesn't burn cron's cooldown."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "capture", "--text", "Default-readonly target",
                "--status", "researching",
                "--next-review-at", "2000-01-01",
                cwd=tmp,
            )
            path = Path(captured.stdout.strip())

            scan = run_cli("scan", "--stale-days", "7", cwd=tmp)
            self.assertIn("researching", scan.stdout)

            text = path.read_text(encoding="utf-8")
            empty_lines = [
                ln for ln in text.splitlines() if ln.startswith("last_prompted_at:")
            ]
            self.assertEqual(["last_prompted_at:"], empty_lines)

    def test_scan_peek_does_not_mark_last_prompted_at(self):
        """--peek (deprecated) still forces read-only even if --mark-prompted is set."""
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "capture", "--text", "Peek-only target",
                "--status", "researching",
                "--next-review-at", "2000-01-01",
                cwd=tmp,
            )
            path = Path(captured.stdout.strip())

            # Peek scan overrides --mark-prompted: still read-only
            scan = run_cli(
                "scan", "--stale-days", "7", "--peek", "--mark-prompted", cwd=tmp,
            )
            self.assertIn("researching", scan.stdout)

            # last_prompted_at remains empty
            text = path.read_text(encoding="utf-8")
            empty_lines = [
                ln for ln in text.splitlines() if ln.startswith("last_prompted_at:")
            ]
            self.assertEqual(["last_prompted_at:"], empty_lines)

    def test_scan_creates_default_idea_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            scan = run_cli("scan", cwd=tmp)

            self.assertEqual("", scan.stdout)
            self.assertTrue(expected_idea_dir(tmp).is_dir())

    def test_scan_include_completed_skips_frontmatterless_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            idea_dir = expected_idea_dir(tmp)
            idea_dir.mkdir(parents=True)
            stray = idea_dir / "notes.md"
            stray.write_text("# Not an idea record\n", encoding="utf-8")

            scan = run_cli("scan", "--include-completed", cwd=tmp)

            self.assertEqual("", scan.stdout.strip())

    def test_scan_skips_unknown_schema_version(self):
        """P1#7: a file written by a future skill version (schema_version: 99)
        must not be re-surfaced by today's scan — semantics may have shifted.
        Plant both a v1 (old enough to be stale) and a v99 record so the
        skip is observable: v1 surfaces, v99 doesn't."""
        with tempfile.TemporaryDirectory() as tmp:
            idea_dir = expected_idea_dir(tmp)
            idea_dir.mkdir(parents=True, exist_ok=True)
            # Capture once to lay the manifest, then overwrite with an old timestamp
            run_cli("capture", "--text", "an old idea", "--source", "chat", cwd=tmp)
            v1 = next(idea_dir.glob("idea-*.md"))
            v1.write_text(
                "---\nschema_version: 1\nid: legacy\nstatus: researching\n"
                "updated_at: 2020-01-01T00:00:00\nlast_prompted_at:\n"
                "next_review_at:\n---\n# Legacy\n## Raw Idea\nstale\n",
                encoding="utf-8",
            )
            # Plant a v99 record beside it (same staleness, should still be skipped)
            v99 = idea_dir / "idea-future.md"
            v99.write_text(
                "---\nschema_version: 99\nid: future\nstatus: researching\n"
                "updated_at: 2020-01-01T00:00:00\nlast_prompted_at:\n"
                "next_review_at:\n---\n# Future\n",
                encoding="utf-8",
            )
            scan = run_cli("scan", "--stale-days", "7", "--peek", cwd=tmp)
            self.assertIn(str(v1), scan.stdout)
            self.assertNotIn("idea-future.md", scan.stdout)
            self.assertIn("schema_version mismatch", scan.stderr)

    def test_capture_rejects_frontmatter_injection_via_category(self):
        """P0#2 regression: a newline inside --category must not split into
        a second frontmatter row that forges status / schema_version."""
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "capture",
                "--text", "innocent idea",
                "--category", "x\nstatus: killed\nschema_version: 99",
                cwd=tmp,
            )
            files = list(expected_idea_dir(tmp).glob("idea-*.md"))
            self.assertEqual(1, len(files))
            text = files[0].read_text(encoding="utf-8")
            # Exactly one status row, and it carries the original status, not "killed"
            status_rows = [ln for ln in text.splitlines() if ln.startswith("status:")]
            self.assertEqual(1, len(status_rows))
            self.assertNotIn("killed", status_rows[0])
            schema_rows = [ln for ln in text.splitlines() if ln.startswith("schema_version:")]
            self.assertEqual(["schema_version: 1"], schema_rows)
            # primary_category line carries the visible newline marker
            cat_row = next(ln for ln in text.splitlines() if ln.startswith("primary_category:"))
            self.assertNotIn("\n", cat_row)
            self.assertIn("↵", cat_row)

    def test_capture_injection_then_update_can_clean(self):
        """P1#17 (links P0#2 + P0#3): the full attack chain.

        Step 1: capture is hit with an injection that would have forged a
                second `status:` row in the pre-P0#2 code.
        Step 2: post-fix, the capture sanitizes; no second row appears.
        Step 3: even if a v0 file with a duplicate `status:` row somehow
                exists (planted directly here), a subsequent `update
                --status` collapses the duplicate so reflect can no
                longer read a forged value.

        Without all three landing together, a malicious capture would
        leave a stuck-forever forged status (P0#3 unfix) or land it in
        the first place (P0#2 unfix)."""
        with tempfile.TemporaryDirectory() as tmp:
            # Step 1+2: capture refuses to forge a status row
            run_cli(
                "capture",
                "--text", "innocent idea",
                "--category", "x\nstatus: killed",
                "--status", "inbox",
                cwd=tmp,
            )
            files = list(expected_idea_dir(tmp).glob("idea-*.md"))
            self.assertEqual(1, len(files))
            path = files[0]
            text = path.read_text(encoding="utf-8")
            status_rows = [ln for ln in text.splitlines() if ln.startswith("status:")]
            self.assertEqual(["status: inbox"], status_rows)

            # Step 3: simulate a legacy file containing an injected
            # second status row (could be from a pre-P0#1 version or
            # a hand-edit). update --status collapses it.
            poisoned = text.replace(
                "status: inbox\n",
                "status: inbox\nstatus: killed\n",
                1,
            )
            path.write_text(poisoned, encoding="utf-8")

            run_cli("update", str(path), "--status", "researching", cwd=tmp)
            cleaned = path.read_text(encoding="utf-8")
            cleaned_status = [ln for ln in cleaned.splitlines() if ln.startswith("status:")]
            self.assertEqual(
                ["status: researching"], cleaned_status,
                "set_meta must collapse the injected duplicate row",
            )

    def test_capture_rejects_h2_injection_via_title(self):
        """P0#2 regression (title path): a newline+## in --title must not
        split the body into a fake H2 section."""
        with tempfile.TemporaryDirectory() as tmp:
            run_cli(
                "capture",
                "--text", "body text",
                "--title", "Real title\n## Fake Section",
                cwd=tmp,
            )
            files = list(expected_idea_dir(tmp).glob("idea-*.md"))
            text = files[0].read_text(encoding="utf-8")
            # No H2 line whose stripped form is exactly "## Fake Section"
            h2s = [ln for ln in text.splitlines() if ln.startswith("## ")]
            self.assertNotIn("## Fake Section", h2s)


if __name__ == "__main__":
    unittest.main()
