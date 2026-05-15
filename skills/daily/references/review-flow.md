# Review Workflow

Loaded by the `daily` skill when the user asks for a review ("看看这周", "周回顾", "月回顾", "复盘", "weekly review", "monthly review"). Pre-requisite: you have already read `daily/SKILL.md`.

## Procedure

1. Determine period: `day` / `week` / `month`, anchor date (default today, local).
2. **Optional discovery pass** — pull the raw data into chat first if the user wants to see what's in scope:
   ```bash
   python3 <skill-dir>/scripts/daily_md.py scan \
     --mode period \
     --period <day|week|month> \
     --date <anchor> \
     --type all
   ```
   Returns both tasks (touched in range) and log entries (date in range), prefixed `task\t` / `log\t`. Synthesize a summary in chat: completed tasks, active tasks, dropped tasks, key log themes, surfaced difficulties.
3. Ask the user: "要把这次回顾存档吗？" / "Want to save this as a review file?"
4. If yes, run the deterministic CLI — **do not use `Write` to compose the review file**:
   ```bash
   python3 <skill-dir>/scripts/daily_md.py review \
     --period <day|week|month> \
     [--date <anchor>]
   ```
   This writes `aha-workspace/daily/reviews/review-<period-id>.md` with frontmatter, range, and a `## Source Snapshot` (Tasks touched / Active by end of range / Logs / Difficulties) pre-filled by the CLI. The `## 模式与启示` and `## 下阶段意图` sections carry an explicit "do not pre-fill" placeholder.
5. **Write-once.** Re-running `review` for the same period does not overwrite — it creates `review-<period-id>-2.md`. If the user's view evolved, treat the older file as a snapshot of that prior view.
6. Conduct the synthesis discussion **in chat**. After agreeing on patterns and intents, edit the two trailing sections in place (the `## Source Snapshot` and frontmatter must not be hand-edited; re-run `review` for a new view).

## `<period-id>` format

- `day` → `YYYY-MM-DD`
- `week` → `YYYY-Www` (ISO week, e.g. `2026-W20`)
- `month` → `YYYY-MM`

## Note

Reviews are valuable even when not archived — many user-agent review conversations are themselves the value. Don't push to write a file unless asked or the user explicitly wants archival.

## Comparison with `reflect.save`

`daily.review` is **single-source** (just this period's daily/ tasks + logs + difficulties). `reflect.save` is the **cross-source** counterpart that adds idea/ + dao/ on top. Both write write-once snapshot files with the same `## 模式与启示` / `## 下阶段意图` discipline, so the two surfaces compose naturally — pick the one that matches what the user actually asked for.
