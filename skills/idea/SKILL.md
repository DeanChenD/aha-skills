---
name: idea
description: Capture a fleeting outward-facing creative impulse — anything from a half-formed product idea to a future side project. Triggers on Chinese 想法/灵感/点子/创意/idea/我有个想法 and English I have an idea / brainstorm / what if we / project idea / explore. Use when the user wants to record something they could later act on, distinct from internal insight (dao), tactical shortcuts (tip), or to-dos (todo).
version: 0.1.0
---

# idea

`idea` captures outward-facing impulses — sparks of "we could build X" or "what if we tried Y." It is the entry point for the lifecycle: capture → refine → decide. The agent records, suggests refinements, and surfaces related ideas; it never decides for the user, never auto-promotes to todo, never overwrites raw.

## Triggers

- 我有个想法 / 想到一个点子 / 这个 idea 不错
- I have an idea / what if we / project idea / brainstorm this
- Slash: /idea

## Storage

Records live at `$HOME/aha/idea.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/idea/scripts/idea.py <verb> ...`.

- `add <raw> [--tag T...] [--status S]` — capture a new idea. Outputs the full record as one JSON line.
- `list [--tag T...] [--status S] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL (one record per line). `--tsv` prints columns `id, raw, refined, status, tags, created_at` with truncated cells.
- `refine <id> <new_refined>` — set or update the refined wording. The previous `refined`, if non-null, is archived into `refinement_log[]` with timestamp. `raw` never changes.
- `set-status <id> <status>` — free-form status string (e.g. `incubating`, `decided`, `parked`).

## Constraints

- `raw` is immutable after first write. Refinement goes in `refined`; old `refined` versions are archived in `refinement_log` automatically.
- Status is free-form and advisory. Do not invent a state machine or auto-advance status.
- Cross-skill links use tags only. Do not mint links/parent fields.
- Suggest refinements; do not silently overwrite.

## Examples

```bash
python skills/idea/scripts/idea.py add "用 JSONL 替代 markdown 做事实源" --tag aha-skills --status incubating
python skills/idea/scripts/idea.py list --tag aha-skills --tsv
python skills/idea/scripts/idea.py refine 2026-05-19-a3f7 "数据是核心,工具附着"
python skills/idea/scripts/idea.py set-status 2026-05-19-a3f7 decided
```
