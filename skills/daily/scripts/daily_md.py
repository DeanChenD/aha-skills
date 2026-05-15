#!/usr/bin/env python3
import argparse
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from aha_md import (  # noqa: E402
    WORKSPACE_DIR_NAME,
    append_to_section,
    ensure_dir,
    format_tags,
    int_meta,
    load_record,
    local_now,
    parse_dt,
    parse_frontmatter_lines,
    parse_tags_field,
    period_range,
    save_record,
    set_meta,
    slugify,
    split_frontmatter,
    title_from_body,
    unique_path,
)


DAILY_ROOT_RELATIVE = Path(WORKSPACE_DIR_NAME) / "daily"
TASKS_DIR_RELATIVE = DAILY_ROOT_RELATIVE / "tasks"
LOGS_DIR_RELATIVE = DAILY_ROOT_RELATIVE / "logs"
CHECKINS_DIR_RELATIVE = DAILY_ROOT_RELATIVE / "check-ins"
REVIEWS_DIR_RELATIVE = DAILY_ROOT_RELATIVE / "reviews"

TASKS_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/daily/tasks"

DESCRIPTION_HEADING = "Description 描述"
DIFFICULTY_LOG_HEADING = "Difficulty Log 困难记录"
POSTPONEMENT_LOG_HEADING = "Postponement Log 推迟记录"
CHECKIN_LOG_HEADING = "Check-in Log 阶段记录"
NOTES_HEADING = "Notes"

TASK_STATUSES = ("pending", "in_progress", "blocked", "done", "dropped")
TERMINAL_STATUSES = {"done", "dropped"}
PRIORITIES = ("low", "medium", "high")
SCAN_MODES = (
    "overdue",
    "due-today",
    "due-soon",
    "active",
    "completed",
    "period",
)
PERIODS = ("day", "week", "month")
SCAN_TYPES = ("task", "log", "all")


def title_from_text(text):
    first = " ".join(text.strip().split())
    if not first:
        return "Untitled Task"
    return first[:80]


def default_tasks_dir():
    return (Path.cwd() / TASKS_DIR_RELATIVE).resolve()


def default_logs_dir():
    return (Path.cwd() / LOGS_DIR_RELATIVE).resolve()


def default_checkins_dir():
    return (Path.cwd() / CHECKINS_DIR_RELATIVE).resolve()


def default_reviews_dir():
    return (Path.cwd() / REVIEWS_DIR_RELATIVE).resolve()


def union_tags(existing_json_str, new_csv):
    existing = parse_tags_field(existing_json_str)
    new = [t.strip() for t in (new_csv or "").split(",") if t.strip()]
    seen = set()
    merged = []
    for tag in existing + new:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)
    return format_tags(merged)


DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_due(value):
    if not value:
        return ""
    stripped = value.strip()
    if DATE_ONLY_RE.match(stripped):
        try:
            d = date.fromisoformat(stripped)
            dt = datetime.combine(d, time(23, 59, 59)).astimezone()
            return dt.isoformat(timespec="seconds")
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(stripped)
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt.isoformat(timespec="seconds")
    except ValueError:
        pass
    raise SystemExit(f"Invalid due value: {value}")


def parse_date_arg(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise SystemExit(f"Invalid date: {value}")


def parse_time_arg(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        try:
            return datetime.strptime(value, "%H:%M:%S").time()
        except ValueError:
            raise SystemExit(f"Invalid time: {value}")


def render_task_skeleton(task_id, title, description, now, due_at_iso, priority, source, category, tags):
    timestamp = now.isoformat(timespec="seconds")
    return f"""---
id: {task_id}
type: task
status: pending
created_at: {timestamp}
updated_at: {timestamp}
due_at: {due_at_iso}
completed_at:
priority: {priority}
source: {source}
primary_category: {category or ""}
tags: {format_tags(tags)}
checkin_count: 0
postpone_count: 0
difficulty_count: 0
---

# {title}

## {DESCRIPTION_HEADING}

{description}

## {DIFFICULTY_LOG_HEADING}

## {POSTPONEMENT_LOG_HEADING}

## {CHECKIN_LOG_HEADING}

## {NOTES_HEADING}
"""


def render_log_skeleton(date_str, now, tags):
    timestamp = now.isoformat(timespec="seconds")
    return f"""---
date: {date_str}
type: log
created_at: {timestamp}
updated_at: {timestamp}
entry_count: 0
tags: {format_tags(tags)}
---

# {date_str}
"""


def render_checkin_body(checkin_id, parent_task_id, now, topic, conversation, takeaway, difficulty, next_step):
    timestamp = now.isoformat(timespec="seconds")
    diff_block = difficulty.strip() if difficulty else "(none)"
    next_block = next_step.strip() if next_step else "(none)"
    return f"""---
checkin_id: {checkin_id}
parent_task_id: {parent_task_id}
created_at: {timestamp}
---

# Check-in: {topic}

## Prompt 起点

{topic}

## Conversation 对话原文

{conversation}

## Difficulties Surfaced

{diff_block}

## Takeaway 收获

{takeaway}

## Next Step

{next_block}
"""


def _append_log_entry(body, time_str, title, text):
    body = body.rstrip() + "\n\n"
    body += f"## {time_str} — {title}\n\n{text.strip()}\n"
    return body


def task(args):
    root = default_tasks_dir()
    ensure_dir(root)
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.text, fallback="task")
    task_id, path = unique_path(root, f"task-{stamp}-{slug}")
    title = args.title or title_from_text(args.text)
    due_iso = parse_due(args.due) if args.due else ""
    body = render_task_skeleton(
        task_id,
        title,
        args.text,
        now,
        due_iso,
        args.priority,
        args.source,
        args.category,
        args.tags,
    )
    path.write_text(body, encoding="utf-8")
    print(path)


def update(args):
    path = Path(args.file).expanduser().resolve()
    lines, meta, body = load_record(path)
    now = local_now()

    if args.category is not None:
        set_meta(lines, "primary_category", args.category)
    if args.tags is not None:
        set_meta(lines, "tags", format_tags(args.tags))
    if args.priority:
        set_meta(lines, "priority", args.priority)

    if args.status:
        set_meta(lines, "status", args.status)
        if args.status == "done":
            set_meta(lines, "completed_at", now.isoformat(timespec="seconds"))

    if args.due is not None:
        new_due_iso = parse_due(args.due) if args.due else ""
        old_due = meta.get("due_at", "")
        set_meta(lines, "due_at", new_due_iso)
        if args.postpone_reason:
            new_count = int_meta(meta, "postpone_count") + 1
            set_meta(lines, "postpone_count", str(new_count))
            log_line = (
                f"- {now.date().isoformat()}: {old_due or '(unset)'} → "
                f"{new_due_iso or '(unset)'}: {args.postpone_reason}"
            )
            body = append_to_section(body, POSTPONEMENT_LOG_HEADING, log_line)

    if args.difficulty:
        new_count = int_meta(meta, "difficulty_count") + 1
        set_meta(lines, "difficulty_count", str(new_count))
        body = append_to_section(
            body,
            DIFFICULTY_LOG_HEADING,
            f"- {now.date().isoformat()}: {args.difficulty}",
        )

    if args.note:
        body = append_to_section(
            body, NOTES_HEADING, f"- {now.date().isoformat()}: {args.note}"
        )

    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))
    save_record(path, lines, body)
    print(path)


def checkin(args):
    path = Path(args.file).expanduser().resolve()
    lines, meta, body = load_record(path)
    now = local_now()

    parent_id = meta.get("id") or path.stem
    new_count = int_meta(meta, "checkin_count") + 1
    checkin_index = f"{new_count:03d}"
    checkin_id = f"{parent_id}-checkin-{checkin_index}"

    checkins_dir = default_checkins_dir()
    ensure_dir(checkins_dir)
    checkin_path = checkins_dir / f"{checkin_id}.md"
    checkin_path.write_text(
        render_checkin_body(
            checkin_id,
            parent_id,
            now,
            args.topic,
            args.conversation,
            args.takeaway,
            args.difficulty,
            args.next_step,
        ),
        encoding="utf-8",
    )

    rel_link = (Path("..") / "check-ins" / checkin_path.name).as_posix()
    summary_line = (
        f"- {now.date().isoformat()}: [Check-in {checkin_index}]({rel_link}) — {args.takeaway}"
    )
    body = append_to_section(body, CHECKIN_LOG_HEADING, summary_line)

    if args.difficulty:
        diff_count = int_meta(meta, "difficulty_count") + 1
        set_meta(lines, "difficulty_count", str(diff_count))
        body = append_to_section(
            body,
            DIFFICULTY_LOG_HEADING,
            f"- {now.date().isoformat()} (check-in {checkin_index}): {args.difficulty}",
        )

    set_meta(lines, "checkin_count", str(new_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    save_record(path, lines, body)
    print(checkin_path)


def log(args):
    root = default_logs_dir()
    ensure_dir(root)
    now = local_now()

    target_date = parse_date_arg(args.date) if args.date else now.date()
    target_time = parse_time_arg(args.time) if args.time else now.time()
    time_str = target_time.strftime("%H:%M")

    title = args.title.strip() if args.title else " ".join(args.text.strip().split())[:40] or "无题"

    path = root / f"log-{target_date.isoformat()}.md"
    if not path.exists():
        path.write_text(render_log_skeleton(target_date.isoformat(), now, args.tags), encoding="utf-8")

    lines, meta, body = load_record(path)
    body = _append_log_entry(body, time_str, title, args.text)

    new_count = int_meta(meta, "entry_count") + 1
    set_meta(lines, "entry_count", str(new_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))
    if args.tags:
        merged = union_tags(meta.get("tags", "[]"), args.tags)
        set_meta(lines, "tags", merged)

    save_record(path, lines, body)
    print(path)


def _load_task_records():
    root = default_tasks_dir()
    ensure_dir(root)
    records = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm_lines, body = split_frontmatter(text)
        if not fm_lines:
            continue
        meta = parse_frontmatter_lines(fm_lines)
        if meta.get("type") and meta.get("type") != "task":
            continue
        records.append((path, meta, body))
    return records


def _load_log_records():
    root = default_logs_dir()
    ensure_dir(root)
    records = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm_lines, body = split_frontmatter(text)
        if not fm_lines:
            continue
        meta = parse_frontmatter_lines(fm_lines)
        if meta.get("type") and meta.get("type") != "log":
            continue
        records.append((path, meta, body))
    return records


def _common_filters(meta, args):
    tags = parse_tags_field(meta.get("tags", ""))
    if args.tag and args.tag not in tags:
        return False
    if args.category and args.category != meta.get("primary_category", ""):
        return False
    return True


def _task_filter_for_mode(meta, args, now):
    if not _common_filters(meta, args):
        return False
    if args.priority and meta.get("priority") != args.priority:
        return False
    status = meta.get("status", "pending")
    if args.status and status != args.status:
        return False
    due = parse_dt(meta.get("due_at"))
    if args.mode == "overdue":
        return due is not None and due < now and status not in TERMINAL_STATUSES
    if args.mode == "due-today":
        anchor = parse_date_arg(args.date) if args.date else now.date()
        return due is not None and due.date() == anchor
    if args.mode == "due-soon":
        if due is None or status in TERMINAL_STATUSES:
            return False
        horizon = now + timedelta(days=args.days)
        return now <= due <= horizon
    if args.mode == "active":
        return status in ("pending", "in_progress", "blocked")
    if args.mode == "completed":
        return status == "done"
    if args.mode == "period":
        anchor = parse_date_arg(args.date) if args.date else now.date()
        start, end = period_range(args.period, anchor)
        updated = parse_dt(meta.get("updated_at"))
        if updated is None:
            return False
        return start <= updated.date() <= end
    return False


def _log_filter_for_mode(meta, args, now):
    if not _common_filters(meta, args):
        return False
    log_date_str = meta.get("date", "")
    try:
        log_date = date.fromisoformat(log_date_str)
    except ValueError:
        return False
    if args.mode == "period":
        anchor = parse_date_arg(args.date) if args.date else now.date()
        start, end = period_range(args.period, anchor)
        return start <= log_date <= end
    if args.mode == "due-today":
        anchor = parse_date_arg(args.date) if args.date else now.date()
        return log_date == anchor
    return False


def _sort_tasks(records, mode):
    far_future = datetime.max.replace(tzinfo=local_now().tzinfo)
    if mode in ("overdue", "due-today", "due-soon", "active"):
        return sorted(records, key=lambda r: parse_dt(r[1].get("due_at")) or far_future)
    if mode == "completed":
        far_past = datetime.min.replace(tzinfo=local_now().tzinfo)
        return sorted(records, key=lambda r: parse_dt(r[1].get("completed_at")) or far_past, reverse=True)
    if mode == "period":
        far_past = datetime.min.replace(tzinfo=local_now().tzinfo)
        return sorted(records, key=lambda r: parse_dt(r[1].get("updated_at")) or far_past, reverse=True)
    return records


def _sort_logs(records):
    return sorted(records, key=lambda r: r[1].get("date", ""), reverse=True)


def scan(args):
    now = local_now()

    if args.mode == "period" and not args.period:
        raise SystemExit("--mode period requires --period day|week|month")

    requested_type = args.type
    if requested_type == "all" and args.mode != "period":
        requested_type = "task"
    if args.mode != "period" and requested_type == "log" and args.mode != "due-today":
        requested_type = "task"

    output_lines = []

    if requested_type in ("task", "all"):
        tasks_in = [r for r in _load_task_records() if _task_filter_for_mode(r[1], args, now)]
        tasks_in = _sort_tasks(tasks_in, args.mode)
        for path, meta, body in tasks_in:
            title = title_from_body(body)
            output_lines.append(
                "\t".join([
                    "task",
                    meta.get("status", ""),
                    meta.get("due_at", ""),
                    meta.get("priority", ""),
                    meta.get("id", ""),
                    str(path),
                    title,
                ])
            )

    if requested_type in ("log", "all") and args.mode in ("period", "due-today"):
        logs_in = [r for r in _load_log_records() if _log_filter_for_mode(r[1], args, now)]
        logs_in = _sort_logs(logs_in)
        for path, meta, body in logs_in:
            entry_count = meta.get("entry_count", "0")
            output_lines.append(
                "\t".join([
                    "log",
                    meta.get("date", ""),
                    entry_count,
                    "-",
                    f"log-{meta.get('date', '')}",
                    str(path),
                    f"{entry_count} entries",
                ])
            )

    if args.limit and args.limit > 0:
        output_lines = output_lines[: args.limit]

    for line in output_lines:
        print(line)


def main():
    parser = argparse.ArgumentParser(
        description=f"Daily skill: tasks, logs, check-ins, scan. Records in {TASKS_DIR_DISPLAY} and siblings."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_task = sub.add_parser("task", help="Create a Markdown task record.")
    p_task.add_argument("--text", required=True, help="Task description (raw user text).")
    p_task.add_argument("--title", help="Optional Markdown title.")
    p_task.add_argument("--due", help="YYYY-MM-DD or YYYY-MM-DDTHH:MM(:SS)")
    p_task.add_argument("--source", default="manual")
    p_task.add_argument("--priority", choices=list(PRIORITIES), default="medium")
    p_task.add_argument("--category")
    p_task.add_argument("--tags", help="Comma-separated tags.")
    p_task.set_defaults(func=task)

    p_update = sub.add_parser("update", help="Update task fields and append logs.")
    p_update.add_argument("file", help="Markdown task file.")
    p_update.add_argument("--status", choices=list(TASK_STATUSES))
    p_update.add_argument("--due", help="New due date/datetime, or empty string to clear.")
    p_update.add_argument(
        "--postpone-reason",
        help="If set together with --due, append a Postponement Log line and bump postpone_count.",
    )
    p_update.add_argument("--priority", choices=list(PRIORITIES))
    p_update.add_argument("--category")
    p_update.add_argument("--tags", help="Comma-separated tags (replaces).")
    p_update.add_argument("--difficulty", help="Append a line to ## Difficulty Log.")
    p_update.add_argument("--note", help="Append a line to ## Notes.")
    p_update.set_defaults(func=update)

    p_checkin = sub.add_parser(
        "checkin", help="Log a stage-by-stage check-in for a task."
    )
    p_checkin.add_argument("file", help="Markdown task file.")
    p_checkin.add_argument("--topic", required=True)
    p_checkin.add_argument("--conversation", required=True)
    p_checkin.add_argument("--takeaway", required=True)
    p_checkin.add_argument("--difficulty", help="Optional surfaced difficulty (also appended to Difficulty Log).")
    p_checkin.add_argument("--next-step", dest="next_step", help="Optional next concrete step.")
    p_checkin.set_defaults(func=checkin)

    p_log = sub.add_parser("log", help="Append a daily log entry to today's (or --date) log file.")
    p_log.add_argument("--text", required=True)
    p_log.add_argument("--title")
    p_log.add_argument("--time", help="HH:MM (defaults to now).")
    p_log.add_argument("--date", help="YYYY-MM-DD (defaults to today, local).")
    p_log.add_argument("--tags", help="Comma-separated tags (union'd into the day's tag set).")
    p_log.set_defaults(func=log)

    p_scan = sub.add_parser("scan", help="Query tasks (and logs in period mode).")
    p_scan.add_argument("--mode", choices=list(SCAN_MODES), default="active")
    p_scan.add_argument("--period", choices=list(PERIODS))
    p_scan.add_argument("--date", help="Anchor date YYYY-MM-DD for date-relative modes.")
    p_scan.add_argument("--days", type=int, default=3, help="Used when --mode due-soon.")
    p_scan.add_argument("--type", choices=list(SCAN_TYPES), default="all")
    p_scan.add_argument("--tag")
    p_scan.add_argument("--category")
    p_scan.add_argument("--priority", choices=list(PRIORITIES))
    p_scan.add_argument("--status", choices=list(TASK_STATUSES))
    p_scan.add_argument("--limit", type=int, default=0, help="Max rows (0 = unlimited).")
    p_scan.set_defaults(func=scan)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
