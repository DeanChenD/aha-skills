---
name: reflect
description: Cross-skill pattern surfacing across idea/dao/tip/task within a time window. Triggers on Chinese 复盘/回顾/最近一段/这段时间/抽个空看看/总结 and English reflect / retro / what happened / weekly review / surface patterns. Use when the user wants the agent to read across all four record-producing skills (idea, dao, tip, task) and synthesize themes — not to add anything new.
version: 0.1.0
---

# reflect

`reflect` is the only read-only skill. It has no Python script. The agent itself is the reflection engine: it reads the four `.jsonl` files via the existing `list` verbs, groups by tag/time/status, and proposes themes back to the user as suggestions. Suggestions never become actions without the user's go-ahead.

## Triggers

- 复盘最近 / 这周回顾 / 这段时间我都干了啥 / 帮我看看模式
- reflect / retro / what have I been doing / weekly review / surface patterns
- Slash: /reflect

## Approach

When invoked:

1. Pick the time window. Default: last 14 days. Honor an explicit user-given window.
2. Pull data in parallel:
   ```
   python skills/idea/scripts/idea.py list --since YYYY-MM-DD
   python skills/dao/scripts/dao.py  list --since YYYY-MM-DD
   python skills/tip/scripts/tip.py  list --since YYYY-MM-DD
   python skills/task/scripts/task.py list --since YYYY-MM-DD
   ```
3. Aggregate in context:
   - tag frequency per skill and across skills
   - cross-source tag co-occurrences
   - task status distribution (open/done/dropped/overdue)
   - notable refinements (idea/dao records with non-empty `refinement_log`)
4. Surface 3-5 themes. Each theme cites at least one source `id` from the underlying records.
5. Offer suggestions ("would you like to ..."): triage suggestions for stale tasks, generalization candidates from repeated tips, candidate links between idea/dao that share tags. **Do not execute** the suggestions.

## Constraints

- **Read-only**: never call `add`, `refine`, `set-status`, `log`, `done`, `drop`, or `set-due`.
- **No fabrication**: every theme must trace to ≥1 record id present in the data pulled.
- **No auto-linking**: do not invent shared tags, parent fields, or bidirectional relationships in the data — surfacing is in the conversation, not in the JSONL.
- **Suggestions only**: questions remain open until the user replies; then route the response to the appropriate skill.

## Why no script

The actual work — reading, aggregating, synthesizing — is what the agent already does well. A script would freeze a particular synthesis shape into code; reflection's value is precisely that each pass can pick a different lens. Keep it as a prompt, not a pipeline.

## Examples

User: "帮我复盘最近两周的 aha-skills 工作"
Agent: pulls `--since 2026-05-05` from all four skills, finds tag `aha-skills` co-occurring across 1 idea, 3 dao, 5 task entries, surfaces themes (e.g. "两次 dao 都在讨论 schema 简化"), suggests "要不要把这两个 dao refine 成一条原则?" — and waits for confirmation before invoking `dao refine`.
