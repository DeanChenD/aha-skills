#!/usr/bin/env python3
"""idea CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store  # noqa: E402

SKILL = "idea"


def main() -> None:
    p = store.AhaArgParser(prog="idea")
    sub = p.add_subparsers(dest="cmd", required=True)
    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr)
        sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
