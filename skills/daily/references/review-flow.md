# Review Workflow

Loaded by the `daily` skill when the user asks for a review ("看看这周", "周回顾", "月回顾", "复盘", "weekly review", "monthly review"). Pre-requisite: you have already read `daily/SKILL.md`.

## Procedure

1. Determine period: `day` / `week` / `month`, anchor date (default today, local).
2. Run:
   ```bash
   python3 <skill-dir>/scripts/daily_md.py scan \
     --mode period \
     --period <day|week|month> \
     --date <anchor> \
     --type all
   ```
   This returns both tasks (touched in range) and log entries (date in range), prefixed with `task\t` or `log\t`.
3. Synthesize a summary **in chat**: completed tasks, active tasks, dropped tasks, key log themes, surfaced difficulties.
4. Ask the user: "要把这次回顾存档吗？" / "Want to save this as a review file?"
5. If yes, use the `Write` tool to create `aha-workspace/daily/reviews/review-<period-id>.md` with this skeleton (filled in by you):

   ```markdown
   ---
   review_id: review-2026-W20
   period: week
   range_start: 2026-05-11
   range_end: 2026-05-17
   created_at: <now ISO>
   ---

   # Week 2026-W20 Review

   ## 范围
   2026-05-11 → 2026-05-17

   ## 任务完成
   ## 阶段进展
   ## 困难与卡点
   ## 模式与启示
   ## 下阶段意图
   ```

## `<period-id>` format

- `day` → `YYYY-MM-DD`
- `week` → `YYYY-Www` (ISO week, e.g. `2026-W20`)
- `month` → `YYYY-MM`

## Note

Reviews are valuable even when not archived — many user-agent review conversations are themselves the value. Don't push to write a file unless asked or the user explicitly wants archival.
