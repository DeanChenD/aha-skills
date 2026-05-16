#!/usr/bin/env python3
import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from aha_md import (  # noqa: E402
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
    load_record,
    local_now,
    locked_record,
    parse_dt,
    parse_frontmatter,
    render_frontmatter,
    replace_section,
    resolve_text_input,
    sanitize_single_line,
    save_record,
    schema_version_compatible,
    set_meta,
    slugify,
    split_frontmatter,
    title_from,
    unique_path,
    verify_unchanged_since,
    workspace_dir,
)


ACTIVE_STATUSES = {"inbox", "researching", "planning"}
PAUSED_STATUS = "paused"
STATUSES = {"inbox", "researching", "planning", "paused", "completed", "killed"}
IDEA_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/idea/idea-md"

SUMMARY_HEADING = "Summary"
CLASSIFICATION_HEADING = "Classification"
RESEARCH_TASK_HEADING = "Research Task"
PLAN_HEADING = "Plan"
QUESTIONS_HEADING = "Questions For User"
DECISION_LOG_HEADING = "Decision Log"
NOTES_HEADING = "Notes"


def default_idea_dir():
    return workspace_dir("idea", "idea-md")


def normalize_datetime(value):
    if not value:
        return ""
    parsed = parse_dt(value)
    if parsed is None:
        raise SystemExit(f"Invalid datetime: {value}")
    return parsed.isoformat(timespec="seconds")


def capture(args):
    root = default_idea_dir()
    ensure_dir(root)
    ensure_workspace_manifest()
    text = resolve_text_input(args, "text")
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(text, fallback="idea")
    idea_id, path = unique_path(root, f"idea-{stamp}-{slug}")
    title = args.title or title_from(text, fallback="Untitled Idea")
    timestamp = now.isoformat(timespec="seconds")
    next_review_at = normalize_datetime(args.next_review_at)
    raw_text_safe = escape_pseudo_h2(text)
    safe_title = escape_pseudo_h2(sanitize_single_line(title))
    frontmatter = render_frontmatter([
        ("id", idea_id),
        ("schema_version", "1"),
        ("status", args.status),
        ("created_at", timestamp),
        ("updated_at", timestamp),
        ("next_review_at", next_review_at),
        ("last_prompted_at", ""),
        ("review_count", "0"),
        ("priority", args.priority),
        ("source", args.source),
        ("primary_category", args.category or ""),
        ("tags", format_tags(args.tags)),
    ])
    body = f"""{frontmatter}
# {safe_title}

## Raw Idea

{raw_text_safe}

## {SUMMARY_HEADING}

TBD

## {CLASSIFICATION_HEADING}

- Primary category:
- Tags:
- Confidence:

## {RESEARCH_TASK_HEADING}

TBD

## {PLAN_HEADING}

- [ ] Clarify:
- [ ] Research:
- [ ] Validate:
- [ ] Draft:
- [ ] Decide:

## {QUESTIONS_HEADING}

1.
2.
3.

## {DECISION_LOG_HEADING}

- {now.date().isoformat()}: Captured.

## {NOTES_HEADING}
"""
    atomic_write(path, body)
    print(path)


def enrich(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "idea", subdir="idea-md")
    with locked_record(path):
        _do_enrich(path, args)
    print(path)


def _do_enrich(path, args):
    lines, _meta, body = load_record(path)
    pre_mtime = path.stat().st_mtime
    now = local_now()

    section_inputs = [
        (SUMMARY_HEADING, resolve_text_input(args, "summary")),
        (CLASSIFICATION_HEADING, resolve_text_input(args, "classification")),
        (RESEARCH_TASK_HEADING, resolve_text_input(args, "research-task")),
        (PLAN_HEADING, resolve_text_input(args, "plan")),
        (QUESTIONS_HEADING, resolve_text_input(args, "questions")),
    ]
    metadata_changed = any([
        args.status,
        args.category is not None,
        args.tags is not None,
        args.priority,
        args.next_review_at is not None,
    ])
    if not metadata_changed and all(value is None for _heading, value in section_inputs):
        raise SystemExit(
            "Nothing to enrich. Provide at least one section field "
            "(--summary/--classification/--research-task/--plan/--questions) "
            "or metadata field."
        )

    for heading, value in section_inputs:
        if value is not None:
            body = replace_section(body, heading, value.strip())

    if args.status:
        set_meta(lines, "status", args.status)
    if args.category is not None:
        set_meta(lines, "primary_category", args.category)
    if args.tags is not None:
        set_meta(lines, "tags", format_tags(args.tags))
    if args.priority:
        set_meta(lines, "priority", args.priority)
    if args.next_review_at is not None:
        set_meta(lines, "next_review_at", normalize_datetime(args.next_review_at))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    verify_unchanged_since(path, pre_mtime, force=args.force)
    save_record(path, lines, body)


def update(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "idea", subdir="idea-md")
    with locked_record(path):
        _do_update(path, args)
    print(path)


def _do_update(path, args):
    lines, meta, body = load_record(path)
    pre_mtime = path.stat().st_mtime

    now = local_now()
    if args.status:
        set_meta(lines, "status", args.status)
    if args.category is not None:
        set_meta(lines, "primary_category", args.category)
    if args.tags is not None:
        set_meta(lines, "tags", format_tags(args.tags))
    if args.priority:
        set_meta(lines, "priority", args.priority)
    if args.next_review_at is not None:
        set_meta(lines, "next_review_at", normalize_datetime(args.next_review_at))
    if args.prompted:
        set_meta(lines, "last_prompted_at", now.isoformat(timespec="seconds"))
    if args.bump_review:
        review_count = int_meta(meta, "review_count") + 1
        set_meta(lines, "review_count", str(review_count))
    elif args.review_count is not None:
        set_meta(lines, "review_count", str(args.review_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    decision_text = resolve_text_input(args, "decision")
    if decision_text:
        body = append_to_section(body, DECISION_LOG_HEADING, f"- {now.date().isoformat()}: {decision_text}")
    note_text = resolve_text_input(args, "note")
    if note_text:
        body = append_to_section(body, NOTES_HEADING, f"- {now.date().isoformat()}: {note_text}")

    verify_unchanged_since(path, pre_mtime, force=args.force)
    save_record(path, lines, body)


def scan(args):
    root = default_idea_dir()
    ensure_dir(root)
    now = local_now()
    cutoff = now - timedelta(days=args.stale_days)
    cooldown_until_now = now - timedelta(hours=args.cooldown_hours) if args.cooldown_hours > 0 else None
    rows = []
    for path in iter_record_paths(root):
        meta = parse_frontmatter(path)
        if not schema_version_compatible(meta, path=path):
            continue
        if not meta.get("id") or not meta.get("status"):
            continue
        status = meta.get("status", "").strip()
        if args.include_completed:
            eligible = True
        elif status == PAUSED_STATUS:
            eligible = args.include_paused
        else:
            eligible = status in ACTIVE_STATUSES
        if not eligible:
            continue
        # Cooldown: skip ideas that were prompted within the cooldown window so a
        # scheduler doesn't re-surface the same idea every run.
        last_prompted = parse_dt(meta.get("last_prompted_at"))
        if cooldown_until_now is not None and last_prompted is not None and last_prompted >= cooldown_until_now:
            continue
        updated_at = parse_dt(meta.get("updated_at"))
        next_review_at = parse_dt(meta.get("next_review_at"))
        due_for_review = next_review_at is not None and next_review_at <= now
        stale = updated_at is None or updated_at <= cutoff
        if due_for_review or (stale and next_review_at is None):
            rows.append((path, status or "unknown", meta.get("updated_at", ""), meta.get("next_review_at", "")))

    # P1#16: scan defaults to read-only. Scheduler (cron) opts into the
    # last_prompted_at mark explicitly with --mark-prompted, so a curious
    # `scan` from the terminal never burns the cron cooldown.
    should_mark = args.mark_prompted and not args.peek
    for path, status, updated, next_review in rows:
        if should_mark:
            # Mark this idea as prompted now, so the next scan within
            # cooldown will skip it. Lock so a parallel update doesn't lose
            # writes against this surface mark.
            try:
                with locked_record(path):
                    lines, body = split_frontmatter(path.read_text(encoding="utf-8"))
                    if lines:
                        set_meta(lines, "last_prompted_at", now.isoformat(timespec="seconds"))
                        save_record(path, lines, body)
            except (OSError, UnicodeDecodeError):
                pass
        print(f"{status}\t{updated}\t{next_review}\t{path}")


def main():
    parser = argparse.ArgumentParser(
        description=f"Capture and scan Markdown idea records in {IDEA_DIR_DISPLAY}."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_capture = sub.add_parser("capture", help="Create a Markdown idea record.")
    add_text_input_args(p_capture, "text", required=True, help_text="Exact raw idea text.")
    p_capture.add_argument("--title", help="Optional Markdown title.")
    p_capture.add_argument("--status", choices=sorted(STATUSES), default="inbox")
    p_capture.add_argument("--source", default="manual")
    p_capture.add_argument("--priority", choices=["low", "medium", "high"], default="medium")
    p_capture.add_argument("--category", help="Primary category.")
    p_capture.add_argument("--tags", help="Comma-separated tags.")
    p_capture.add_argument("--next-review-at", help="ISO datetime or date for the next review.")
    p_capture.set_defaults(func=capture)

    p_scan = sub.add_parser("scan", help="List stale Markdown idea records.")
    p_scan.add_argument("--stale-days", type=int, default=7)
    p_scan.add_argument("--include-paused", action="store_true")
    p_scan.add_argument("--include-completed", action="store_true")
    p_scan.add_argument(
        "--cooldown-hours", type=int, default=24,
        help="Skip ideas whose last_prompted_at is within this window. "
             "Set 0 to disable. Default 24h prevents cron from re-pinging "
             "the same idea every run.",
    )
    p_scan.add_argument(
        "--mark-prompted", action="store_true",
        help="Stamp last_prompted_at on each surfaced idea. Default OFF —"
             " scheduler / cron must opt in so an interactive `scan` doesn't"
             " accidentally burn the cron cooldown.",
    )
    p_scan.add_argument(
        "--peek", action="store_true",
        help="(Deprecated; scan is read-only by default. Kept as a no-op"
             " override that forces read-only even if --mark-prompted is set.)",
    )
    p_scan.set_defaults(func=scan)

    p_enrich = sub.add_parser(
        "enrich",
        help="Replace idea body sections (summary/classification/research task/plan/questions).",
    )
    p_enrich.add_argument("file", help="Markdown idea file to enrich.")
    add_text_input_args(
        p_enrich, "summary", required=False,
        help_text="Replace ## Summary.",
    )
    add_text_input_args(
        p_enrich, "classification", required=False,
        help_text="Replace ## Classification.",
    )
    add_text_input_args(
        p_enrich, "research-task", required=False,
        help_text="Replace ## Research Task.",
    )
    add_text_input_args(
        p_enrich, "plan", required=False,
        help_text="Replace ## Plan.",
    )
    add_text_input_args(
        p_enrich, "questions", required=False,
        help_text="Replace ## Questions For User.",
    )
    p_enrich.add_argument("--status", choices=sorted(STATUSES))
    p_enrich.add_argument("--category")
    p_enrich.add_argument("--tags", help="Comma-separated tags.")
    p_enrich.add_argument("--priority", choices=["low", "medium", "high"])
    p_enrich.add_argument("--next-review-at", help="ISO datetime or date for the next review. Empty string clears it.")
    p_enrich.add_argument(
        "--force", action="store_true",
        help="Skip the cross-host mtime conflict check.",
    )
    p_enrich.set_defaults(func=enrich)

    p_update = sub.add_parser("update", help="Update idea frontmatter and append logs.")
    p_update.add_argument("file", help="Markdown idea file to update.")
    p_update.add_argument("--status", choices=sorted(STATUSES))
    p_update.add_argument("--category")
    p_update.add_argument("--tags", help="Comma-separated tags.")
    p_update.add_argument("--priority", choices=["low", "medium", "high"])
    p_update.add_argument("--next-review-at", help="ISO datetime or date for the next review. Empty string clears it.")
    p_update.add_argument("--prompted", action="store_true", help="Set last_prompted_at to now.")
    p_update.add_argument("--bump-review", action="store_true", help="Increment review_count by one.")
    p_update.add_argument("--review-count", type=int)
    add_text_input_args(
        p_update, "decision", required=False,
        help_text="Append an entry to Decision Log.",
    )
    add_text_input_args(
        p_update, "note", required=False,
        help_text="Append an entry to Notes.",
    )
    p_update.add_argument(
        "--force", action="store_true",
        help="Skip the cross-host mtime conflict check; overwrite even if "
             "the file was modified by another writer since this command loaded it.",
    )
    p_update.set_defaults(func=update)

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
