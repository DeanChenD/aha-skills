#!/usr/bin/env python3
import argparse
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from aha_md import (  # noqa: E402
    WORKSPACE_DIR_NAME,
    append_to_section,
    assert_workspace_path,
    atomic_write,
    check_manifest_consistency,
    ensure_dir,
    ensure_workspace_manifest,
    escape_pseudo_h2,
    format_tags,
    int_meta,
    load_record,
    local_now,
    locked_record,
    parse_dt,
    parse_frontmatter_lines,
    parse_tags_field,
    read_section,
    render_frontmatter,
    replace_section,
    sanitize_single_line,
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
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.text, fallback="dao")
    dao_id, path = unique_path(root, f"dao-{stamp}-{slug}")
    title = args.title or title_from_text(args.text)
    body = render_dao_skeleton(
        dao_id,
        title,
        escape_pseudo_h2(args.text),
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
    assert_workspace_path(path, "dao")
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

    body = replace_section(body, REFINED_HEADING, args.text.strip())

    set_meta(lines, "refine_count", str(new_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    save_record(path, lines, body)


def discuss(args):
    path = Path(args.file).expanduser().resolve()
    assert_workspace_path(path, "dao")
    with locked_record(path):
        session_path = _do_discuss(path, args)
    print(session_path)


def _do_discuss(path, args):
    lines, meta, body = load_record(path)
    now = local_now()

    parent_id = meta.get("id") or path.stem
    new_count = int_meta(meta, "discussion_count") + 1
    session_index = f"{new_count:03d}"
    session_id = f"{parent_id}-session-{session_index}"

    sessions_dir = default_sessions_dir()
    ensure_dir(sessions_dir)
    session_path = sessions_dir / f"{session_id}.md"

    timestamp = now.isoformat(timespec="seconds")
    safe_topic = escape_pseudo_h2(args.topic)
    safe_conversation = escape_pseudo_h2(args.conversation)
    safe_takeaway = escape_pseudo_h2(args.takeaway)
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
        f"- {now.date().isoformat()}: [Session {session_index}]({rel_link}) — {args.takeaway}"
    )
    body = append_to_section(body, DISCUSSION_HEADING, summary_line)

    set_meta(lines, "discussion_count", str(new_count))
    set_meta(lines, "updated_at", timestamp)

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
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm_lines, body = split_frontmatter(text)
        if not fm_lines:
            continue
        meta = parse_frontmatter_lines(fm_lines)
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

    for path, meta, body in selected:
        title = title_from_body(body)
        if args.peek:
            # Surface only — do not mutate review_count / last_reviewed_at.
            # Use this mode from a scheduler that is just looking, not
            # representing an actual user re-engagement.
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
    assert_workspace_path(path, "dao")
    with locked_record(path):
        _do_update(path, args)
    print(path)


def _do_update(path, args):
    lines, _meta, body = load_record(path)
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

    save_record(path, lines, body)


def main():
    parser = argparse.ArgumentParser(
        description=f"Capture, refine, discuss and review Markdown dao records in {DAO_DIR_DISPLAY}."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_capture = sub.add_parser("capture", help="Create a Markdown dao record.")
    p_capture.add_argument("--text", required=True, help="Exact raw insight text.")
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
    p_refine.add_argument("--text", required=True, help="New refined text.")
    p_refine.set_defaults(func=refine)

    p_discuss = sub.add_parser(
        "discuss",
        help="Create a session file and append takeaway to main dao file.",
    )
    p_discuss.add_argument("file", help="Markdown dao file.")
    p_discuss.add_argument("--topic", required=True, help="Discussion topic / prompt.")
    p_discuss.add_argument("--conversation", required=True, help="Full conversation text.")
    p_discuss.add_argument(
        "--takeaway", required=True, help="1-3 sentence takeaway written back to main file."
    )
    p_discuss.set_defaults(func=discuss)

    p_scan = sub.add_parser(
        "scan", help="Surface old dao records for review; updates review_count."
    )
    p_scan.add_argument("--mode", choices=list(SCAN_MODES), default="random")
    p_scan.add_argument("--tag", help="Filter by tag.")
    p_scan.add_argument("--category", help="Filter by primary_category.")
    p_scan.add_argument("--limit", type=int, default=3)
    p_scan.add_argument(
        "--peek",
        action="store_true",
        help="Surface candidates without bumping review_count / last_reviewed_at. "
             "Use from a scheduler so cron pings don't masquerade as user reviews "
             "(--mode least-reviewed otherwise drifts toward 'least cron-touched').",
    )
    p_scan.set_defaults(func=scan)

    p_update = sub.add_parser("update", help="Update dao frontmatter and append notes.")
    p_update.add_argument("file", help="Markdown dao file to update.")
    p_update.add_argument("--category")
    p_update.add_argument("--tags", help="Comma-separated tags.")
    p_update.add_argument("--priority", choices=["low", "medium", "high"])
    p_update.add_argument("--note", help="Append an entry to ## Notes.")
    p_update.set_defaults(func=update)

    args = parser.parse_args()
    check_manifest_consistency()
    args.func(args)


if __name__ == "__main__":
    main()
