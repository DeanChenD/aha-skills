#!/usr/bin/env python3
"""task CLI."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "task"
STATUSES = ("open", "done", "dropped")
TSV_COLS = ["id", "raw", "status", "due", "tags", "created_at"]


def _iso_date(s: str) -> str:
    date.fromisoformat(s)
    return s


def cmd_add(args) -> None:
    ts = store.now_iso()
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": ts,
        "updated_at": ts,
        "due": args.due,
        "status": "open",
        "done_at": None,
        "log": [],
        "reflection": None,
    }
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))


def cmd_log(args) -> None:
    out = store.append_log(SKILL, args.id, args.note)
    print(store.to_jsonl_line(out))


def cmd_done(args) -> None:
    out = store.mark_done(SKILL, args.id, args.reflection)
    print(store.to_jsonl_line(out))


def cmd_drop(args) -> None:
    out = store.mark_dropped(SKILL, args.id, args.reflection)
    print(store.to_jsonl_line(out))


def cmd_set_due(args) -> None:
    out = store.update_record(SKILL, args.id, lambda r: {**r, "due": args.due})
    print(store.to_jsonl_line(out))


def cmd_list(args) -> None:
    records = store.filter_records(
        store.read_all(SKILL),
        since=args.since,
        until=args.until,
        tags=args.tag or None,
        status=args.status,
        due_before=args.due_before,
        limit=args.limit,
    )
    if args.tsv:
        print("\t".join(TSV_COLS))
        for r in records:
            print(store.to_tsv_row(r, TSV_COLS))
    else:
        for r in records:
            print(store.to_jsonl_line(r))


def main() -> None:
    p = store.AhaArgParser(prog="task")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a task")
    a.add_argument("raw")
    a.add_argument("--due", type=_iso_date, default=None)
    a.add_argument("--tag", action="append", default=[])
    a.set_defaults(fn=cmd_add)

    l = sub.add_parser("list", help="list tasks")
    l.add_argument("--status", choices=STATUSES, default=None)
    l.add_argument("--tag", action="append", default=[])
    l.add_argument("--since", default=None)
    l.add_argument("--until", default=None)
    l.add_argument("--due-before", dest="due_before",
                   type=_iso_date, default=None)
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--tsv", action="store_true")
    l.set_defaults(fn=cmd_list)

    g = sub.add_parser("log", help="append a progress note")
    g.add_argument("id")
    g.add_argument("note")
    g.set_defaults(fn=cmd_log)

    d = sub.add_parser("done", help="mark task done")
    d.add_argument("id")
    d.add_argument("--reflection", default=None)
    d.set_defaults(fn=cmd_done)

    dr = sub.add_parser("drop", help="mark task dropped")
    dr.add_argument("id")
    dr.add_argument("--reflection", default=None)
    dr.set_defaults(fn=cmd_drop)

    sd = sub.add_parser("set-due", help="update due date")
    sd.add_argument("id")
    sd.add_argument("due", type=_iso_date)
    sd.set_defaults(fn=cmd_set_due)

    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr); sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    main()
