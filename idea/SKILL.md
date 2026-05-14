---
name: idea
description: Use when the user invokes /idea, records a sudden idea, asks to maintain an idea inbox, turn an idea into a research task, create follow-up questions, review stale ideas, remind the user to continue, or decide whether an idea should become a plan / be paused / be killed.
---

# Idea

Use this skill to turn fleeting ideas into durable Markdown idea records and push them through a lightweight incubation loop: capture, classify, research, plan, decide.

## Storage

Always store idea Markdown records in `./aha-workspace/idea/idea-md`, resolved relative to the current working directory. Create the directory automatically before capture or scan if it does not exist.

`aha-workspace/` is the shared workspace root for all skills in this family; the `idea` skill owns `aha-workspace/idea/`. Set the host's workdir (Hermes `workdir`, your shell, etc.) to a stable parent directory so the same `aha-workspace/` is reused across runs. Do not pass any other idea path.

Keep one Markdown file per idea. Preserve the raw idea text exactly as given and never overwrite it. Update analysis, plan, status, and decision history in the same file.

> **Why**: `## Raw Idea` 是用户思维的考古层。改它就丢失了想法演化的证据；后续的 `## Summary` / `## Plan` / `## Decision Log` 才是版本管理。

Use `scripts/idea_md.py` for deterministic file creation and stale-idea scans (run from the workspace parent so `./aha-workspace/...` resolves correctly):

```bash
python3 <skill-dir>/scripts/idea_md.py capture --text "<raw idea>" --source chat
python3 <skill-dir>/scripts/idea_md.py scan --stale-days 7 --include-paused
python3 <skill-dir>/scripts/idea_md.py update ./aha-workspace/idea/idea-md/<file>.md --status planning --decision "Ready for a concrete plan." --bump-review
```

## Capture Workflow

When the user sends an idea:

1. Capture the exact raw content and current timestamp in a Markdown file.
2. Classify the idea with 1-5 tags and one primary category.
3. Create a research task that states what must become true for the idea to be actionable.
4. Write a short plan with concrete next actions.
5. Ask at most 3 high-leverage follow-up questions, preferably as choices.
6. Set status to `researching` unless the user clearly says only to store it.

Use this status model:

- `inbox`: captured but not processed
- `researching`: needs exploration, assumptions, examples, market/technical checks, or user clarification
- `planning`: enough is known to form an executable plan
- `paused`: intentionally deferred
- `completed`: converted into a sufficient plan or artifact
- `killed`: intentionally abandoned with a recorded reason

## Markdown Shape

Each idea file should keep this structure:

```markdown
---
id: idea-YYYYMMDD-HHMMSS-slug
status: researching
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
next_review_at: YYYY-MM-DDTHH:MM:SS+08:00
last_prompted_at:
review_count: 0
priority: medium
source: chat
primary_category: product
tags: [agent, workflow, research]
---

# <concise idea title>

## Raw Idea

<exact user text>

## Summary

<1-3 sentence summary>

## Classification

- Primary category:
- Tags:
- Confidence:

## Research Task

<what needs to be researched or clarified before this is executable>

## Plan

- [ ] Clarify:
- [ ] Research:
- [ ] Validate:
- [ ] Draft:
- [ ] Decide:

## Questions For User

1.
2.
3.

## Decision Log

- YYYY-MM-DD: Captured.

## Notes
```

## Incubation Workflow

When asked to continue, review, remind, or scan ideas:

1. Run `scan` to list active ideas whose `updated_at` is older than the chosen threshold or whose `next_review_at` is due.
2. Pick the highest-leverage next step for each stale idea.
3. Do not ask broad questions like "what do you want to do?" Give specific choices:
   - continue research
   - answer a missing question
   - create a prototype/MVP task
   - pause until a date
   - kill with a reason
4. Update the Markdown file after every decision or meaningful interaction.

If an idea has not moved after repeated reminders, explicitly suggest `paused` or `killed`. Preserve the reason in `Decision Log`.

## Scheduled Review

For a scheduled agent run, use the skill as a triage loop:

1. Scan due ideas.
2. Read at most 3 idea files per run unless the user asks for a full sweep.
3. For each idea, either advance the plan, ask one concrete question, set a `next_review_at`, or recommend `paused`/`killed`.
4. Write every meaningful decision back to the Markdown file with `update`.
5. If nothing needs user attention, return `[SILENT]` when the host scheduler supports silent runs.

Example prompt for a scheduler:

```text
Use the idea skill. Scan ./aha-workspace/idea/idea-md for stale or due ideas. For each due idea, choose the next smallest useful action. Update the Markdown file with status, next_review_at, notes, and decision log. Only message me when you need an answer or there is a concrete plan/kill recommendation.
```

When running in Hermes, install the skill under `~/.hermes/skills/idea` or configure `skills.external_dirs` to include the directory that contains this skill. Then create a cron job with the `idea` skill attached and `workdir` set to a stable parent directory; the Markdown records live in `<workdir>/aha-workspace/idea/idea-md/`.

## Red Flags — STOP and re-read

| 看到自己想 | 实际是 |
|---|---|
| "用户提了个 idea，我直接帮他改成更精炼的版本吧" | 不要改 `## Raw Idea`。在 `## Summary` 写精炼版。 |
| "他没回答，那就当 paused 吧" | 不要替用户做 `paused` / `killed` 决定。明确提议、等回答。 |
| "我问个开放问题让他想想" | 不问"你想做什么？"。给具体选项（continue / answer / pause / kill）。 |
| "stale 5 天了我顺手 kill 了吧" | 不要 auto-kill。提议 + 等用户确认。 |
| "用 Edit 直接改 idea 的 .md 比走 CLI 快" | 不要绕过 `idea_md.py`。直接 Edit 会丢失 `Decision Log` / `next_review_at` 的自动维护。 |

## Output Style

After capturing or updating an idea, tell the user:

- the file path
- the current status
- the next action or the specific question you need answered

Keep the interaction short. The Markdown file is the source of truth.
