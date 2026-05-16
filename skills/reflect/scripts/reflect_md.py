#!/usr/bin/env python3
"""reflect — cross-skill weekly pattern miner.

Walks the three sibling skills' workspaces (idea / dao / daily) and emits
deterministic data slices that the agent can synthesize into reflections.

Subcommands:
  aggregate    list records in a period across all (or one) sources
  tags         tag frequencies + co-occurrence pairs across sources
  difficulties extract daily.task ## Difficulty Log lines whose date is in range
  save         pre-fill a Markdown reflection skeleton with the snapshot above
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from aha_md import (  # noqa: E402
    UNTRUSTED_CONTENT_BANNER,
    WORKSPACE_DIR_NAME,
    atomic_write,
    check_manifest_consistency,
    doctor_workspace,
    ensure_dir,
    ensure_workspace_manifest,
    extract_difficulty_entries,
    iter_record_paths,
    local_now,
    parse_dt,
    parse_frontmatter_lines,
    parse_tags_field,
    period_id,
    period_range,
    read_section,
    read_text_or_warn,
    render_frontmatter,
    render_untrusted_inline,
    schema_version_compatible,
    split_frontmatter,
    task_in_period,
    title_from_body,
    unique_path,
    workspace_dir,
)


REFLECT_DIR_DISPLAY = f"./{WORKSPACE_DIR_NAME}/reflect/reflections"

PERIODS = ("day", "week", "month")
SOURCES = ("idea", "dao", "daily", "all")



def _idea_dir():
    return workspace_dir("idea", "idea-md")


def _dao_dir():
    return workspace_dir("dao", "dao-md")


def _daily_tasks_dir():
    return workspace_dir("daily", "tasks")


def _daily_logs_dir():
    return workspace_dir("daily", "logs")


def _reflect_dir():
    return workspace_dir("reflect", "reflections")


def _parse_frontmatter_with_body(path):
    """Return (meta_dict, body) or (None, None) when path is not parseable
    or has a schema_version we cannot interpret with current semantics.

    Read errors (OSError) and decode errors (UnicodeDecodeError on a non-
    UTF-8 file) both fold into (None, None) — the caller bumps the
    parse_error counter and a stderr warning fires from read_text_or_warn.
    """
    text = read_text_or_warn(path)
    if text is None:
        return None, None
    lines, body = split_frontmatter(text)
    if not lines:
        return None, None
    meta = parse_frontmatter_lines(lines)
    if not schema_version_compatible(meta, path=path):
        return None, None
    return meta, body


def parse_date_str(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def in_range(target_date, start, end):
    return target_date is not None and start <= target_date <= end


def _record_date_for_range(meta):
    """Date used for inclusion test: prefer updated_at, fall back to created_at,
    then `date` (daily logs)."""
    for key in ("updated_at", "created_at"):
        dt = parse_dt(meta.get(key))
        if dt is not None:
            return dt.date()
    plain = parse_date_str(meta.get("date", ""))
    if plain is not None:
        return plain
    return None


def _new_health_bucket():
    return {"present": 0, "out_of_range": 0, "parse_error": 0, "missing": False}


def load_records(source, start, end):
    """Yield (source_label, sub_type, meta, body, path) for records in range.

    Returns a tuple ``(records, health)`` where ``health`` is a per-source
    dict of counters used by ``## Source Health`` rendering and the
    ``--strict`` failure mode.
    """
    out = []
    health = {
        "idea": _new_health_bucket(),
        "dao": _new_health_bucket(),
        "daily.task": _new_health_bucket(),
        "daily.log": _new_health_bucket(),
    }

    def scan_source(label, root, *, type_filter=None, date_extractor=None):
        if not root.is_dir():
            health[label]["missing"] = True
            return
        for path in iter_record_paths(root):
            meta, body = _parse_frontmatter_with_body(path)
            if meta is None:
                health[label]["parse_error"] += 1
                continue
            if type_filter and meta.get("type") and meta.get("type") != type_filter:
                continue
            if date_extractor is not None:
                if not date_extractor(meta):
                    health[label]["out_of_range"] += 1
                    continue
            health[label]["present"] += 1
            out.append((label, type_filter or label, meta, body, path))

    if source in ("idea", "all"):
        scan_source(
            "idea", _idea_dir(),
            date_extractor=lambda m: in_range(_record_date_for_range(m), start, end),
        )
    if source in ("dao", "all"):
        scan_source(
            "dao", _dao_dir(),
            date_extractor=lambda m: in_range(_record_date_for_range(m), start, end),
        )
    if source in ("daily", "all"):
        scan_source(
            "daily.task", _daily_tasks_dir(),
            type_filter="task",
            date_extractor=lambda m: task_in_period(m, start, end),
        )
        scan_source(
            "daily.log", _daily_logs_dir(),
            type_filter="log",
            date_extractor=lambda m: in_range(parse_date_str(m.get("date", "")), start, end),
        )
    return out, health


def _render_source_health(health):
    """Render a Source Health markdown block for save() snapshots.

    Lists each source's present/out_of_range/parse_error counts plus a
    missing flag. The block surfaces silent skip conditions a future
    operator would otherwise have no way to diagnose.
    """
    rows = ["| source | present | out-of-range | parse-error | root missing |",
            "|---|---|---|---|---|"]
    for source in ("idea", "dao", "daily.task", "daily.log"):
        h = health.get(source, _new_health_bucket())
        rows.append(
            f"| {source} | {h['present']} | {h['out_of_range']} | "
            f"{h['parse_error']} | {'yes' if h['missing'] else 'no'} |"
        )
    rows.append("")
    from datetime import datetime as _datetime
    tz_str = _datetime.now().astimezone().strftime("%z")
    if len(tz_str) == 5:
        tz_str = f"{tz_str[:3]}:{tz_str[3:]}"
    rows.append(f"_Host TZ: {tz_str}_")
    return "\n".join(rows)


def _health_has_issues(health):
    for h in health.values():
        if h.get("missing") or h.get("parse_error", 0) > 0:
            return True
    return False


def _resolve_period(args):
    anchor = parse_date_str(args.date) if args.date else local_now().date()
    if anchor is None:
        raise SystemExit(f"Invalid --date: {args.date}")
    start, end = period_range(args.period, anchor)
    return start, end


def aggregate(args):
    start, end = _resolve_period(args)
    records, health = load_records(args.source, start, end)
    if getattr(args, "strict", False) and _health_has_issues(health):
        for source, h in health.items():
            if h["missing"] or h["parse_error"]:
                sys.stderr.write(
                    f"strict: {source} — missing={h['missing']} "
                    f"parse_error={h['parse_error']}\n"
                )
        raise SystemExit(2)
    for source, sub_type, meta, body, path in records:
        if source == "idea":
            status = meta.get("status", "")
            date_field = meta.get("updated_at", "")
        elif source == "dao":
            status = "-"
            date_field = meta.get("updated_at", "")
        elif source == "daily.task":
            status = meta.get("status", "")
            date_field = meta.get("due_at", "") or meta.get("updated_at", "")
        else:  # daily.log
            status = "-"
            date_field = meta.get("date", "")
        title = title_from_body(body)
        tags = parse_tags_field(meta.get("tags", ""))
        print("\t".join([
            source,
            sub_type,
            status or "-",
            date_field or "-",
            meta.get("id", "") or f"log-{meta.get('date', '')}",
            str(path),
            title,
            ",".join(tags),
        ]))


def _records_with_tags(records):
    out = []
    for source, _sub_type, meta, _body, path in records:
        tags = parse_tags_field(meta.get("tags", ""))
        if tags:
            record_id = meta.get("id") or meta.get("date") or Path(path).stem
            out.append((source, record_id, tags))
    return out


def tags(args):
    start, end = _resolve_period(args)
    records, health = load_records(args.source, start, end)
    if getattr(args, "strict", False) and _health_has_issues(health):
        for source, h in health.items():
            if h["missing"] or h["parse_error"]:
                sys.stderr.write(
                    f"strict: {source} — missing={h['missing']} "
                    f"parse_error={h['parse_error']}\n"
                )
        raise SystemExit(2)
    tagged = _records_with_tags(records)

    freq = {}
    sources_for_tag = {}
    for source, _rid, ts in tagged:
        for t in ts:
            freq[t] = freq.get(t, 0) + 1
            sources_for_tag.setdefault(t, set()).add(source)

    co_pairs = {}
    records_for_pair = {}
    for source, rid, ts in tagged:
        unique = sorted(set(ts))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair = (unique[i], unique[j])
                co_pairs[pair] = co_pairs.get(pair, 0) + 1
                records_for_pair.setdefault(pair, set()).add(f"{source}:{rid}")

    freq_lines = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    for tag, count in freq_lines:
        print(f"{tag}\t{count}\t{','.join(sorted(sources_for_tag[tag]))}")

    pair_rows = [
        (pair, count) for pair, count in co_pairs.items() if count >= args.min_count
    ]
    pair_rows.sort(key=lambda kv: (-kv[1], kv[0]))
    if pair_rows:
        print()
        for (a, b), count in pair_rows:
            # source_records_csv = list of <source>:<id> that carry both tags
            print(f"{a}\t{b}\t{count}\t{','.join(sorted(records_for_pair[(a, b)]))}")


def difficulties(args):
    start, end = _resolve_period(args)
    root = _daily_tasks_dir()
    if not root.is_dir():
        return
    for path in iter_record_paths(root):
        meta, body = _parse_frontmatter_with_body(path)
        if meta is None:
            continue
        if meta.get("type") and meta.get("type") != "task":
            continue
        if not body:
            continue
        title = title_from_body(body)
        for date_str, text in extract_difficulty_entries(body):
            d = parse_date_str(date_str)
            if not in_range(d, start, end):
                continue
            print("\t".join([
                d.isoformat(),
                meta.get("id", ""),
                str(path),
                title,
                text,
            ]))


def _render_snapshot(records, args, start, end):
    lines = [UNTRUSTED_CONTENT_BANNER, ""]
    by_source = {"idea": [], "dao": [], "daily.task": [], "daily.log": []}
    for rec in records:
        source = rec[0]
        if source in by_source:
            by_source[source].append(rec)

    # idea
    lines.append(f"### idea ({len(by_source['idea'])})")
    if by_source["idea"]:
        for _, _, meta, body, _ in by_source["idea"]:
            tags = parse_tags_field(meta.get("tags", ""))
            tag_str = ", ".join(render_untrusted_inline(t) for t in tags) if tags else "-"
            lines.append(
                f"- {meta.get('status', '?'):<11} | tags: [{tag_str}] | "
                f"{meta.get('id', '')} — {render_untrusted_inline(title_from_body(body))}"
            )
    else:
        lines.append("- (none in range)")
    lines.append("")

    # dao
    lines.append(f"### dao ({len(by_source['dao'])})")
    if by_source["dao"]:
        for _, _, meta, body, _ in by_source["dao"]:
            updated = meta.get("updated_at", "")[:10] or "?"
            tags = parse_tags_field(meta.get("tags", ""))
            tag_str = ", ".join(render_untrusted_inline(t) for t in tags) if tags else "-"
            lines.append(
                f"- {updated} | tags: [{tag_str}] | "
                f"{meta.get('id', '')} — {render_untrusted_inline(title_from_body(body))}"
            )
    else:
        lines.append("- (none in range)")
    lines.append("")

    # daily.tasks
    tasks_in = by_source["daily.task"]
    done_count = sum(1 for _, _, m, _, _ in tasks_in if m.get("status") == "done")
    lines.append(f"### daily.tasks ({len(tasks_in)} touched, {done_count} done)")
    if tasks_in:
        for _, _, meta, body, _ in tasks_in:
            due = meta.get("due_at", "")[:10] or "-"
            lines.append(
                f"- {meta.get('status', '?'):<11} | due {due} | "
                f"{meta.get('id', '')} — {render_untrusted_inline(title_from_body(body))}"
            )
    else:
        lines.append("- (none in range)")
    lines.append("")

    # daily.logs
    logs_in = by_source["daily.log"]
    lines.append(f"### daily.logs ({len(logs_in)})")
    if logs_in:
        for _, _, meta, _body, _ in logs_in:
            tags = parse_tags_field(meta.get("tags", ""))
            tag_str = ", ".join(render_untrusted_inline(t) for t in tags) if tags else "-"
            lines.append(
                f"- {meta.get('date', '?')} | {meta.get('entry_count', '0')} entries "
                f"| tags: [{tag_str}]"
            )
    else:
        lines.append("- (none in range)")
    lines.append("")

    # difficulties (re-walk; cheap)
    diffs = _collect_difficulties(start, end)
    lines.append(f"### daily.difficulties ({len(diffs)})")
    if diffs:
        for d, task_id, _path, _title, text in diffs:
            lines.append(
                f"- {d.isoformat()} ({task_id}): {render_untrusted_inline(text)}"
            )
    else:
        lines.append("- (none in range)")

    return "\n".join(lines), diffs


def _collect_difficulties(start, end):
    out = []
    root = _daily_tasks_dir()
    if not root.is_dir():
        return out
    for path in iter_record_paths(root):
        meta, body = _parse_frontmatter_with_body(path)
        if meta is None or not body:
            continue
        if meta.get("type") and meta.get("type") != "task":
            continue
        title = title_from_body(body)
        for date_str, text in extract_difficulty_entries(body):
            d = parse_date_str(date_str)
            if not in_range(d, start, end):
                continue
            out.append((d, meta.get("id", ""), path, title, text))
    return out


def _render_tag_summary(records):
    lines = []
    tagged = _records_with_tags(records)
    freq = {}
    sources_for_tag = {}
    for source, _rid, ts in tagged:
        for t in ts:
            freq[t] = freq.get(t, 0) + 1
            sources_for_tag.setdefault(t, set()).add(source)
    if not freq:
        return "- (no tags in range)"
    for tag, count in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])):
        sources_str = ", ".join(sorted(sources_for_tag[tag]))
        lines.append(f"- {tag}: {count} ({sources_str})")
    return "\n".join(lines)


def save(args):
    start, end = _resolve_period(args)
    pid = period_id(args.period, start, end)

    root = _reflect_dir()
    ensure_dir(root)
    ensure_workspace_manifest()
    reflect_id, path = unique_path(root, f"reflect-{pid}")

    records, health = load_records("all", start, end)
    if getattr(args, "strict", False) and _health_has_issues(health):
        for source, h in health.items():
            if h["missing"] or h["parse_error"]:
                sys.stderr.write(
                    f"strict: {source} — missing={h['missing']} "
                    f"parse_error={h['parse_error']}\n"
                )
        raise SystemExit(2)
    snapshot_md, _diffs = _render_snapshot(records, args, start, end)
    tag_summary = _render_tag_summary(records)
    source_health = _render_source_health(health)

    now = local_now()
    frontmatter = render_frontmatter([
        ("reflect_id", reflect_id),
        ("type", "reflect"),
        ("schema_version", "1"),
        ("period", args.period),
        ("range_start", start.isoformat()),
        ("range_end", end.isoformat()),
        ("created_at", now.isoformat(timespec="seconds")),
        ("sources", "[idea, dao, daily]"),
    ])
    body = f"""{frontmatter}
# Reflect: {pid}

## 范围

{start.isoformat()} → {end.isoformat()}

## Source Health

{source_health}

## Source Snapshot

{snapshot_md}

## Tags Across Sources

{tag_summary}

## 模式与启示

<待与用户讨论后填写；agent 不要单方面预填。这一段是慢思考的产物——读完上面的 Source Snapshot 之后与用户多轮交流，再把得出的 3-7 条观察写到这里。关注：跨源 tag 重叠 / 反复出现的困难主题 / 某个 idea 触到了某个 dao。>

## 下阶段意图

<待与用户讨论后填写；agent 不要单方面预填。1-3 条"意图"（不是 goals）。>
"""
    atomic_write(path, body)
    print(path)


def _add_period_args(p):
    p.add_argument("--period", choices=list(PERIODS), required=True)
    p.add_argument("--date", help="Anchor date YYYY-MM-DD (default: today, local).")


def _add_strict_arg(p):
    p.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero (code 2) if any source root is missing or any "
             "record fails to parse. Default behaviour is to warn and skip.",
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "reflect — cross-skill aggregation over aha-workspace/. "
            f"Reflections land in {REFLECT_DIR_DISPLAY}."
        )
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_agg = sub.add_parser("aggregate", help="List records in a period across sources.")
    _add_period_args(p_agg)
    _add_strict_arg(p_agg)
    p_agg.add_argument("--source", choices=list(SOURCES), default="all")
    p_agg.set_defaults(func=aggregate)

    p_tags = sub.add_parser("tags", help="Tag frequencies + co-occurrence.")
    _add_period_args(p_tags)
    _add_strict_arg(p_tags)
    p_tags.add_argument("--source", choices=list(SOURCES), default="all")
    p_tags.add_argument("--min-count", type=int, default=2,
                        help="Minimum co-occurrence count to report (default 2).")
    p_tags.set_defaults(func=tags)

    p_diff = sub.add_parser("difficulties", help="Extract daily task difficulty log lines in range.")
    _add_period_args(p_diff)
    p_diff.set_defaults(func=difficulties)

    p_save = sub.add_parser(
        "save",
        help="Write a reflection skeleton pre-filled with cross-source snapshot.",
    )
    _add_period_args(p_save)
    _add_strict_arg(p_save)
    p_save.set_defaults(func=save)

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
