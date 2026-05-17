# aha-skills

> [简体中文](README.md) | **English**

A collection of lightweight, file-based skills for AI agents (Claude Code, Hermes). Each skill is self-contained in its own folder, exposes a `SKILL.md` describing when and how to use it, and persists state as plain Markdown so the human and the agent share the same source of truth.

All runtime data lives under a shared `aha-workspace/` directory in the host's working directory. Each skill owns a sub-folder there (e.g. `aha-workspace/idea/`).

## Design Philosophy

`aha-skills` is not a toolkit. It's four roles for keeping fleeting moments of cognition from slipping away:

- `idea` — outward action instinct: capture → incubate → decide
- `dao` — inward realization (感悟 / 道): record verbatim → distill → discuss when needed
- `daily` — keep the rhythm: tasks, logs, check-ins, reviews
- `reflect` — cross-skill pattern miner: read across the three above over a period; surface tag overlap, recurring difficulties, and themes that span sources

Four invariants that cut across all of them:

1. **Markdown is the single source of truth.** Agent and human read the same `.md` files. No private agent state.
2. **Raw text is immutable.** `## Raw` always preserves the user's original wording; refinements live in `## Refined`, with prior versions archived to `## Refinement Log`. This is an archaeological record of how the user's thinking evolved — not version noise.
3. **State mutations go through a deterministic CLI.** `*_md.py` is simultaneously the agent's write path and the testing boundary, blocking format drift from free-form LLM editing.
4. **No forced workflow.** `dao` has no status machine; `daily` does not auto-postpone overdue tasks. The agent suggests; the user decides.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │       aha-workspace/            │  ← shared runtime root
                    └─────────────────────────────────┘
                       │           │           │
        ┌──────────────┘           │           └──────────────┐
        ▼                          ▼                          ▼
  ┌──────────┐              ┌──────────┐              ┌──────────┐
  │  idea/   │              │   dao/   │              │  daily/  │
  │  action  │              │ insight  │              │  rhythm  │
  └──────────┘              └──────────┘              └──────────┘
        └─────────────────────────┬─────────────────────────┘
                                  ▼
                          ┌─────────────┐
                          │  reflect/   │   ← cross-skill pattern miner
                          │ cross-skill │      reads from the three above
                          └─────────────┘
```

Three peers that own their own write surface, plus a fourth (`reflect`) that reads across all three for cross-source pattern mining. Each skill owns a subdirectory under `aha-workspace/`; only `reflect` reads outside its own subdirectory at runtime, and only in read-only mode.

### When to use which skill

| When the user is talking about... | Use this skill |
|---|---|
| a todo with a deadline / what they did today / a weekly or monthly review / something overdue / postponing | `daily` |
| an outward direction that needs incubating, researching, deciding / "I have an idea" / their idea inbox | `idea` |
| an inward realization, a one-line aha, wanting to sit with a thought / "I just realized" / refining an old insight | `dao` |
| looking across idea + dao + daily over a window for recurring tags / themes / difficulties; explicit cross-skill reflection | `reflect` |

When intent is ambiguous, prefer asking once over guessing — these are deliberately distinct work modes, not interchangeable buckets. A *single-source* review ("look at this week's tasks") stays in that source; only use `reflect` for explicitly cross-source synthesis.

## Skills

### `idea/` — Idea Inbox & Incubator

Capture sudden ideas, timestamp them, classify them, and incubate them into Markdown research plans.

- **Trigger**: `/idea` or any request to record / review / continue / kill an idea.
- **Storage**: `./aha-workspace/idea/idea-md/<idea-id>.md` (one file per idea, raw text never overwritten).
- **Lifecycle**: `inbox → researching → planning → completed` (with `paused` / `killed` as terminal options).
- **CLI**: `skills/idea/scripts/idea_md.py` provides deterministic `capture`, `update`, `list`, and `scan` subcommands.

See [`skills/idea/SKILL.md`](skills/idea/SKILL.md) for the full workflow, Markdown shape, and scheduled-review pattern.

#### Quick start

```bash
# Capture an idea
python3 skills/idea/scripts/idea_md.py capture \
  --text "Build a tiny idea inbox" \
  --source chat \
  --status researching \
  --category product \
  --tags "idea,research"

# List all ideas (full inventory, unlike scan's due/stale filter)
python3 skills/idea/scripts/idea_md.py list --status inbox

# List stale or due-for-review ideas
python3 skills/idea/scripts/idea_md.py scan --stale-days 7 --include-paused

# Advance an idea
python3 skills/idea/scripts/idea_md.py update \
  ./aha-workspace/idea/idea-md/<file>.md \
  --status planning \
  --decision "Ready for a concrete plan." \
  --bump-review
```

### `dao/` — Insight Capture, Refinement & Review (感悟 / 道)

Capture personal insights verbatim, polish them into a refined sediment, optionally explore them through multi-turn philosophical discussion, and periodically resurface old ones for review. Counterpart to `idea`: where `idea` is for outward-facing actions, `dao` is for inner-facing realizations.

- **Trigger**: `/dao`; phrases like "I just realized", "I had an insight", "refine this further", "let's discuss this more deeply", "look back at past insights" (Chinese equivalents — "我悟到了 / 想通了", "再帮我提炼一下", "展开聊聊", "翻翻以前的感悟" — also recognized; full list in [`skills/dao/SKILL.md`](skills/dao/SKILL.md)).
- **Storage**:
  - Main records: `./aha-workspace/dao/dao-md/<dao-id>.md` (raw text never overwritten; `## Refined` rotated; `## Refinement Log` archives prior versions).
  - Discussion transcripts: `./aha-workspace/dao/sessions/<dao-id>-session-NNN.md` (linked from main file with a 1-3 sentence takeaway).
- **Actions** (no forced status workflow): `capture`, `refine`, `discuss`, `list`, `scan`, `update`.
- **CLI**: `skills/dao/scripts/dao_md.py`.

See [`skills/dao/SKILL.md`](skills/dao/SKILL.md) for triggers, Markdown shape, and the scheduled-review pattern.

#### Quick start

```bash
# Capture a raw insight
F=$(python3 skills/dao/scripts/dao_md.py capture \
  --text "Fear is a compass, not a stop sign" \
  --category life --tags "courage,fear")

# Refine it (auto-archives the previous version into ## Refinement Log)
python3 skills/dao/scripts/dao_md.py refine "$F" \
  --text "Fear marks the edge of where I should grow."

# Log a philosophical discussion
python3 skills/dao/scripts/dao_md.py discuss "$F" \
  --topic "Fear vs aversion" \
  --conversation "user: ...\nagent: ..." \
  --takeaway "Distinguish fear (points at growth) from aversion (points at self-protection)."

# List all dao records (full inventory)
python3 skills/dao/scripts/dao_md.py list --sort updated

# Preview 3 random old daos (read-only by default)
python3 skills/dao/scripts/dao_md.py scan --mode random --limit 3
# If the surfacing itself should count as a review, mark it explicitly
python3 skills/dao/scripts/dao_md.py scan --mode least-reviewed --tag courage --mark-reviewed
```

### `daily/` — Tasks, Daily Logs, Check-ins & Periodic Reviews

Manage important todos with explicit due dates and postponements, log stage-by-stage progress and surfaced difficulties, capture per-day journal entries, and produce day/week/month reviews. The rhythm-keeping counterpart to `idea` (outward action) and `dao` (inward realization).

- **Trigger**: `/daily`; phrases like "I need to do X today", "add a todo", "didn't finish today", "want to postpone to ...", "let's check in on X", "log this", "how do I feel today", "review this week" (Chinese equivalents — "今天要做...", "加个待办", "今天没做完...", "想推迟到...", "聊聊 X 的进展", "记一笔", "看看这周", "周回顾" — also recognized; full list in [`skills/daily/SKILL.md`](skills/daily/SKILL.md)).
- **Storage**:
  - Tasks: `./aha-workspace/daily/tasks/task-<id>.md` (status workflow + difficulty / postponement / check-in logs).
  - Daily logs: `./aha-workspace/daily/logs/log-YYYY-MM-DD.md` (one file per day, multiple `## HH:MM — title` entries appended within).
  - Check-in transcripts: `./aha-workspace/daily/check-ins/<task-id>-checkin-NNN.md`.
  - Reviews (written by `daily_md.py review`, write-once, mirrors `reflect.save`): `./aha-workspace/daily/reviews/review-<period-id>.md`.
- **Actions**: `task` / `update` / `checkin` / `log` / `list` / `scan` / `review` (no forced status workflow).
- **CLI**: `skills/daily/scripts/daily_md.py`.

See [`skills/daily/SKILL.md`](skills/daily/SKILL.md) for the overdue-reminder conversation flow, check-in pattern, and review skeleton.

#### Quick start

```bash
# Capture a task
T=$(python3 skills/daily/scripts/daily_md.py task \
  --text "Write the v1 spec" --due "2030-01-15T18:00" \
  --priority high --tags "work,doc")

# Postpone with an explicit reason (logged to ## Postponement Log)
python3 skills/daily/scripts/daily_md.py update "$T" \
  --due "2030-01-20T18:00" --postpone-reason "PRD review pending"

# Record a check-in
python3 skills/daily/scripts/daily_md.py checkin "$T" \
  --topic "Mid-build status" \
  --conversation "user: status?\nagent: 30% done." \
  --takeaway "Half a day to lock the data model." \
  --difficulty "data model still fuzzy" \
  --next-step "Lock model tomorrow morning"

# Append a daily log entry
python3 skills/daily/scripts/daily_md.py log \
  --text "Got distracted three times this afternoon" \
  --time "14:30" --title "Focus dip" --tags "work,mood"

# What's overdue right now?
python3 skills/daily/scripts/daily_md.py scan --mode overdue

# List the full task / log / check-in / review inventory
python3 skills/daily/scripts/daily_md.py list --type all

# Pull this week's tasks + log entries for a review
python3 skills/daily/scripts/daily_md.py scan --mode period --period week --type all
```

### `reflect/` — Cross-skill weekly pattern miner

Read across `idea` + `dao` + `daily` records over a time window and surface patterns the agent can discuss with the user — e.g. "three of this week's daos all touch on 'boundaries'", "two overdue tasks both came from 'agreeing too quickly'", "a single recurring tag spans tasks, insights, and ideas". Sits above the other three; reads only.

- **Trigger**: `/reflect`; phrases like "look across everything this month", "any common threads", "weekly cross-skill reflection" (Chinese: "跨着想想 / 跨 skill 复盘 / 这周看下整体" — full list in [`skills/reflect/SKILL.md`](skills/reflect/SKILL.md)).
- **Storage**: `./aha-workspace/reflect/reflections/reflect-<period-id>.md` (write-once snapshot; never overwrites).
- **Actions**: `aggregate` / `tags` / `difficulties` / `save` (no per-record state; reflect captures nothing of its own).
- **CLI**: `skills/reflect/scripts/reflect_md.py`.

`save` pre-fills the reflection file with a deterministic cross-source snapshot (idea / dao / daily.tasks / daily.logs / daily.difficulties + tag frequencies). The agent and user co-author the trailing `## 模式与启示` and `## 下阶段意图` sections during the conversation — those are not auto-fillable.

#### Quick start

```bash
# This week, across all three sources
python3 skills/reflect/scripts/reflect_md.py aggregate --period week
python3 skills/reflect/scripts/reflect_md.py tags --period week --min-count 2
python3 skills/reflect/scripts/reflect_md.py difficulties --period week

# Once you've discussed with the user, archive the reflection
python3 skills/reflect/scripts/reflect_md.py save --period week
# → ./aha-workspace/reflect/reflections/reflect-2026-W20.md

# Anchor to a specific date (e.g. last week)
python3 skills/reflect/scripts/reflect_md.py save --period week --date 2026-05-07
```

> **ISO week year-boundary note**: `--period week` uses ISO 8601 numbering, so 2025-12-31 belongs to `2026-W01` (the week containing 2026-01-04), and 2023-01-01 belongs to `2022-W52`. This is by spec, not a bug; archived filenames / paths use the ISO year.

## Repository layout

```
aha-skills/
├── README.md               # Chinese README (primary)
├── README.en.md            # English README (this file)
├── .gitignore
└── skills/
    ├── _lib/
    │   ├── aha_md.py            # Primitives shared by all 4 skills:
    │   │                        # frontmatter / sanitize /
    │   │                        # section finder (line-based + fence-aware) /
    │   │                        # atomic_write / locked_record / workspace_anchor /
    │   │                        # schema_version / period_range/id, etc.
    │   └── tests/test_aha_md.py
    ├── idea/
    │   ├── SKILL.md            # Skill definition (frontmatter + workflow)
    │   ├── references/         # Reference material the skill may load
    │   ├── scripts/
    │   │   └── idea_md.py      # CLI: capture / update / list / scan
    │   └── tests/
    │       └── test_idea_md.py # unittest suite for idea_md.py
    ├── dao/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── scripts/
    │   │   └── dao_md.py        # CLI: capture / refine / discuss / list / scan / update
    │   └── tests/
    │       └── test_dao_md.py
    ├── daily/
    │   ├── SKILL.md
    │   ├── references/          # 5 sub-flows: task-capture / overdue-flow / checkin-flow / log-flow / review-flow
    │   ├── scripts/
    │   │   └── daily_md.py      # CLI: task / update / checkin / log / list / scan / review
    │   └── tests/
    │       └── test_daily_md.py
    └── reflect/
        ├── SKILL.md
        ├── references/
        ├── scripts/
        │   └── reflect_md.py    # CLI: aggregate / tags / difficulties / save
        └── tests/
            └── test_reflect_md.py
```

## Installing a skill into a host

> **Important**: All four skill scripts import shared primitives from a sibling `_lib/aha_md.py`
> (the first line of `scripts/*_md.py` does `sys.path.insert(0, .../skills/_lib)`).
> **You must copy / symlink the entire `skills/` parent directory into the host**, or otherwise
> keep `_lib/` as a sibling of the installed skill. **Installing a single skill without `_lib/`
> next to it fails on the very first import (`ImportError`).**

- **Claude Code**: symlink the whole `skills/` directory under `~/.claude/skills/`
  (e.g. `ln -s "$(pwd)/skills" ~/.claude/skills/aha`), preserving the sibling
  relationship between `_lib/` and the four skill folders. You may also symlink
  `idea/ dao/ daily/ reflect/` individually, but you **must** also symlink `_lib/` alongside.
- **Hermes**: install under `~/.hermes/skills/<parent>` or add the parent directory to
  `skills.external_dirs`; same `_lib/` sibling rule. Set `workdir` to a stable parent
  directory so `aha-workspace/` is reused across runs.

## Host capability matrix — the `[SILENT]` protocol

The cron-prompt examples (notably the tail of `idea/SKILL.md`, `dao/SKILL.md:150`, and the tail of `reflect/SKILL.md`) instruct the agent to "if nothing needs user attention, return `[SILENT]`". This is a **host-side** convention: when the host sees the literal `[SILENT]` reply, it should treat that run as a no-op and not send a notification / email / IM.

| Host | `[SILENT]` handling | Recommendation |
|---|---|---|
| **Hermes** | Supported. Returning `[SILENT]` finishes the cron run without a user-facing notification | Use the SKILL.md cron prompt as written |
| **Claude Code (interactive)** | Not applicable — runs once, output goes straight to the user | Ignore the cron-prompt section; the skill set still works for manual invocation |
| **Hand-rolled cron + shell + curl** | Not recognized host-side; the literal string lands in stdout | In the wrapper script `grep -v '^\[SILENT\]$'` or short-circuit notification on match |
| **Other** | Implementation-dependent; if the host turns the agent's output into the notification body, `[SILENT]` becomes noise | Wrap an "empty-output ⇒ skip notification" middleware |

Fallback: if the host doesn't recognize `[SILENT]`, the agent can still return an empty string or a single line `(nothing to surface)` per prompt, and let the host filter on the keyword.

## Running tests

```bash
python3 scripts/run_tests.py
# or
make test
```

## Conventions

- One Markdown file per record; user-supplied content is **render-equivalent preserved** (`## Raw` is never overwritten by tooling; two minimal escapes are applied at write time to protect structural boundaries — see the next two bullets — but the CommonMark rendered output equals the original).
- The workspace is anchored via `aha-workspace/.manifest.json`: the CLI walks up from cwd looking for a manifest, and creates one in cwd if none is found. The manifest records `schema_version` / `timezone` / `host_id`; a TZ mismatch produces a stderr warning.
- Every write path goes through atomic rename (`atomic_write`) + flock (`locked_record`), keeping cron and interactive-agent runs concurrency-safe and avoiding sync-conflict copies on iCloud / Dropbox.
- `update` / `refine` / `checkin` / `discuss` refuse to write outside `aha-workspace/<skill>/`.
- `## Foo` written by the user is escaped to `\## Foo` at write time (CommonMark renders identically); section detection is line-based + fence-aware so it can't be tricked by pseudo-headings inside raw text.
- Single-line free-text fields in frontmatter and section openers (`--note` / `--decision` / `--difficulty` etc.) have `\n` translated to a `↵` mark, preventing row-injection like fake `status: dropped` lines.
- **Frontmatter `tags` is a JSON array**: write `tags: ["agent", "workflow"]` (with the double quotes). `parse_tags_field` calls `json.loads`, so YAML flow style `[agent, workflow]` parses as an empty list — meaning reflect / scan won't see those tags. Keep the quotes when hand-editing.
- New skills follow the same shape: `SKILL.md`, optional `scripts/`, `tests/`, `references/`; reuse all primitives from `skills/_lib/aha_md.py`.
- **Shell-injection surface**: every subcommand that accepts raw user text (`capture --text`, `task --text`, `log --text`, `refine --text`, `discuss --conversation`, etc.) also exposes `--<name>-stdin` / `--<name>-file` entry points. **Agents must always pipe via stdin / file when assembling bash** — embedding `$(...)` / backticks / pipe characters into `--text "..."` lets the shell execute them. The README quick-starts show the inline form for brevity; **only use it for static literals**.
- **Sync-tool conflict files are skipped**: reflect / scan / daily review's `rglob` automatically filters out files whose basename contains `conflict` (case-insensitive) — Dropbox / Box / older iCloud write `task-X (laptop's conflicted copy 2026-05-10).md` during cross-device races. These are sync byproducts, not real records. aha-skills' own atomic rename + flock guarantees we don't produce them; if you see one, diff and merge or delete by hand.
- **Cross-host write-conflict detection**: `flock` is local-only (NFS / iCloud / Dropbox don't propagate it). All `update / refine / checkin / discuss` paths compare mtime before saving — if the file changed between load and save (typically because another host's write synced over), the CLI refuses to overwrite and asks for `--force`. This is best-effort defense (mtime resolution is usually 1 s), not a distributed lock. When sharing a workspace across hosts, prefer not editing at the same time.
