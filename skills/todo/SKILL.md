---
name: todo
description: Track a concrete to-do item along with its log of progress notes and a post-hoc reflection. Triggers on Chinese 待办/任务/todo/记一下日志/check-in/复盘 and English todo / task / log this / check in / retro this. Use when the user wants something they will later finish or drop, distinct from open-ended ideas (idea), insights (dao), or shortcuts (tip).
version: 0.1.0
---

# todo

`todo` couples capture with rhythm. It holds: `raw` (what to do), `due` (optional date), `status` ∈ {open, done, dropped}, `log[]` (append-only progress notes), and `reflection` (post-hoc summary set when done or dropped). Status is the only enum in the system; everything else stays free-form. The agent suggests next steps and surfaces stale todos but never auto-completes, auto-extends due dates, or deletes records.

## Triggers

- 待办 / 加一个 todo / task / 记一下今天搞了什么 / 复盘一下
- todo / task / log this / check in / retro this
- Slash: /todo

## Storage

Records live at `$HOME/aha/todo.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/todo/scripts/todo.py <verb> ...`.

- `add <raw> [--due YYYY-MM-DD] [--tag T...]` — capture a todo; status starts `open`.
- `list [--status S] [--tag T...] [--since DATE] [--until DATE] [--due-before DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, status, due, tags, created_at`.
- `log <id> <note>` — append a progress note (timestamped, append-only).
- `done <id> [--reflection R]` — mark `done`; sets `done_at`; optional reflection.
- `drop <id> [--reflection R]` — mark `dropped`; optional reflection.
- `set-due <id> <YYYY-MM-DD>` — update due date.

## Constraints

- `raw` is immutable.
- `status` is the only enum: `open | done | dropped`. Do not invent intermediate states like `paused` or `blocked` — capture nuance in a `log` note instead.
- `log` is append-only. Never rewrite or remove entries.
- Past-due todos do not auto-extend. The agent may suggest a new due date; only the user accepts.
- Cross-skill links via tags only.

## Examples

```bash
python skills/todo/scripts/todo.py add "写 aha-skills 验收 doc" --due 2026-05-30 --tag aha-skills
python skills/todo/scripts/todo.py log 2026-05-19-2b8e "今天走查了 store.py"
python skills/todo/scripts/todo.py list --status open --due-before 2026-06-01 --tsv
python skills/todo/scripts/todo.py done 2026-05-19-2b8e --reflection "切片切对了,锁工作"
```
