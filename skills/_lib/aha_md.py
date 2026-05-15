"""aha-skills shared primitives.

Imported by all four skill CLIs (idea / dao / daily / reflect) via sys.path
injection — each script bootstraps with:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
    from aha_md import ...

Owning conventions (kept here so a fix lands once across all skills):

- Frontmatter: --- fenced block at the top of the file, "key: value" lines only.
  Multi-line values not supported by design — values are sanitized on write.
- Section finder: matches "## <heading>" lines only — see append_to_section etc.
- One Markdown record per file; raw user text written verbatim into a section.

This module has no I/O side effects on import.
"""

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path


WORKSPACE_DIR_NAME = "aha-workspace"


def local_now():
    return datetime.now().astimezone()


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def slugify(text, fallback="item"):
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    if not words:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return "-".join(words[:8])[:64].strip("-") or fallback


def title_from(text, fallback="Untitled"):
    first = " ".join(text.strip().split())
    if not first:
        return fallback
    return first[:80]


def title_from_body(body):
    if not body:
        return ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


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


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return [], text
    end = text.find("\n---\n", 4)
    if end == -1:
        return [], text
    return text[4:end].splitlines(), text[end + len("\n---\n"):]


def parse_frontmatter_lines(lines):
    data = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_frontmatter(path):
    lines, _ = split_frontmatter(Path(path).read_text(encoding="utf-8"))
    return parse_frontmatter_lines(lines)


_NEWLINE_MARKER = " ↵ "


def sanitize_single_line(value):
    """Collapse any embedded newlines to a visible ↵ marker.

    Used for both frontmatter values (where a literal \\n would inject a new
    key:value row, e.g. forging `status: dropped`) and section log lines
    (where `\\n## ` would split the section or inject a fake heading that
    later append/replace operations would mistake for a real section).
    """
    if value is None:
        return value
    s = str(value)
    if "\n" in s or "\r" in s:
        s = s.replace("\r\n", _NEWLINE_MARKER).replace("\n", _NEWLINE_MARKER).replace("\r", _NEWLINE_MARKER)
    return s


def set_meta(lines, key, value):
    rendered = f"{key}: {sanitize_single_line(value)}"
    prefix = f"{key}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = rendered
            return
    lines.append(rendered)


def append_to_section(body, heading, line):
    line = sanitize_single_line(line)
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


def int_meta(meta, key):
    try:
        return int(meta.get(key) or "0")
    except ValueError:
        return 0


def unique_path(root, base_id):
    candidate_id = base_id
    candidate_path = Path(root) / f"{candidate_id}.md"
    counter = 2
    while candidate_path.exists():
        candidate_id = f"{base_id}-{counter}"
        candidate_path = Path(root) / f"{candidate_id}.md"
        counter += 1
    return candidate_id, candidate_path


def load_record(path):
    text = Path(path).read_text(encoding="utf-8")
    lines, body = split_frontmatter(text)
    if not lines:
        raise SystemExit(f"Missing frontmatter: {path}")
    meta = parse_frontmatter_lines(lines)
    return lines, meta, body


def save_record(path, lines, body):
    Path(path).write_text(
        "---\n" + "\n".join(lines) + "\n---\n" + body, encoding="utf-8"
    )


def period_range(period, anchor):
    """Return inclusive (start_date, end_date) for day/week/month."""
    if period == "day":
        return anchor, anchor
    if period == "week":
        weekday = anchor.isoweekday()
        monday = anchor - timedelta(days=weekday - 1)
        sunday = monday + timedelta(days=6)
        return monday, sunday
    if period == "month":
        first = anchor.replace(day=1)
        if first.month == 12:
            next_first = first.replace(year=first.year + 1, month=1)
        else:
            next_first = first.replace(month=first.month + 1)
        last = next_first - timedelta(days=1)
        return first, last
    raise SystemExit(f"Unknown period: {period}")
