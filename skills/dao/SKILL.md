---
name: dao
description: Capture an inward-facing realization, principle, or methodology — the "道" or aha moment that names how things work. Triggers on Chinese 感悟/领悟/方法论/道/原则/aha/想明白了 and English insight / realization / principle / methodology / lesson learned. Use when the user is naming a pattern they noticed (internal), distinct from outward ideas (idea), tactical tips (tip), or work to do (todo).
version: 0.1.0
---

# dao

`dao` records the moment a pattern crystallizes. It preserves the user's exact words (`raw`), then optionally distills them (`refined`) without ever erasing the original. The agent may suggest a tighter phrasing, surface related dao through tags, or invite a deeper conversation — but the wording belongs to the user.

## Triggers

- 我突然意识到 / 这个其实就是 / 想明白了 / 这是一种 ...
- insight / realization / lesson learned / I just realized
- Slash: /dao

## Storage

Records live at `$HOME/aha/dao.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/dao/scripts/dao.py <verb> ...`.

- `add <raw> [--tag T...]` — capture a dao. Outputs the full record as one JSON line.
- `list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, refined, tags, created_at`.
- `refine <id> <new_refined>` — set or update refined wording. Previous `refined`, if any, is archived to `refinement_log[]`. `raw` never changes.

## Constraints

- `raw` is immutable. Never edit a user's exact phrasing — refine into `refined` instead.
- A "deep talk" or follow-up conversation does not need its own verb; the outcome is one more refinement.
- No status — dao does not have stages.
- Cross-skill links via tags only.

## Examples

```bash
python skills/dao/scripts/dao.py add "好脚手架是替你说不的人,不是替你说是的人"
python skills/dao/scripts/dao.py list --tag 系统设计 --tsv
python skills/dao/scripts/dao.py refine 2026-05-19-1c2f "好的脚手架替你说不"
```
