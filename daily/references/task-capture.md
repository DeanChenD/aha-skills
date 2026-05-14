# Task Capture Workflow

Loaded by the `daily` skill when the user mentions a todo ("今天要做X" / "加个待办" / "明天前完成Y" / "todo: ..."). Pre-requisite: you have already read `daily/SKILL.md`.

## Procedure

1. Identify task text, optional due, optional priority, optional tags.
2. If no due is mentioned, **ask once** for a target completion time. If the user says "没有 deadline / 持续做 / no deadline" — accept and capture without due.
3. Run:
   ```bash
   python3 <skill-dir>/scripts/daily_md.py task \
     --text "<verbatim>" \
     --due "<iso or date, omit if none>" \
     --priority <inferred low|medium|high> \
     --tags "..."
   ```
4. Tell the user: file path, "captured as `pending` due `<due>`", and offer one specific next step (start now / defer to a specific time).

## Don't

- Don't paraphrase the task text. `--text` is recorded verbatim into `## Description`.
- Don't guess `due` if the user didn't give one. Ask, or omit it.
- Don't pre-set status to `in_progress` on capture — that's a separate decision.
