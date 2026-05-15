import importlib.util
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "daily_md.py"

SPEC = importlib.util.spec_from_file_location("daily_md", SCRIPT)
daily_md = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(daily_md)


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def expected_tasks_dir(workspace_root):
    return (Path(workspace_root) / "aha-workspace" / "daily" / "tasks").resolve()


def expected_logs_dir(workspace_root):
    return (Path(workspace_root) / "aha-workspace" / "daily" / "logs").resolve()


def expected_checkins_dir(workspace_root):
    return (Path(workspace_root) / "aha-workspace" / "daily" / "check-ins").resolve()


class DailyMarkdownCliTest(unittest.TestCase):
    def test_task_creates_record_with_due_and_status_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "task",
                "--text",
                "Write the v1 spec",
                "--due",
                "2030-01-15T18:00",
                "--priority",
                "high",
                "--tags",
                "work,doc",
                cwd=tmp,
            )
            path = Path(result.stdout.strip())
            self.assertTrue(path.exists())
            self.assertEqual(expected_tasks_dir(tmp), path.parent)
            text = path.read_text(encoding="utf-8")
            self.assertIn("type: task", text)
            self.assertIn("status: pending", text)
            self.assertIn("priority: high", text)
            self.assertIn('tags: ["work", "doc"]', text)
            self.assertIn("due_at: 2030-01-15T18:00:00", text)
            self.assertIn("postpone_count: 0", text)
            self.assertIn("difficulty_count: 0", text)
            self.assertIn("checkin_count: 0", text)
            self.assertIn("Write the v1 spec", text)
            self.assertIn("## Description", text)
            self.assertIn("schema_version: 1", text)

    def test_update_status_done_sets_completed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("task", "--text", "small task", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli("update", str(path), "--status", "done", cwd=tmp)

            text = path.read_text(encoding="utf-8")
            self.assertIn("status: done", text)
            self.assertRegex(text, r"completed_at: \d{4}-\d{2}-\d{2}T")

    def test_update_due_with_reason_logs_postponement_only_when_reason_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli(
                "task", "--text", "thing", "--due", "2030-06-01", cwd=tmp
            )
            path = Path(captured.stdout.strip())

            # Postpone WITH reason → log + count
            run_cli(
                "update",
                str(path),
                "--due",
                "2030-06-10",
                "--postpone-reason",
                "PRD review pending",
                cwd=tmp,
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("postpone_count: 1", text)
            self.assertIn("PRD review pending", text)
            self.assertIn("→ 2030-06-10T23:59:59", text)

            # Bare due change WITHOUT reason → no new log line, count unchanged
            run_cli("update", str(path), "--due", "2030-06-20", cwd=tmp)
            text2 = path.read_text(encoding="utf-8")
            self.assertIn("postpone_count: 1", text2)
            self.assertIn("due_at: 2030-06-20T23:59:59", text2)
            self.assertEqual(text.count("PRD review pending"), text2.count("PRD review pending"))

    def test_update_difficulty_appends_to_log_and_bumps_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("task", "--text", "tough task", cwd=tmp)
            path = Path(captured.stdout.strip())

            run_cli(
                "update",
                str(path),
                "--difficulty",
                "blocked on API contract",
                cwd=tmp,
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn("difficulty_count: 1", text)
            self.assertIn("blocked on API contract", text)
            self.assertIn("## Difficulty Log", text)

    def test_checkin_creates_session_appends_takeaway_and_optionally_difficulty(self):
        with tempfile.TemporaryDirectory() as tmp:
            captured = run_cli("task", "--text", "build feature X", cwd=tmp)
            path = Path(captured.stdout.strip())

            checkin = run_cli(
                "checkin",
                str(path),
                "--topic",
                "Mid-build status",
                "--conversation",
                "user: status?\nagent: 30% done.",
                "--takeaway",
                "Half a day to finish data model.",
                "--difficulty",
                "data model still fuzzy",
                "--next-step",
                "Lock model tomorrow morning",
                cwd=tmp,
            )
            checkin_path = Path(checkin.stdout.strip())
            self.assertTrue(checkin_path.exists())
            self.assertEqual(expected_checkins_dir(tmp), checkin_path.parent)
            self.assertIn("checkin-001", checkin_path.name)

            session_text = checkin_path.read_text(encoding="utf-8")
            self.assertIn("# Check-in: Mid-build status", session_text)
            self.assertIn("Half a day to finish data model.", session_text)
            self.assertIn("data model still fuzzy", session_text)
            self.assertIn("Lock model tomorrow morning", session_text)

            main_text = path.read_text(encoding="utf-8")
            self.assertIn("checkin_count: 1", main_text)
            self.assertIn("difficulty_count: 1", main_text)
            self.assertIn("[Check-in 001]", main_text)
            self.assertIn("../check-ins/", main_text)
            self.assertIn("data model still fuzzy", main_text)

    def test_log_creates_today_file_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "log",
                "--text",
                "Got up early, feeling sharp",
                "--time",
                "08:00",
                "--title",
                "Morning",
                "--tags",
                "mood",
                cwd=tmp,
            )
            path = Path(result.stdout.strip())
            self.assertTrue(path.exists())
            self.assertEqual(expected_logs_dir(tmp), path.parent)
            self.assertTrue(path.name.startswith("log-"))

            text = path.read_text(encoding="utf-8")
            self.assertIn("type: log", text)
            self.assertIn("entry_count: 1", text)
            self.assertIn('tags: ["mood"]', text)
            self.assertIn("## 08:00 — Morning", text)
            self.assertIn("Got up early, feeling sharp", text)
            self.assertIn("schema_version: 1", text)

    def test_log_second_entry_appends_to_same_file_and_unions_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            today = date.today().isoformat()
            run_cli(
                "log",
                "--text",
                "first entry",
                "--time",
                "08:00",
                "--title",
                "AM",
                "--tags",
                "mood,work",
                "--date",
                today,
                cwd=tmp,
            )
            run_cli(
                "log",
                "--text",
                "second entry",
                "--time",
                "20:00",
                "--title",
                "PM",
                "--tags",
                "work,family",
                "--date",
                today,
                cwd=tmp,
            )

            files = list(expected_logs_dir(tmp).glob("log-*.md"))
            self.assertEqual(1, len(files))
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("entry_count: 2", text)
            self.assertIn("## 08:00 — AM", text)
            self.assertIn("## 20:00 — PM", text)
            # Union order preserved: existing first, then new (deduped)
            self.assertIn('tags: ["mood", "work", "family"]', text)

    def test_scan_overdue_lists_only_overdue_active_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            overdue = run_cli("task", "--text", "expired thing", "--due", "2020-01-01", cwd=tmp)
            future = run_cli("task", "--text", "future thing", "--due", "2099-01-01", cwd=tmp)
            done_overdue = run_cli("task", "--text", "done late", "--due", "2020-01-01", cwd=tmp)
            run_cli("update", done_overdue.stdout.strip(), "--status", "done", cwd=tmp)

            scan = run_cli("scan", "--mode", "overdue", cwd=tmp)
            lines = [line for line in scan.stdout.strip().splitlines() if line]

            self.assertEqual(1, len(lines))
            self.assertIn("expired thing", lines[0])
            self.assertNotIn("future thing", scan.stdout)
            self.assertNotIn("done late", scan.stdout)
            self.assertTrue(lines[0].startswith("task\t"))

    def test_scan_period_week_includes_tasks_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            today = date.today().isoformat()
            run_cli("task", "--text", "this-week task", cwd=tmp)
            run_cli("log", "--text", "morning log", "--time", "08:00", "--date", today, cwd=tmp)

            scan = run_cli(
                "scan",
                "--mode",
                "period",
                "--period",
                "week",
                "--date",
                today,
                "--type",
                "all",
                cwd=tmp,
            )

            lines = [line for line in scan.stdout.strip().splitlines() if line]
            type_prefixes = {line.split("\t", 1)[0] for line in lines}
            self.assertIn("task", type_prefixes)
            self.assertIn("log", type_prefixes)
            self.assertTrue(any("this-week task" in line for line in lines))

    def test_scan_filters_by_status_and_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_cli("task", "--text", "alpha", "--tags", "work", cwd=tmp)
            beta = run_cli("task", "--text", "beta", "--tags", "personal", cwd=tmp)
            run_cli("update", beta.stdout.strip(), "--status", "in_progress", cwd=tmp)

            scan = run_cli(
                "scan",
                "--mode",
                "active",
                "--status",
                "pending",
                "--tag",
                "work",
                cwd=tmp,
            )
            lines = [line for line in scan.stdout.strip().splitlines() if line]
            self.assertEqual(1, len(lines))
            self.assertIn("alpha", lines[0])


    def test_review_writes_skeleton_with_snapshot_and_is_write_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            today = date.today().isoformat()
            run_cli("task", "--text", "ship spec", "--due", "2099-01-01", "--tags", "work", cwd=tmp)
            run_cli("log", "--text", "afternoon focus dip", "--time", "14:30", "--date", today, "--tags", "mood", cwd=tmp)

            res = run_cli("review", "--period", "week", cwd=tmp)
            out_path = Path(res.stdout.strip())
            self.assertTrue(out_path.exists())
            self.assertEqual(
                (Path(tmp) / "aha-workspace" / "daily" / "reviews").resolve(),
                out_path.parent.resolve(),
            )

            text = out_path.read_text(encoding="utf-8")
            self.assertIn("schema_version: 1", text)
            self.assertIn("period: week", text)
            self.assertIn("### Tasks touched", text)
            self.assertIn("ship spec", text)
            self.assertIn("### Logs (1)", text)
            self.assertIn("## 模式与启示", text)
            self.assertIn("## 下阶段意图", text)
            # P1#7 placeholder discipline mirrored from reflect
            self.assertIn("不要单方面预填", text)

            # Write-once: second invocation creates -2.md, not overwrite
            res2 = run_cli("review", "--period", "week", cwd=tmp)
            second_path = Path(res2.stdout.strip())
            self.assertNotEqual(out_path.name, second_path.name)
            self.assertTrue(second_path.name.endswith("-2.md"))


if __name__ == "__main__":
    unittest.main()
