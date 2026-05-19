---
name: tip
description: Record a small actionable shortcut — a CLI flag, keystroke, workaround, or "did you know" trick. Triggers on Chinese 小技巧/小妙招/有个捷径/小贴士/快捷方式 and English shortcut / trick / pro tip / hack / lifehack. Use for tactical, repeatable techniques. Distinct from outward ideas (idea), inward insights (dao), and to-dos (task).
version: 0.1.0
---

# tip

`tip` is the lightweight bucket for "tiny things that save time." No status, no refinement — just record the trick with tags so future you (or `reflect`) can find it again. If a tip generalizes into a principle, write a new `dao`; the tip stays as the original observation.

## Triggers

- 教你一招 / 小妙招 / 我有个捷径 / 这个快捷方式
- pro tip / shortcut / trick / lifehack
- Slash: /tip

## Storage

Records live at `$HOME/aha/tip.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/tip/scripts/tip.py <verb> ...`.

- `add <raw> [--tag T...]` — capture a tip.
- `list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, tags, created_at`.

## Constraints

- `raw` is immutable.
- No `refined`, no `status` — keep tip lean.
- Generalization = new `dao`, not a tip rewrite.
- Cross-skill links via tags only.

## Examples

```bash
python skills/tip/scripts/tip.py add "git commit --fixup <sha> 配合 rebase --autosquash" --tag git
python skills/tip/scripts/tip.py list --tag vim --tsv
```
