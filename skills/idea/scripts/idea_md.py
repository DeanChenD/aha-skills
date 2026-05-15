#!/usr/bin/env python3
import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from aha_md import (  # noqa: E402
    WORKSPACE_DIR_NAME,
    append_to_section,
    assert_workspace_path,
    ensure_dir,
    format_tags,
    int_meta,
    local_now,
    parse_dt,
    parse_frontmatter,
    set_meta,
    slugify,
    split_frontmatter,
    unique_path,
)


ACTIVE_STATUSES = {"inbox", "researching", "planning"}
PAUSED_STATUS = "paused"
STATUSES = {"inbox", "researching", "planning", "paused", "completed", "killed"}
IDEA_DIR_RELATIVE = Path(WORKSPACE_DIR_NAME) / "idea" / "idea-md"
IDEA_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/idea/idea-md"


def default_idea_dir():
    return (Path.cwd() / IDEA_DIR_RELATIVE).resolve()


def normalize_datetime(value):
    if not value:
        return ""
    parsed = parse_dt(value)
    if parsed is None:
        raise SystemExit(f"Invalid datetime: {value}")
    return parsed.isoformat(timespec="seconds")


def title_from_text(text):
    first = " ".join(text.strip().split())
    if not first:
        return "Untitled Idea"
    return first[:80]


def capture(args):
    root = default_idea_dir()
    ensure_dir(root)
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.text, fallback="idea")
    idea_id, path = unique_path(root, f"idea-{stamp}-{slug}")
    title = args.title or title_from_text(args.text)
    timestamp = now.isoformat(timespec="seconds")
    next_review_at = normalize_datetime(args.next_review_at)
    body = f"""---
id: {idea_id}
status: {args.status}
created_at: {timestamp}
updated_at: {timestamp}
next_review_at: {next_review_at}
last_prompted_at:
review_count: 0
priority: {args.priority}
source: {args.source}
primary_category: {args.category or ""}
tags: {format_tags(args.tags)}
---

# {title}

## Raw Idea

{args.text}

## Summary

TBD

## Classification

- Primary category:
- Tags:
- Confidence:

## Research Task

TBD

## Plan

- [ ] Clarify:
- [ ] Research:
- [ ] Validate:
- [ ] Draft:
- [ ] Decide:

## Questions For User

1.
2.
3.

## Decision Log

- {now.date().isoformat()}: Captured.

## Notes
"""
    path.write_text(body, encoding="utf-8")
    print(path)


def update(args):
    path = Path(args.file).expanduser().resolve()
    assert_workspace_path(path, "idea")
    text = path.read_text(encoding="utf-8")
    lines, body = split_frontmatter(text)
    if not lines:
        raise SystemExit(f"Missing frontmatter: {path}")
    meta = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()

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

    if args.decision:
        body = append_to_section(body, "Decision Log", f"- {now.date().isoformat()}: {args.decision}")
    if args.note:
        body = append_to_section(body, "Notes", f"- {now.date().isoformat()}: {args.note}")

    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body, encoding="utf-8")
    print(path)


def scan(args):
    root = default_idea_dir()
    ensure_dir(root)
    now = local_now()
    cutoff = now - timedelta(days=args.stale_days)
    rows = []
    for path in sorted(root.rglob("*.md")):
        meta = parse_frontmatter(path)
        status = meta.get("status", "").strip()
        if args.include_completed:
            eligible = True
        elif status == PAUSED_STATUS:
            eligible = args.include_paused
        else:
            eligible = status in ACTIVE_STATUSES
        if not eligible:
            continue
        updated_at = parse_dt(meta.get("updated_at"))
        next_review_at = parse_dt(meta.get("next_review_at"))
        due_for_review = next_review_at is not None and next_review_at <= now
        stale = updated_at is None or updated_at <= cutoff
        if due_for_review or (stale and next_review_at is None):
            rows.append((status or "unknown", meta.get("updated_at", ""), meta.get("next_review_at", ""), str(path)))
    for status, updated, next_review, path in rows:
        print(f"{status}\t{updated}\t{next_review}\t{path}")


def main():
    parser = argparse.ArgumentParser(
        description=f"Capture and scan Markdown idea records in {IDEA_DIR_DISPLAY}."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_capture = sub.add_parser("capture", help="Create a Markdown idea record.")
    p_capture.add_argument("--text", required=True, help="Exact raw idea text.")
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
    p_scan.set_defaults(func=scan)

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
    p_update.add_argument("--decision", help="Append an entry to Decision Log.")
    p_update.add_argument("--note", help="Append an entry to Notes.")
    p_update.set_defaults(func=update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
