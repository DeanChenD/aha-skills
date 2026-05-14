#!/usr/bin/env python3
import argparse
import hashlib
import json
import random
import re
from datetime import datetime
from pathlib import Path


WORKSPACE_DIR_NAME = "aha-workspace"
DAO_DIR_RELATIVE = Path(WORKSPACE_DIR_NAME) / "dao" / "dao-md"
SESSIONS_DIR_RELATIVE = Path(WORKSPACE_DIR_NAME) / "dao" / "sessions"
DAO_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/dao/dao-md"

RAW_HEADING = "Raw 原始感悟"
REFINED_HEADING = "Refined 提炼沉淀"
CONTEXT_HEADING = "Context 触发情境"
DISCUSSION_HEADING = "Discussion 探讨"
REFINEMENT_LOG_HEADING = "Refinement Log"
NOTES_HEADING = "Notes"

REFINED_PLACEHOLDER = "TBD"
SCAN_MODES = ("random", "oldest", "least-reviewed")


def local_now():
    return datetime.now().astimezone()


def slugify(text):
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    if not words:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return "-".join(words[:8])[:64].strip("-") or "dao"


def title_from(text):
    first = " ".join(text.strip().split())
    if not first:
        return "Untitled Dao"
    return first[:80]


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def default_dao_dir():
    return (Path.cwd() / DAO_DIR_RELATIVE).resolve()


def default_sessions_dir():
    return (Path.cwd() / SESSIONS_DIR_RELATIVE).resolve()


def unique_dao_path(root, dao_id):
    candidate_id = dao_id
    candidate_path = root / f"{candidate_id}.md"
    counter = 2
    while candidate_path.exists():
        candidate_id = f"{dao_id}-{counter}"
        candidate_path = root / f"{candidate_id}.md"
        counter += 1
    return candidate_id, candidate_path


def format_tags(value):
    if not value:
        return "[]"
    if isinstance(value, str):
        tags = [tag.strip() for tag in value.split(",") if tag.strip()]
    else:
        tags = list(value)
    return json.dumps(tags, ensure_ascii=False)


def parse_tags_field(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (ValueError, json.JSONDecodeError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return [], text
    end = text.find("\n---\n", 4)
    if end == -1:
        return [], text
    return text[4:end].splitlines(), text[end + len("\n---\n") :]


def parse_frontmatter_lines(lines):
    data = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_frontmatter(path):
    lines, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    return parse_frontmatter_lines(lines)


def set_meta(lines, key, value):
    prefix = f"{key}:"
    rendered = f"{key}: {value}"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = rendered
            return
    lines.append(rendered)


def append_to_section(body, heading, line):
    marker = f"## {heading}"
    pos = body.find(marker)
    if pos == -1:
        suffix = "" if body.endswith("\n") else "\n"
        return f"{body}{suffix}\n{marker}\n\n{line}\n"
    next_pos = body.find("\n## ", pos + len(marker))
    insert_at = len(body) if next_pos == -1 else next_pos
    before = body[:insert_at].rstrip()
    after = body[insert_at:]
    return f"{before}\n{line}\n{after}"


def read_section(body, heading):
    marker = f"## {heading}"
    pos = body.find(marker)
    if pos == -1:
        return ""
    start = pos + len(marker)
    next_pos = body.find("\n## ", start)
    end = len(body) if next_pos == -1 else next_pos
    return body[start:end].strip("\n").strip()


def replace_section(body, heading, new_content):
    marker = f"## {heading}"
    pos = body.find(marker)
    if pos == -1:
        suffix = "" if body.endswith("\n") else "\n"
        return f"{body}{suffix}\n{marker}\n\n{new_content.rstrip()}\n"
    start = pos + len(marker)
    next_pos = body.find("\n## ", start)
    end = len(body) if next_pos == -1 else next_pos
    head = body[:pos] + marker + "\n\n" + new_content.rstrip() + "\n"
    tail = body[end:]
    if tail and not tail.startswith("\n"):
        head = head.rstrip("\n") + "\n"
    return head + tail


def title_from_body(body):
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def parse_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def render_dao_skeleton(dao_id, title, raw_text, now, source, priority, category, tags):
    timestamp = now.isoformat(timespec="seconds")
    return f"""---
id: {dao_id}
created_at: {timestamp}
updated_at: {timestamp}
last_reviewed_at:
review_count: 0
refine_count: 0
discussion_count: 0
priority: {priority}
source: {source}
primary_category: {category or ""}
tags: {format_tags(tags)}
---

# {title}

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


def _load(path):
    text = path.read_text(encoding="utf-8")
    lines, body = split_frontmatter(text)
    if not lines:
        raise SystemExit(f"Missing frontmatter: {path}")
    meta = parse_frontmatter_lines(lines)
    return lines, meta, body


def _save(path, lines, body):
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body, encoding="utf-8")


def _int_meta(meta, key):
    try:
        return int(meta.get(key) or "0")
    except ValueError:
        return 0


def capture(args):
    root = default_dao_dir()
    ensure_dir(root)
    now = local_now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.text)
    dao_id, path = unique_dao_path(root, f"dao-{stamp}-{slug}")
    title = args.title or title_from(args.text)
    body = render_dao_skeleton(
        dao_id,
        title,
        args.text,
        now,
        args.source,
        args.priority,
        args.category,
        args.tags,
    )
    path.write_text(body, encoding="utf-8")
    print(path)


def refine(args):
    path = Path(args.file).expanduser().resolve()
    lines, meta, body = _load(path)
    now = local_now()

    old_count = _int_meta(meta, "refine_count")
    new_count = old_count + 1

    current_refined = read_section(body, REFINED_HEADING)
    if current_refined and current_refined != REFINED_PLACEHOLDER:
        log_line = f"- {now.date().isoformat()} (v{old_count}): {current_refined}"
        body = append_to_section(body, REFINEMENT_LOG_HEADING, log_line)

    body = replace_section(body, REFINED_HEADING, args.text.strip())

    set_meta(lines, "refine_count", str(new_count))
    set_meta(lines, "updated_at", now.isoformat(timespec="seconds"))

    _save(path, lines, body)
    print(path)


def discuss(args):
    path = Path(args.file).expanduser().resolve()
    lines, meta, body = _load(path)
    now = local_now()

    parent_id = meta.get("id") or path.stem
    new_count = _int_meta(meta, "discussion_count") + 1
    session_index = f"{new_count:03d}"
    session_id = f"{parent_id}-session-{session_index}"

    sessions_dir = default_sessions_dir()
    ensure_dir(sessions_dir)
    session_path = sessions_dir / f"{session_id}.md"

    timestamp = now.isoformat(timespec="seconds")
    session_body = f"""---
session_id: {session_id}
parent_dao_id: {parent_id}
created_at: {timestamp}
---

# Discussion: {args.topic}

## Prompt 起点

{args.topic}

## Conversation 对话原文

{args.conversation}

## Takeaway 收获

{args.takeaway}
"""
    session_path.write_text(session_body, encoding="utf-8")

    rel_link = (Path("..") / "sessions" / session_path.name).as_posix()
    summary_line = (
        f"- {now.date().isoformat()}: [Session {session_index}]({rel_link}) — {args.takeaway}"
    )
    body = append_to_section(body, DISCUSSION_HEADING, summary_line)

    set_meta(lines, "discussion_count", str(new_count))
    set_meta(lines, "updated_at", timestamp)

    _save(path, lines, body)
    print(session_path)


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
        return sorted(candidates, key=lambda c: _int_meta(c[1], "review_count"))
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
        new_review = _int_meta(meta, "review_count") + 1
        fm_lines, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        set_meta(fm_lines, "review_count", str(new_review))
        set_meta(fm_lines, "last_reviewed_at", timestamp)
        _save(path, fm_lines, body)
        title = title_from_body(body)
        print(
            f"{new_review}\t{meta.get('updated_at', '')}\t{meta.get('id', '')}\t{path}\t{title}"
        )


def update(args):
    path = Path(args.file).expanduser().resolve()
    lines, _meta, body = _load(path)
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

    _save(path, lines, body)
    print(path)


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
    p_scan.set_defaults(func=scan)

    p_update = sub.add_parser("update", help="Update dao frontmatter and append notes.")
    p_update.add_argument("file", help="Markdown dao file to update.")
    p_update.add_argument("--category")
    p_update.add_argument("--tags", help="Comma-separated tags.")
    p_update.add_argument("--priority", choices=["low", "medium", "high"])
    p_update.add_argument("--note", help="Append an entry to ## Notes.")
    p_update.set_defaults(func=update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
