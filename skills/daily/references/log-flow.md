# Daily Log Workflow

Loaded by the `daily` skill when the user wants to record a moment ("记一笔", "今天...", "刚刚...", "log this", "just now ...") or shares a free-form reflection. Pre-requisite: you have already read `daily/SKILL.md`.

## Procedure

1. Decide if it's a `log` or a `task`:
   - has a target end-state + a deadline → `task`
   - otherwise → `log`

2. Run (route raw user text via stdin — `--text "..."` would expand `$(...)`/backticks in the user's content):
   ```bash
   printf '%s' "$LOG_TEXT" | python3 <skill-dir>/scripts/daily_md.py log \
     --text-stdin \
     [--time HH:MM] \
     [--title "<short>"] \
     [--tags "..."]
   # or:
   python3 <skill-dir>/scripts/daily_md.py log --text-file ./raw.txt ...
   ```

3. The CLI:
   - Creates `aha-workspace/daily/logs/log-<today>.md` if today's file doesn't exist.
   - Appends `## HH:MM — <title>` with the text.
   - Bumps `entry_count` and unions tags.

4. Confirm: "Logged in `<path>`; today now has N entries."

## Hard rule

Don't auto-rewrite or "polish" the user's words for log entries — preserve their voice. The whole point is to keep an unedited timeline.
