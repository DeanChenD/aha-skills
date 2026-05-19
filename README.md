# aha-skills

Low-friction capture of fleeting cognition — so it can be retrieved, refined, reviewed, and grown.

Five skills:

- **idea** — outward sparks: capture → incubate → decide.
- **dao** — inward realizations: original phrasing preserved, distillation layered on top.
- **tip** — small tactical shortcuts.
- **todo** — to-dos with progress log and post-hoc reflection.
- **reflect** — agent-driven cross-skill pattern surfacing (read-only).

## Design tenets

1. JSONL is the only source of truth. One file per skill at `~/aha/<skill>.jsonl`, one JSON record per line.
2. The user's `raw` input is immutable. Refinement goes into `refined`; older versions are archived in `refinement_log`.
3. The agent edits JSONL **only** through Python scripts — no free-form file edits.
4. No forced workflows. The agent suggests; the user decides.

See `docs/superpowers/specs/2026-05-19-aha-skills-redesign-design.md` for full design and rationale. **AI agents working in this repo: read `AGENTS.md` first** — it codifies the conventions, schema rules, and behavioral constraints that the codebase depends on.

## Layout

```
skills/
  _lib/store.py         shared lib (paths, ids, locking, JSONL CRUD)
  idea/SKILL.md + scripts/idea.py
  dao/SKILL.md  + scripts/dao.py
  tip/SKILL.md  + scripts/tip.py
  todo/SKILL.md + scripts/todo.py
  reflect/SKILL.md      (no script — agent-driven)
scripts/run_tests.py
Makefile
```

## Quickstart

```bash
make test                                                    # run the suite
make idea ARGS="add '用 JSONL 替代 Markdown' --tag aha-skills"
make todo ARGS="add 'ship redesign' --due 2026-05-30"
make todo ARGS="list --status open --tsv"
```

Data location: `$HOME/aha/<skill>.jsonl`. Override with `AHA_HOME=/path/to/dir`.

## Requirements

- Python 3.11+
- macOS or Linux (uses `fcntl.flock`)
- pytest (dev only)

## Conventions

- `id`: `YYYY-MM-DD-xxxx` (4 hex chars)
- `created_at`/`updated_at`: ISO 8601 with local UTC offset
- Cross-skill linkage: tags only, shared namespace
- Errors: exit 0 success, exit 1 user error, exit 2 data/system error
