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


def _section_offsets(body):
    """Return list of (line_start, line_end, heading_text) for all h2 section
    headings in body — line-based and fence-aware.

    "Heading" means a line whose stripped content is exactly "## <text>".
    Lines inside ``` ... ``` or ~~~ ... ~~~ fenced code blocks are skipped,
    so a code sample containing "## Notes" does not pose as a real section.

    This is the only place section boundaries are decided; append_to_section /
    read_section / replace_section all delegate here.
    """
    out = []
    in_fence = False
    pos = 0
    while pos <= len(body):
        line_end = body.find("\n", pos)
        if line_end == -1:
            line_end = len(body)
        line = body[pos:line_end]
        stripped_left = line.lstrip()
        if stripped_left.startswith("```") or stripped_left.startswith("~~~"):
            in_fence = not in_fence
        elif not in_fence:
            s = line.strip()
            if s.startswith("## ") and not s.startswith("### "):
                out.append((pos, line_end, s[3:].strip()))
        if line_end == len(body):
            break
        pos = line_end + 1
    return out


def _find_section(body, heading):
    """Return ((heading_line_start, heading_line_end), section_end) for the
    first h2 section whose heading text equals `heading`, or None."""
    sections = _section_offsets(body)
    for index, (line_start, line_end, h) in enumerate(sections):
        if h == heading:
            section_end = sections[index + 1][0] if index + 1 < len(sections) else len(body)
            return (line_start, line_end), section_end
    return None


def escape_pseudo_h2(text):
    """Escape line-leading '## ' (h2) markers inside multi-line user content
    so they are not mistaken for real section headings by _section_offsets.

    Markdown renders '\\## ' identically to '## ' on a non-heading line per
    CommonMark backslash escape rules, so this is visually transparent to
    readers but structurally inert to the section finder.

    Used at capture/refine time on user-controlled section bodies (e.g.
    Raw, Refined) where the user might legitimately type a `## Foo` line.
    """
    if not text:
        return text
    out = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            indent = line[: len(line) - len(stripped)]
            out.append(f"{indent}\\{stripped}")
        else:
            out.append(line)
    return "".join(out)


def append_to_section(body, heading, line):
    line = sanitize_single_line(line)
    found = _find_section(body, heading)
    if found is None:
        suffix = "" if body.endswith("\n") else "\n"
        return f"{body}{suffix}\n## {heading}\n\n{line}\n"
    (_, _), section_end = found
    before = body[:section_end].rstrip()
    after = body[section_end:]
    return f"{before}\n{line}\n{after}"


def read_section(body, heading):
    found = _find_section(body, heading)
    if found is None:
        return ""
    (_, line_end), section_end = found
    return body[line_end:section_end].strip("\n").strip()


def replace_section(body, heading, new_content):
    new_content = escape_pseudo_h2(new_content)
    found = _find_section(body, heading)
    if found is None:
        suffix = "" if body.endswith("\n") else "\n"
        return f"{body}{suffix}\n## {heading}\n\n{new_content.rstrip()}\n"
    (line_start, _), section_end = found
    head = body[:line_start] + f"## {heading}\n\n" + new_content.rstrip() + "\n"
    tail = body[section_end:]
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


def assert_workspace_path(path, skill_name):
    """Reject paths outside aha-workspace/<skill_name>/.

    Enforces the README invariant that a skill at runtime never writes
    outside its own workspace. Without this check, an agent given a malicious
    or mistaken path argument could mutate any .md file on disk via the
    update/refine/checkin/discuss commands.

    The workspace root is resolved relative to the current working directory,
    matching how default_*_dir() helpers in each skill compute their paths.
    """
    workspace_root = (Path.cwd() / WORKSPACE_DIR_NAME / skill_name).resolve()
    target = Path(path).expanduser().resolve()
    try:
        target.relative_to(workspace_root)
    except ValueError:
        raise SystemExit(
            f"Refusing to operate outside skill workspace.\n"
            f"  expected under: {workspace_root}\n"
            f"  got: {target}"
        )


CURRENT_SCHEMA_VERSION = 1


def assert_schema_version(meta, path=None, expected=CURRENT_SCHEMA_VERSION):
    """Validate frontmatter `schema_version` against expected.

    Behavior:
    - Missing schema_version: warn to stderr (treated as legacy v1, accepted).
      Avoids breaking existing user data captured before this field was written.
    - Mismatched schema_version (e.g. 2 when expected 1): SystemExit. The
      writer is from a newer/older skill version that may not have the same
      field semantics; refuse rather than silently degrade.
    """
    raw = meta.get("schema_version")
    if not raw:
        import sys as _sys
        location = f" ({path})" if path else ""
        print(
            f"warning: missing schema_version in frontmatter{location}; "
            f"treating as v{expected} (legacy file).",
            file=_sys.stderr,
        )
        return
    try:
        actual = int(raw)
    except (TypeError, ValueError):
        raise SystemExit(
            f"Unparseable schema_version: {raw!r}"
            + (f" in {path}" if path else "")
        )
    if actual != expected:
        raise SystemExit(
            f"Unsupported schema_version: got {actual}, expected {expected}"
            + (f" in {path}" if path else "")
            + "."
        )


def load_record(path, expected_schema_version=CURRENT_SCHEMA_VERSION):
    text = Path(path).read_text(encoding="utf-8")
    lines, body = split_frontmatter(text)
    if not lines:
        raise SystemExit(f"Missing frontmatter: {path}")
    meta = parse_frontmatter_lines(lines)
    assert_schema_version(meta, path=path, expected=expected_schema_version)
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
