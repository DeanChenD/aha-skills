#!/usr/bin/env python3
import argparse
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from aha_md import (  # noqa: E402
    DIFFICULTY_LOG_HEADING,
    UNTRUSTED_CONTENT_BANNER,
    WORKSPACE_DIR_NAME,
    add_text_input_args,
    append_to_section,
    assert_record_path,
    assert_workspace_path,
    atomic_write,
    check_manifest_consistency,
    doctor_workspace,
    ensure_dir,
    ensure_workspace_manifest,
    escape_pseudo_h2,
    format_tags,
    int_meta,
    iter_record_paths,
    iter_task_difficulties_in_range,
    load_record,
    local_now,
    locked_record,
    parse_dt,
    parse_frontmatter_lines,
    parse_tags_field,
    period_id,
    period_range,
    read_section,
    read_text_or_warn,
    render_frontmatter,
    render_untrusted_inline,
    resolve_text_input,
    sanitize_single_line,
    schema_version_compatible,
    task_in_period,
    verify_unchanged_since,
    save_record,
    set_meta,
    slugify,
    split_frontmatter,
    title_from,
    title_from_body,
    unique_path,
    workspace_dir,
)


TASKS_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/daily/tasks"

DESCRIPTION_HEADING = "Description 描述"
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


def default_tasks_dir():
    return workspace_dir("daily", "tasks")


def default_logs_dir():
    return workspace_dir("daily", "logs")


def default_checkins_dir():
    return workspace_dir("daily", "check-ins")


def default_reviews_dir():
    return workspace_dir("daily", "reviews")


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
    safe_title = escape_pseudo_h2(sanitize_single_line(title))
    frontmatter = render_frontmatter([
        ("id", task_id),
        ("schema_version", "1"),
        ("type", "task"),
        ("status", "pending"),
        ("created_at", timestamp),
        ("updated_at", timestamp),
        ("due_at", due_at_iso),
        ("completed_at", ""),
        ("priority", priority),
        ("source", source),
        ("primary_category", category or ""),
        ("tags", format_tags(tags)),
        ("checkin_count", "0"),
        ("postpone_count", "0"),
        ("difficulty_count", "0"),
    ])
    return f"""{frontmatter}
# {safe_title}

## {DESCRIPTION_HEADING}

{description}

## {DIFFICULTY_LOG_HEADING}

## {POSTPONEMENT_LOG_HEADING}

## {CHECKIN_LOG_HEADING}

## {NOTES_HEADING}
"""


def render_log_skeleton(date_str, now, tags):
    timestamp = now.isoformat(timespec="seconds")
    safe_date = sanitize_single_line(date_str)
    frontmatter = render_frontmatter([
        ("date", date_str),
        ("schema_version", "1"),
        ("type", "log"),
        ("created_at", timestamp),
        ("updated_at", timestamp),
        ("entry_count", "0"),
        ("tags", format_tags(tags)),
    ])
    return f"""{frontmatter}
# {safe_date}
"""


def render_checkin_body(checkin_id, parent_task_id, now, topic, conversation, takeaway, difficulty, next_step):
    timestamp = now.isoformat(timespec="seconds")
    safe_topic = escape_pseudo_h2(topic)
    safe_conversation = escape_pseudo_h2(conversation)
    safe_takeaway = escape_pseudo_h2(takeaway)
    safe_difficulty = escape_pseudo_h2(difficulty.strip()) if difficulty else "(none)"
    safe_next = escape_pseudo_h2(next_step.strip()) if next_step else "(none)"
    safe_topic_title = escape_pseudo_h2(sanitize_single_line(topic))
    frontmatter = render_frontmatter([
        ("checkin_id", checkin_id),
        ("schema_version", "1"),
        ("parent_task_id", parent_task_id),
        ("created_at", timestamp),
    ])
    return f"""{frontmatter}
# Check-in: {safe_topic_title}

## Prompt 起点

{safe_topic}

## Conversation 对话原文

{safe_conversation}

## Difficulties Surfaced

{safe_difficulty}

## Takeaway 收获

{safe_takeaway}

## Next Step

{safe_next}
"""


def _append_log_entry(body, time_str, title, text):
    body = body.rstrip() + "\n\n"
    safe_time = sanitize_single_line(time_str)
    safe_title = sanitize_single_line(title)
    # Preserve leading whitespace so code blocks / ASCII art keep their
    # indentation. Only normalize trailing newlines so we end on exactly one.
    safe_text = escape_pseudo_h2(text).rstrip("\n")
    body += f"## {safe_time} — {safe_title}\n\n{safe_text}\n"
    return body


def task(args):
    root = default_tasks_dir()
    ensure_dir(root)
    ensure_workspace_manifest()
    text = resolve_text_input(args, "text")
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(text, fallback="task")
    task_id, path = unique_path(root, f"task-{stamp}-{slug}")
    title = args.title or title_from(text, fallback="Untitled Task")
    due_iso = parse_due(args.due) if args.due else ""
    body = render_task_skeleton(
        task_id,
        title,
        escape_pseudo_h2(text),
        now,
        due_iso,
        args.priority,
        args.source,
        args.category,
        args.tags,
    )
    atomic_write(path, body)
    print(path)


def update(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "daily", subdir="tasks", required_type="task")
    with locked_record(path):
        _do_update(path, args)
    print(path)


def _do_update(path, args):
    lines, meta, body = load_record(path)
    pre_mtime = path.stat().st_mtime
    now = local_now()

    if args.category is not None:
        set_meta(lines, "primary_category", args.category)
    if args.tags is not None:
        set_meta(lines, "tags", format_tags(args.tags))
    if args.priority:
        set_meta(lines, "priority", args.priority)

    if args.status:
        old_status = meta.get("status", "")
        set_meta(lines, "status", args.status)
        if args.status == "done":
            # Only stamp completed_at on the *transition* to done. A
            # repeated `--status done` (e.g. a re-run from cron) must
            # preserve the original completion time, not overwrite it.
            if old_status != "done":
                set_meta(lines, "completed_at", now.isoformat(timespec="seconds"))
        else:
            # Reopening (done → pending / in_progress / blocked / dropped)
            # clears completed_at so period inclusion treats the task as
            # active again.
            if old_status == "done":
                set_meta(lines, "completed_at", "")

    if args.due is not None:
        new_due_iso = parse_due(args.due) if args.due else ""
        old_due = meta.get("due_at", "")
        # README:153 / SKILL.md require an explicit reason when an
        # existing due moves. Silent re-dating loses the postponement
        # history. --correction is the bypass for fat-finger recording
        # mistakes (no log entry, no count bump).
        moving_existing_due = bool(old_due) and new_due_iso != old_due
        if moving_existing_due and not args.postpone_reason and not args.correction:
            raise SystemExit(
                "Refusing to change due_at without a reason.\n"
                "  --postpone-reason \"...\" to log a postponement, or\n"
                "  --correction to fix a data-entry mistake (no log, no count bump)."
            )
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
    verify_unchanged_since(path, pre_mtime, force=getattr(args, "force", False))
    save_record(path, lines, body)


def checkin(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "daily", subdir="tasks", required_type="task")
    with locked_record(path):
        checkin_path = _do_checkin(path, args)
    print(checkin_path)


def _do_checkin(path, args):
    lines, meta, body = load_record(path)
    pre_mtime = path.stat().st_mtime
    now = local_now()

    parent_id = meta.get("id") or path.stem
    new_count = int_meta(meta, "checkin_count") + 1
    checkin_index = f"{new_count:03d}"
    base_checkin_id = f"{parent_id}-checkin-{checkin_index}"

    topic = resolve_text_input(args, "topic")
    conversation = resolve_text_input(args, "conversation")
    takeaway = resolve_text_input(args, "takeaway")
    difficulty = resolve_text_input(args, "difficulty")
    next_step = resolve_text_input(args, "next-step")

    checkins_dir = default_checkins_dir()
    ensure_dir(checkins_dir)
    # P1#12: reserve atomically. If a prior crash left a checkin-001 on
    # disk while the parent's checkin_count rolled back, the reserved
    # path bumps to `-2` instead of clobbering the orphan.
    checkin_id, checkin_path = unique_path(checkins_dir, base_checkin_id)
    checkin_body = render_checkin_body(
        checkin_id,
        parent_id,
        now,
        topic,
        conversation,
        takeaway,
        difficulty,
        next_step,
    )

    rel_link = (Path("..") / "check-ins" / checkin_path.name).as_posix()
    display_index = (
        checkin_id.split("-checkin-", 1)[1]
        if "-checkin-" in checkin_id
        else checkin_index
    )
    summary_line = (
        f"- {now.date().isoformat()}: [Check-in {display_index}]({rel_link}) — {takeaway}"
    )
    body = append_to_section(body, CHECKIN_LOG_HEADING, summary_line)

    if difficulty:
        diff_count = int_meta(meta, "difficulty_count") + 1
        set_meta(lines, "difficulty_count", str(diff_count))
        body = append_to_section(
            body,
            DIFFICULTY_LOG_HEADING,
            f"- {now.date().isoformat()} (check-in {display_index}): {difficulty}",
        )

    set_meta(lines, "checkin_count", str(new_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    try:
        verify_unchanged_since(path, pre_mtime, force=getattr(args, "force", False))
        save_record(path, lines, body)
    except BaseException:
        try:
            if checkin_path.exists() and checkin_path.stat().st_size == 0:
                checkin_path.unlink()
        except OSError:
            pass
        raise
    atomic_write(checkin_path, checkin_body)
    return checkin_path


def log(args):
    root = default_logs_dir()
    ensure_dir(root)
    ensure_workspace_manifest()
    text = resolve_text_input(args, "text")
    now = local_now()

    target_date = parse_date_arg(args.date) if args.date else now.date()
    target_time = parse_time_arg(args.time) if args.time else now.time()
    time_str = target_time.strftime("%H:%M")

    title = args.title.strip() if args.title else " ".join(text.strip().split())[:40] or "无题"

    path = root / f"log-{target_date.isoformat()}.md"

    # Lock from skeleton-init through append: cron + chat could both observe
    # path.exists() == False, both write skeleton (last writer wins, first
    # writer's empty skeleton is fine), but their subsequent
    # load → append → save would race and clobber the prior entry.
    with locked_record(path):
        if not path.exists():
            atomic_write(path, render_log_skeleton(target_date.isoformat(), now, args.tags))
        lines, meta, body = load_record(path)
        body = _append_log_entry(body, time_str, title, text)

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
    for path in iter_record_paths(root):
        text = read_text_or_warn(path)
        if text is None:
            continue
        fm_lines, body = split_frontmatter(text)
        if not fm_lines:
            continue
        meta = parse_frontmatter_lines(fm_lines)
        if not schema_version_compatible(meta, path=path):
            continue
        if meta.get("type") and meta.get("type") != "task":
            continue
        records.append((path, meta, body))
    return records


def _load_log_records():
    root = default_logs_dir()
    ensure_dir(root)
    records = []
    for path in iter_record_paths(root):
        text = read_text_or_warn(path)
        if text is None:
            continue
        fm_lines, body = split_frontmatter(text)
        if not fm_lines:
            continue
        meta = parse_frontmatter_lines(fm_lines)
        if not schema_version_compatible(meta, path=path):
            continue
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
        # P2#14: by default treat done/dropped as out of "due today" — a
        # task whose due_at lands today but is already finished should
        # not show up in the day's surface. Users wanting historical
        # done-today review go through --status done explicitly.
        if due is None:
            return False
        if status in TERMINAL_STATUSES and not args.status:
            return False
        anchor = parse_date_arg(args.date) if args.date else now.date()
        return due.date() == anchor
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
        return task_in_period(meta, start, end)
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
    if args.mode not in ("period", "due-today") and requested_type in ("all", "log"):
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


def _collect_difficulties_in_range(start, end):
    return list(iter_task_difficulties_in_range(_load_task_records(), start, end))


def _render_review_snapshot(start, end):
    """Single-source snapshot of daily/. Mirrors reflect.save's daily portion
    but covers all the tasks/logs/difficulties of this period in one view."""
    tasks = [r for r in _load_task_records()]
    tasks_in = []
    for path, meta, body in tasks:
        if task_in_period(meta, start, end):
            tasks_in.append((path, meta, body))

    completed_in = [(p, m, b) for p, m, b in tasks_in if m.get("status") == "done"]
    active_after = [(p, m, b) for p, m, b in tasks_in if m.get("status") in ("pending", "in_progress", "blocked")]
    dropped_in = [(p, m, b) for p, m, b in tasks_in if m.get("status") == "dropped"]

    logs_in = []
    for path, meta, body in _load_log_records():
        try:
            log_date = date.fromisoformat(meta.get("date", ""))
        except ValueError:
            continue
        if start <= log_date <= end:
            logs_in.append((path, meta, body))
    logs_in.sort(key=lambda r: r[1].get("date", ""))

    difficulties = _collect_difficulties_in_range(start, end)

    lines = [UNTRUSTED_CONTENT_BANNER, ""]
    lines.append(f"### Tasks touched ({len(tasks_in)} touched, {len(completed_in)} done, {len(dropped_in)} dropped)")
    if tasks_in:
        for _, meta, body in tasks_in:
            due = meta.get("due_at", "")[:10] or "-"
            lines.append(
                f"- {meta.get('status', '?'):<11} | due {due} | "
                f"{meta.get('id', '')} — {render_untrusted_inline(title_from_body(body))}"
            )
    else:
        lines.append("- (none in range)")
    lines.append("")

    lines.append(f"### Active by end of range ({len(active_after)})")
    if active_after:
        for _, meta, body in active_after:
            due = meta.get("due_at", "")[:10] or "-"
            lines.append(
                f"- {meta.get('status', '?'):<11} | due {due} | "
                f"{meta.get('id', '')} — {render_untrusted_inline(title_from_body(body))}"
            )
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append(f"### Logs ({len(logs_in)})")
    if logs_in:
        for _, meta, _body in logs_in:
            tags = parse_tags_field(meta.get("tags", ""))
            tag_str = ", ".join(render_untrusted_inline(t) for t in tags) if tags else "-"
            lines.append(
                f"- {meta.get('date', '?')} | {meta.get('entry_count', '0')} entries "
                f"| tags: [{tag_str}]"
            )
    else:
        lines.append("- (none in range)")
    lines.append("")

    lines.append(f"### Difficulties ({len(difficulties)})")
    if difficulties:
        for d, task_id, _p, _t, text in difficulties:
            lines.append(
                f"- {d.isoformat()} ({task_id}): {render_untrusted_inline(text)}"
            )
    else:
        lines.append("- (none in range)")

    return "\n".join(lines)


def review(args):
    anchor_str = args.date
    try:
        anchor = date.fromisoformat(anchor_str) if anchor_str else local_now().date()
    except ValueError:
        raise SystemExit(f"Invalid --date: {anchor_str}")
    start, end = period_range(args.period, anchor)
    pid = period_id(args.period, start, end)

    root = default_reviews_dir()
    ensure_dir(root)
    review_id, path = unique_path(root, f"review-{pid}")

    snapshot_md = _render_review_snapshot(start, end)
    now = local_now()
    frontmatter = render_frontmatter([
        ("review_id", review_id),
        ("type", "review"),
        ("schema_version", "1"),
        ("period", args.period),
        ("range_start", start.isoformat()),
        ("range_end", end.isoformat()),
        ("created_at", now.isoformat(timespec="seconds")),
    ])
    body = f"""{frontmatter}
# Review: {pid}

## 范围

{start.isoformat()} → {end.isoformat()}

## Source Snapshot

{snapshot_md}

## 模式与启示

<待与用户讨论后填写；agent 不要单方面预填。读完上面的 Source Snapshot 之后与用户多轮交流，再写下 3-7 条本周观察。>

## 下阶段意图

<待与用户讨论后填写；agent 不要单方面预填。1-3 条具体的"意图"（不是 goals）。>
"""
    atomic_write(path, body)
    print(path)


def main():
    parser = argparse.ArgumentParser(
        description=f"Daily skill: tasks, logs, check-ins, scan. Records in {TASKS_DIR_DISPLAY} and siblings."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_task = sub.add_parser("task", help="Create a Markdown task record.")
    add_text_input_args(p_task, "text", required=True, help_text="Task description (raw user text).")
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
        help="Required when moving an existing due_at; appends a Postponement Log line and bumps postpone_count.",
    )
    p_update.add_argument(
        "--correction", action="store_true",
        help="Bypass --postpone-reason requirement for data-entry corrections (no log, no count bump).",
    )
    p_update.add_argument("--priority", choices=list(PRIORITIES))
    p_update.add_argument("--category")
    p_update.add_argument("--tags", help="Comma-separated tags (replaces).")
    p_update.add_argument("--difficulty", help="Append a line to ## Difficulty Log.")
    p_update.add_argument("--note", help="Append a line to ## Notes.")
    p_update.add_argument(
        "--force", action="store_true",
        help="Skip cross-host mtime conflict check.",
    )
    p_update.set_defaults(func=update)

    p_checkin = sub.add_parser(
        "checkin", help="Log a stage-by-stage check-in for a task."
    )
    p_checkin.add_argument("file", help="Markdown task file.")
    add_text_input_args(p_checkin, "topic", required=True)
    add_text_input_args(p_checkin, "conversation", required=True)
    add_text_input_args(p_checkin, "takeaway", required=True)
    add_text_input_args(p_checkin, "difficulty", required=False, help_text="Optional surfaced difficulty (also appended to Difficulty Log).")
    add_text_input_args(p_checkin, "next-step", required=False, help_text="Optional next concrete step.")
    p_checkin.add_argument(
        "--force", action="store_true",
        help="Skip cross-host mtime conflict check.",
    )
    p_checkin.set_defaults(func=checkin)

    p_log = sub.add_parser("log", help="Append a daily log entry to today's (or --date) log file.")
    add_text_input_args(p_log, "text", required=True)
    p_log.add_argument("--title")
    p_log.add_argument("--time", help="HH:MM (defaults to now).")
    p_log.add_argument("--date", help="YYYY-MM-DD (defaults to today, local).")
    p_log.add_argument("--tags", help="Comma-separated tags (union'd into the day's tag set).")
    p_log.set_defaults(func=log)

    p_review = sub.add_parser(
        "review",
        help="Write a daily review skeleton pre-filled with this period's tasks/logs/difficulties (write-once, never overwrites).",
    )
    p_review.add_argument("--period", choices=list(PERIODS), required=True)
    p_review.add_argument("--date", help="Anchor date YYYY-MM-DD (default: today, local).")
    p_review.set_defaults(func=review)

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

    p_doctor = sub.add_parser(
        "doctor",
        help="Inspect workspace anchor, manifest, and timezone consistency.",
    )
    p_doctor.set_defaults(func=lambda _args: sys.exit(doctor_workspace()))

    args = parser.parse_args()
    if args.cmd != "doctor":
        check_manifest_consistency()
    args.func(args)


if __name__ == "__main__":
    main()
