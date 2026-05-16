#!/usr/bin/env python3
import argparse
import random
import sys
from datetime import datetime
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
    parse_frontmatter_lines,
    parse_tags_field,
    read_section,
    render_frontmatter,
    replace_section,
    resolve_text_input,
    sanitize_single_line,
    schema_version_compatible,
    save_record,
    set_meta,
    slugify,
    split_frontmatter,
    title_from_body,
    unique_path,
    workspace_dir,
)


DAO_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/dao/dao-md"

RAW_HEADING = "Raw 原始感悟"
REFINED_HEADING = "Refined 提炼沉淀"
CONTEXT_HEADING = "Context 触发情境"
DISCUSSION_HEADING = "Discussion 探讨"
REFINEMENT_LOG_HEADING = "Refinement Log"
NOTES_HEADING = "Notes"

REFINED_PLACEHOLDER = "TBD"
SCAN_MODES = ("random", "oldest", "least-reviewed")


def default_dao_dir():
    return workspace_dir("dao", "dao-md")


def default_sessions_dir():
    return workspace_dir("dao", "sessions")


def title_from_text(text):
    first = " ".join(text.strip().split())
    if not first:
        return "Untitled Dao"
    return first[:80]


def render_dao_skeleton(dao_id, title, raw_text, now, source, priority, category, tags):
    timestamp = now.isoformat(timespec="seconds")
    safe_title = escape_pseudo_h2(sanitize_single_line(title))
    frontmatter = render_frontmatter([
        ("id", dao_id),
        ("schema_version", "1"),
        ("created_at", timestamp),
        ("updated_at", timestamp),
        ("last_reviewed_at", ""),
        ("review_count", "0"),
        ("refine_count", "0"),
        ("discussion_count", "0"),
        ("priority", priority),
        ("source", source),
        ("primary_category", category or ""),
        ("tags", format_tags(tags)),
    ])
    return f"""{frontmatter}
# {safe_title}

## {RAW_HEADING}

{raw_text}

## {REFINED_HEADING}

{REFINED_PLACEHOLDER}

## {CONTEXT_HEADING}

{REFINED_PLACEHOLDER}

## {DISCUSSION_HEADING}

## {REFINEMENT_LOG_HEADING}

## {NOTES_HEADING}
"""


def capture(args):
    root = default_dao_dir()
    ensure_dir(root)
    ensure_workspace_manifest()
    text = resolve_text_input(args, "text")
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(text, fallback="dao")
    dao_id, path = unique_path(root, f"dao-{stamp}-{slug}")
    title = args.title or title_from_text(text)
    body = render_dao_skeleton(
        dao_id,
        title,
        escape_pseudo_h2(text),
        now,
        args.source,
        args.priority,
        args.category,
        args.tags,
    )
    atomic_write(path, body)
    print(path)


def refine(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "dao", subdir="dao-md")
    with locked_record(path):
        _do_refine(path, args)
    print(path)


def _do_refine(path, args):
    lines, meta, body = load_record(path)
    now = local_now()

    old_count = int_meta(meta, "refine_count")
    new_count = old_count + 1

    current_refined = read_section(body, REFINED_HEADING)
    if current_refined and current_refined != REFINED_PLACEHOLDER:
        log_line = f"- {now.date().isoformat()} (v{old_count}): {current_refined}"
        body = append_to_section(body, REFINEMENT_LOG_HEADING, log_line)

    text = resolve_text_input(args, "text")
    body = replace_section(body, REFINED_HEADING, text.strip())

    set_meta(lines, "refine_count", str(new_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))
    # refine is an active engagement with the record — stamp it so
    # scan --mode least-reviewed will not keep re-surfacing it.
    _bump_review(lines, meta, now)

    save_record(path, lines, body)


def discuss(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "dao", subdir="dao-md")
    with locked_record(path):
        session_path = _do_discuss(path, args)
    print(session_path)


def _do_discuss(path, args):
    lines, meta, body = load_record(path)
    now = local_now()

    parent_id = meta.get("id") or path.stem
    new_count = int_meta(meta, "discussion_count") + 1
    session_index = f"{new_count:03d}"
    base_session_id = f"{parent_id}-session-{session_index}"

    sessions_dir = default_sessions_dir()
    ensure_dir(sessions_dir)
    # P1#12: reserve atomically. If a prior crash left a session-001 on
    # disk while the parent's discussion_count was rolled back, the
    # reserved path bumps to `-2` instead of clobbering the orphan.
    session_id, session_path = unique_path(sessions_dir, base_session_id)

    timestamp = now.isoformat(timespec="seconds")
    topic = resolve_text_input(args, "topic")
    conversation = resolve_text_input(args, "conversation")
    takeaway = resolve_text_input(args, "takeaway")
    safe_topic = escape_pseudo_h2(topic)
    safe_conversation = escape_pseudo_h2(conversation)
    safe_takeaway = escape_pseudo_h2(takeaway)
    session_body = f"""---
session_id: {session_id}
schema_version: 1
parent_dao_id: {parent_id}
created_at: {timestamp}
---

# Discussion: {safe_topic}

## Prompt 起点

{safe_topic}

## Conversation 对话原文

{safe_conversation}

## Takeaway 收获

{safe_takeaway}
"""
    atomic_write(session_path, session_body)

    rel_link = (Path("..") / "sessions" / session_path.name).as_posix()
    summary_line = (
        f"- {now.date().isoformat()}: [Session {session_index}]({rel_link}) — {takeaway}"
    )
    body = append_to_section(body, DISCUSSION_HEADING, summary_line)

    set_meta(lines, "discussion_count", str(new_count))
    set_meta(lines, "updated_at", timestamp)
    # discuss is an active engagement with the record — stamp it so
    # scan --mode least-reviewed will not keep re-surfacing it.
    _bump_review(lines, meta, now)

    save_record(path, lines, body)
    return session_path


def _scan_sort(candidates, mode):
    if mode == "random":
        random.shuffle(candidates)
        return candidates
    if mode == "oldest":
        return sorted(
            candidates,
            key=lambda c: parse_dt(c[1].get("updated_at")) or datetime.min.replace(tzinfo=local_now().tzinfo),
        )
    if mode == "least-reviewed":
        return sorted(candidates, key=lambda c: int_meta(c[1], "review_count"))
    return candidates


def scan(args):
    root = default_dao_dir()
    ensure_dir(root)

    candidates = []
    for path in iter_record_paths(root):
        text = path.read_text(encoding="utf-8")
        fm_lines, body = split_frontmatter(text)
        if not fm_lines:
            continue
        meta = parse_frontmatter_lines(fm_lines)
        if not schema_version_compatible(meta, path=path):
            continue
        tags = parse_tags_field(meta.get("tags", ""))
        category = meta.get("primary_category", "")
        if args.tag and args.tag not in tags:
            continue
        if args.category and args.category != category:
            continue
        candidates.append((path, meta, body))

    if not candidates:
        return

    selected = _scan_sort(candidates, args.mode)[: args.limit]
    now = local_now()
    timestamp = now.isoformat(timespec="seconds")

    # P1#16: scan defaults to read-only. Scheduler (cron) opts into the
    # review_count bump explicitly with --mark-reviewed, so an
    # interactive `scan` from the terminal doesn't masquerade as a real
    # re-engagement.
    should_mark = args.mark_reviewed and not args.peek
    for path, meta, body in selected:
        title = title_from_body(body)
        if not should_mark:
            review_count = int_meta(meta, "review_count")
        else:
            with locked_record(path):
                fm_lines, fresh_body = split_frontmatter(path.read_text(encoding="utf-8"))
                review_count = int_meta(parse_frontmatter_lines(fm_lines), "review_count") + 1
                set_meta(fm_lines, "review_count", str(review_count))
                set_meta(fm_lines, "last_reviewed_at", timestamp)
                save_record(path, fm_lines, fresh_body)
        print(
            f"{review_count}\t{meta.get('updated_at', '')}\t{meta.get('id', '')}\t{path}\t{title}"
        )


def update(args):
    path = Path(args.file).expanduser().resolve()
    assert_record_path(path, "dao", subdir="dao-md")
    with locked_record(path):
        _do_update(path, args)
    print(path)


def _do_update(path, args):
    lines, meta, body = load_record(path)
    now = local_now()

    if args.category is not None:
        set_meta(lines, "primary_category", args.category)
    if args.tags is not None:
        set_meta(lines, "tags", format_tags(args.tags))
    if args.priority:
        set_meta(lines, "priority", args.priority)
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    if args.note:
        body = append_to_section(body, NOTES_HEADING, f"- {now.date().isoformat()}: {args.note}")
        # Engagement: appending a note counts as review touch.
        # Field-only edits (category / tags / priority) do not.
        _bump_review(lines, meta, now)

    save_record(path, lines, body)


def _bump_review(lines, meta, now):
    """Stamp `last_reviewed_at` to now and increment `review_count` by one.

    Called from refine / discuss / update --note: each is an active
    engagement with the record, and dao/SKILL.md:146 promises these
    move the record out of `scan --mode least-reviewed`'s line. Without
    this stamp, the same recently-engaged record keeps getting surfaced
    on the next cron run.
    """
    new_count = int_meta(meta, "review_count") + 1
    set_meta(lines, "review_count", str(new_count))
    set_meta(lines, "last_reviewed_at", now.isoformat(timespec="seconds"))


def main():
    parser = argparse.ArgumentParser(
        description=f"Capture, refine, discuss and review Markdown dao records in {DAO_DIR_DISPLAY}."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_capture = sub.add_parser("capture", help="Create a Markdown dao record.")
    add_text_input_args(p_capture, "text", required=True, help_text="Exact raw insight text.")
    p_capture.add_argument("--title", help="Optional Markdown title.")
    p_capture.add_argument("--source", default="manual")
    p_capture.add_argument("--priority", choices=["low", "medium", "high"], default="medium")
    p_capture.add_argument("--category", help="Primary category.")
    p_capture.add_argument("--tags", help="Comma-separated tags.")
    p_capture.set_defaults(func=capture)

    p_refine = sub.add_parser(
        "refine",
        help="Replace ## Refined; archive old version into ## Refinement Log.",
    )
    p_refine.add_argument("file", help="Markdown dao file to refine.")
    add_text_input_args(p_refine, "text", required=True, help_text="New refined text.")
    p_refine.set_defaults(func=refine)

    p_discuss = sub.add_parser(
        "discuss",
        help="Create a session file and append takeaway to main dao file.",
    )
    p_discuss.add_argument("file", help="Markdown dao file.")
    add_text_input_args(p_discuss, "topic", required=True, help_text="Discussion topic / prompt.")
    add_text_input_args(p_discuss, "conversation", required=True, help_text="Full conversation text.")
    add_text_input_args(p_discuss, "takeaway", required=True, help_text="1-3 sentence takeaway written back to main file.")
    p_discuss.set_defaults(func=discuss)

    p_scan = sub.add_parser(
        "scan", help="Surface old dao records for review; updates review_count."
    )
    p_scan.add_argument("--mode", choices=list(SCAN_MODES), default="random")
    p_scan.add_argument("--tag", help="Filter by tag.")
    p_scan.add_argument("--category", help="Filter by primary_category.")
    p_scan.add_argument("--limit", type=int, default=3)
    p_scan.add_argument(
        "--mark-reviewed",
        action="store_true",
        help="Bump review_count and stamp last_reviewed_at on each surfaced "
             "record. Default OFF — scheduler / cron must opt in so an "
             "interactive `scan` doesn't masquerade as a real re-engagement.",
    )
    p_scan.add_argument(
        "--peek",
        action="store_true",
        help="(Deprecated; scan is read-only by default. Kept as a no-op "
             "override that forces read-only even if --mark-reviewed is set.)",
    )
    p_scan.set_defaults(func=scan)

    p_update = sub.add_parser("update", help="Update dao frontmatter and append notes.")
    p_update.add_argument("file", help="Markdown dao file to update.")
    p_update.add_argument("--category")
    p_update.add_argument("--tags", help="Comma-separated tags.")
    p_update.add_argument("--priority", choices=["low", "medium", "high"])
    p_update.add_argument("--note", help="Append an entry to ## Notes.")
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
