---
name: dao
description: Use when the user invokes /dao, shares an inward realization or insight they want to sit with rather than act on, asks to refine an existing insight, asks to discuss one philosophically, or asks to resurface past insights. Distinguish from `idea` (outward action) and `daily` (rhythm/tasks). Recognizes Chinese realization phrases like "悟到 / 想通 / 感悟到" as well as English equivalents.
version: 0.2.0
---

# Dao

Use this skill to capture personal insights ("感悟" / 道) as Markdown, polish them into a refined sediment, optionally explore them through philosophical discussion, and periodically resurface old ones for review.

## Triggers (examples, not exhaustive)

The description above routes on intent. These are concrete phrasings users have used — keep updating as new ones surface, but do not rely on this list alone:

- 中文：「我悟到了」「想通了」「感悟到」「想明白了」「再帮我提炼一下」「重新整理一下」「展开聊聊」「和我探讨一下」「翻翻以前的感悟」「回顾一下感悟」
- English: "I just realized", "I had an insight", "I want to write this thought down", "refine this further", "let's discuss this more deeply", "look back at past insights"
- Slash: `/dao`

This skill does **not** force a status workflow. It is a set of four discrete actions on a Markdown record: `capture`, `refine`, `discuss`, `scan` (plus a generic `update`). The user decides which action to invoke; the agent never auto-promotes a record between states.

## Storage

Always store dao records under the current working directory:

- Main dao files: `./aha-workspace/dao/dao-md/<id>.md` (one file per insight; raw text never overwritten).
- Discussion session transcripts: `./aha-workspace/dao/sessions/<id>-session-NNN.md`.

`aha-workspace/` is the shared workspace root for all skills in this family; the `dao` skill owns `aha-workspace/dao/`. Set the host's workdir (Hermes `workdir`, your shell, etc.) to a stable parent directory so the same `aha-workspace/` is reused across runs. Do not pass any other dao path.

Create both directories automatically before any operation. Use `scripts/dao_md.py` for deterministic file creation, refinement, discussion logging, and review scans:

```bash
# Raw user text → stdin / file (never inline into shell quotes; user text
# may contain $(...), backticks, etc. that would execute).
printf '%s' "$RAW" | python3 <skill-dir>/scripts/dao_md.py capture --text-stdin
printf '%s' "$REFINED" | python3 <skill-dir>/scripts/dao_md.py refine ./aha-workspace/dao/dao-md/<file>.md --text-stdin
python3 <skill-dir>/scripts/dao_md.py discuss ./aha-workspace/dao/dao-md/<file>.md \
    --topic-file ./topic.txt --conversation-file ./conv.txt --takeaway-file ./takeaway.txt

python3 <skill-dir>/scripts/dao_md.py scan --mode random --limit 3
python3 <skill-dir>/scripts/dao_md.py update ./aha-workspace/dao/dao-md/<file>.md --note "<context>"
```

## Markdown Shape

```markdown
---
id: dao-YYYYMMDD-HHMMSS-slug
schema_version: 1
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
last_reviewed_at:
review_count: 0
refine_count: 0
discussion_count: 0
priority: medium
source: chat
primary_category: life
tags: [courage, work]
---

# <concise title>

## Raw 原始感悟

<exact user text — never overwrite>

## Refined 提炼沉淀

<latest distilled version; placeholder TBD until first refine>

## Context 触发情境

<optional: when / where / why this came up>

## Discussion 探讨

- YYYY-MM-DD: [Session 001](../sessions/dao-...-session-001.md) — <takeaway>

## Refinement Log

- YYYY-MM-DD (v1): <previous refined version, archived on next refine>

## Notes
```

## Capture Workflow

When the user shares an insight ("我刚刚悟到..." / "感觉..." / "想明白了..."):

1. Run `capture --text "<exact user text>"` to create the file. Preserve the user's wording verbatim in `## Raw`.
2. Unless the user explicitly says "先放着" / "暂时不用整理", immediately call `refine` once to produce the first `## Refined` version. Make it tighter and clearer than the raw text — but do not editorialize, add new claims, or moralize.
3. Optionally fill `## Context` (via `update --note` or by editing the section) if the user mentioned the trigger.
4. If the insight is clearly philosophical and the user seems open to discussion, offer one specific angle worth exploring (do not start the discussion automatically).

Tagging guidance: pick 1-3 short tags and one `primary_category` (e.g. `life`, `work`, `relationship`, `philosophy`, `craft`). Keep the vocabulary stable across captures so `scan --tag` stays useful.

## Refine Workflow

`refine` is non-destructive: it replaces the current `## Refined` block with the new text and archives the previous version into `## Refinement Log` as `- YYYY-MM-DD (vN): <old text>`. The `TBD` placeholder is **not** archived (it is not a real version).

Trigger refine when the user says:
- "再帮我提炼一下" / "重新整理一下"
- "改成更精炼的版本"
- "上次的那版不够准，换成..."

Never refine the `## Raw` section. If the user wants to correct the original wording, suggest a refine instead.

> **Why**: `## Raw 原始感悟` 是用户思维的考古层。改它就丢失了认知演化的证据；`## Refinement Log` 才是版本管理。

## Discuss Workflow

Use `discuss` when the user wants to go deeper on an existing dao — typical signals: "展开聊聊", "我想深入想想这个", "和我探讨一下", or for clearly philosophical entries you may proactively offer to discuss.

Procedure:
1. Conduct the conversation in the chat first (multi-turn, exploratory).
2. When the discussion winds down, summarize a 1-3 sentence **takeaway**.
3. Run `discuss <file> --topic ... --conversation ... --takeaway ...`.
   - `--conversation` should contain the conversation as readable text (e.g. `user: ...\nagent: ...` per turn). The full transcript lands in `aha-workspace/dao/sessions/<id>-session-NNN.md`.
   - `--takeaway` is appended to the main file's `## Discussion` section as a one-liner with a relative link to the session file.
4. If the discussion materially changed the refined sediment, also run `refine` afterwards.

Always produce a takeaway. A discussion without a takeaway is a context leak.

## Scan / Review Workflow

`scan` is for **resurfacing**, not for chasing TODOs. Default mode is `random`, default limit is 3. Each hit increments `review_count` and stamps `last_reviewed_at` — so over time `--mode least-reviewed` will pull the most-neglected entries.

Suggested triggers:
- The user says "翻翻以前的感悟" / "回顾一下" / "随便给我看几条以前的".
- A scheduled run (Hermes / cron) wants to surface 1-3 old daos.

After running scan, pick **at most one** entry to engage with: read the `## Refined` aloud (or paraphrase), then offer one of:
- "Want to refine this further given what you know now?"
- "Want to discuss this more deeply?"
- "Want to add a note about how this has aged?"
- "Or just let it sit — done."

Do not bulk-process multiple entries in one breath. Review is meant to be slow.

Filters:
- `--tag <tag>` and `--category <name>` narrow the candidate pool before sorting.
- `--mode oldest` sorts by `updated_at` ascending; `--mode least-reviewed` by `review_count` ascending.

## Scheduled Review

For a scheduled agent run, use the skill as a soft surfacing loop:

```text
Use the dao skill. Run scan --peek --mode least-reviewed --limit 1. If a record returns, read its Refined section and ask me one specific question: refine, discuss, note, or let-it-sit. If I actually engage (refine / discuss / note), the corresponding subcommand updates review_count for me. Otherwise leave review_count alone — being looked at by a scheduler is not a review. If nothing returns or nothing seems alive, return [SILENT].
```

**Install note** — `scripts/dao_md.py` imports from a sibling `_lib/aha_md.py` via `sys.path.insert(0, .../skills/_lib)`. Install the *whole* `skills/` parent directory (or symlink `_lib/` alongside `dao/`); a bare `dao/` install with no `_lib/` peer fails on first import. See [README — 安装到 host](../../README.md#安装到-host).

When running in Hermes, install the skill under `~/.hermes/skills/dao` (with `_lib/` alongside) or configure `skills.external_dirs` to include the parent that contains both `dao/` and `_lib/`. Then create a cron job with the `dao` skill attached and `workdir` set to a stable parent directory; the Markdown records live in `<workdir>/aha-workspace/dao/`.

## Red Flags — STOP and re-read

| 看到自己想 | 实际是 |
|---|---|
| "原话有错别字 / 口语，帮他改一下" | 永远不动 `## Raw 原始感悟`。要改提议 `refine`。 |
| "discuss 完直接告诉用户结论就行" | discuss 必须产出 takeaway 并 append 到 `## Discussion`。无 takeaway = context leak。 |
| "scan 出 5 条，一次性帮他过一遍" | 一次只 engage 一条。Review 是慢的。 |
| "重新 refine 一版直接覆盖旧的" | 旧版本必须存到 `## Refinement Log`（CLI 自动处理；不要绕开它直接 Edit）。 |
| "philosophical entry 我自己开个 discuss 算了" | discuss 在 chat 里多轮探讨之后再写。不要自动起话题。 |

## Output Style

After capturing, refining, discussing, or scanning:

- Tell the user the file path (or session path).
- Tell them what changed (one line).
- Offer at most one specific next step — no broad "what would you like to do?" prompts.

The Markdown file is the source of truth. The chat is the side channel.
