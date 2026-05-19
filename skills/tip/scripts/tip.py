#!/usr/bin/env python3
"""tip CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "tip"
TSV_COLS = ["id", "raw", "tags", "created_at"]


def cmd_add(args) -> None:
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": store.now_iso(),
        "updated_at": "",
    }
    rec["updated_at"] = rec["created_at"]
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))


def cmd_list(args) -> None:
    records = store.filter_records(
        store.read_all(SKILL),
        since=args.since, until=args.until,
        tags=args.tag or None, limit=args.limit,
    )
    if args.tsv:
        print("\t".join(TSV_COLS))
        for r in records:
            print(store.to_tsv_row(r, TSV_COLS))
    else:
        for r in records:
            print(store.to_jsonl_line(r))


def main() -> None:
    p = store.AhaArgParser(prog="tip")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="capture a tip")
    a.add_argument("raw")
    a.add_argument("--tag", action="append", default=[])
    a.set_defaults(fn=cmd_add)

    l = sub.add_parser("list", help="list tips")
    l.add_argument("--tag", action="append", default=[])
    l.add_argument("--since", default=None)
    l.add_argument("--until", default=None)
    l.add_argument("--limit", type=int, default=None)
    l.add_argument("--tsv", action="store_true")
    l.set_defaults(fn=cmd_list)

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
