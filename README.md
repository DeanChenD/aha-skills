# aha-skills

A collection of lightweight, file-based skills for AI agents (Claude Code, Hermes, OpenAI agents). Each skill is self-contained in its own folder, exposes a `SKILL.md` describing when and how to use it, and persists state as plain Markdown so the human and the agent share the same source of truth.

All runtime data lives under a shared `aha-workspace/` directory in the host's working directory. Each skill owns a sub-folder there (e.g. `aha-workspace/idea/`).

## Design Philosophy

`aha-skills` 不是一个工具集合，而是关于「如何把易逝的认知瞬间留下」的三个分工：

- `idea` — 向外的行动直觉：捕捉 → 孵化 → 决策成行
- `dao` — 向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- `daily` — 维持节奏：任务、日志、check-in、复盘

四条贯穿三者的设计公约：

1. **Markdown 是单一事实源**。Agent 和人读同一份 `.md`，不存在 agent 私有 state。
2. **原文不可变**。`## Raw` 永远保留用户原话；提炼写在 `## Refined`，旧版进 `## Refinement Log`。这是用户认知演化的考古层，不是版本噪音。
3. **state mutation 走 deterministic CLI**。`*_md.py` 同时是 agent 的写入路径和测试边界，挡住 LLM 自由编辑时的格式漂移。
4. **不强加 workflow**。`dao` 没有状态机，`daily` 不自动顺延 due —— agent 提建议，用户做决定。

## Skills

### `idea/` — Idea Inbox & Incubator

Capture sudden ideas, timestamp them, classify them, and incubate them into Markdown research plans.

- **Trigger**: `/idea` or any request to record / review / continue / kill an idea.
- **Storage**: `./aha-workspace/idea/idea-md/<idea-id>.md` (one file per idea, raw text never overwritten).
- **Lifecycle**: `inbox → researching → planning → completed` (with `paused` / `killed` as terminal options).
- **CLI**: `idea/scripts/idea_md.py` provides deterministic `capture`, `update`, and `scan` subcommands.

See [`idea/SKILL.md`](idea/SKILL.md) for the full workflow, Markdown shape, and scheduled-review pattern.

#### Quick start

```bash
# Capture an idea
python3 idea/scripts/idea_md.py capture \
  --text "Build a tiny idea inbox" \
  --source chat \
  --status researching \
  --category product \
  --tags "idea,research"

# List stale or due-for-review ideas
python3 idea/scripts/idea_md.py scan --stale-days 7 --include-paused

# Advance an idea
python3 idea/scripts/idea_md.py update \
  ./aha-workspace/idea/idea-md/<file>.md \
  --status planning \
  --decision "Ready for a concrete plan." \
  --bump-review
```

### `dao/` — Insight Capture, Refinement & Review (感悟 / 道)

Capture personal insights verbatim, polish them into a refined sediment, optionally explore them through multi-turn philosophical discussion, and periodically resurface old ones for review. Counterpart to `idea`: where `idea` is for outward-facing actions, `dao` is for inner-facing realizations.

- **Trigger**: `/dao`, "我悟到了 / 想通了 / 感悟到 ...", "再帮我提炼一下", "展开聊聊", "翻翻以前的感悟".
- **Storage**:
  - Main records: `./aha-workspace/dao/dao-md/<dao-id>.md` (raw text never overwritten; `## Refined` rotated; `## Refinement Log` archives prior versions).
  - Discussion transcripts: `./aha-workspace/dao/sessions/<dao-id>-session-NNN.md` (linked from main file with a 1-3 sentence takeaway).
- **Actions** (no forced status workflow): `capture`, `refine`, `discuss`, `scan`, `update`.
- **CLI**: `dao/scripts/dao_md.py`.

See [`dao/SKILL.md`](dao/SKILL.md) for triggers, Markdown shape, and the scheduled-review pattern.

#### Quick start

```bash
# Capture a raw insight
F=$(python3 dao/scripts/dao_md.py capture \
  --text "Fear is a compass, not a stop sign" \
  --category life --tags "courage,fear")

# Refine it (auto-archives the previous version into ## Refinement Log)
python3 dao/scripts/dao_md.py refine "$F" \
  --text "Fear marks the edge of where I should grow."

# Log a philosophical discussion
python3 dao/scripts/dao_md.py discuss "$F" \
  --topic "Fear vs aversion" \
  --conversation "user: ...\nagent: ..." \
  --takeaway "Distinguish fear (points at growth) from aversion (points at self-protection)."

# Resurface 3 random old daos for review (also bumps review_count)
python3 dao/scripts/dao_md.py scan --mode random --limit 3
python3 dao/scripts/dao_md.py scan --mode least-reviewed --tag courage
```

### `daily/` — Tasks, Daily Logs, Check-ins & Periodic Reviews

Manage important todos with explicit due dates and postponements, log stage-by-stage progress and surfaced difficulties, capture per-day journal entries, and produce day/week/month reviews. The "节奏型" companion to `idea` (outward action) and `dao` (inward realization).

- **Trigger**: `/daily`, "今天要做...", "加个待办", "今天没做完...", "想推迟到...", "聊聊 X 的进展", "记一笔", "今天感觉...", "看看这周", "周回顾".
- **Storage**:
  - Tasks: `./aha-workspace/daily/tasks/task-<id>.md` (status workflow + difficulty / postponement / check-in logs).
  - Daily logs: `./aha-workspace/daily/logs/log-YYYY-MM-DD.md` (one file per day, multiple `## HH:MM — title` entries appended within).
  - Check-in transcripts: `./aha-workspace/daily/check-ins/<task-id>-checkin-NNN.md`.
  - Reviews (agent-written via `Write`): `./aha-workspace/daily/reviews/review-<period-id>.md`.
- **Actions**: `task` / `update` / `checkin` / `log` / `scan` (no forced status workflow).
- **CLI**: `daily/scripts/daily_md.py`.

See [`daily/SKILL.md`](daily/SKILL.md) for the overdue-reminder conversation flow, check-in pattern, and review skeleton.

#### Quick start

```bash
# Capture a task
T=$(python3 daily/scripts/daily_md.py task \
  --text "Write the v1 spec" --due "2030-01-15T18:00" \
  --priority high --tags "work,doc")

# Postpone with an explicit reason (logged to ## Postponement Log)
python3 daily/scripts/daily_md.py update "$T" \
  --due "2030-01-20T18:00" --postpone-reason "PRD review pending"

# Record a check-in
python3 daily/scripts/daily_md.py checkin "$T" \
  --topic "Mid-build status" \
  --conversation "user: status?\nagent: 30% done." \
  --takeaway "Half a day to lock the data model." \
  --difficulty "data model still fuzzy" \
  --next-step "Lock model tomorrow morning"

# Append a daily log entry
python3 daily/scripts/daily_md.py log \
  --text "Got distracted three times this afternoon" \
  --time "14:30" --title "Focus dip" --tags "work,mood"

# What's overdue right now?
python3 daily/scripts/daily_md.py scan --mode overdue

# Pull this week's tasks + log entries for a review
python3 daily/scripts/daily_md.py scan --mode period --period week --type all
```

## Repository layout

```
aha-skills/
├── README.md
├── .gitignore
├── idea/
│   ├── SKILL.md            # Skill definition (frontmatter + workflow)
│   ├── agents/
│   │   └── openai.yaml     # OpenAI agent interface metadata
│   ├── references/         # Reference material the skill may load
│   ├── scripts/
│   │   └── idea_md.py      # CLI: capture / update / scan
│   └── tests/
│       └── test_idea_md.py # unittest suite for idea_md.py
├── dao/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── references/
│   ├── scripts/
│   │   └── dao_md.py        # CLI: capture / refine / discuss / scan / update
│   └── tests/
│       └── test_dao_md.py
└── daily/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── references/
    ├── scripts/
    │   └── daily_md.py      # CLI: task / update / checkin / log / scan
    └── tests/
        └── test_daily_md.py
```

## Installing a skill into a host

- **Claude Code**: drop the skill folder into `~/.claude/skills/` (or symlink it), then invoke via the `Skill` tool / slash command.
- **Hermes**: install under `~/.hermes/skills/<skill-name>` or add the parent directory to `skills.external_dirs`. Set `workdir` to a stable parent so `aha-workspace/` is reused across runs.
- **OpenAI agents**: load `agents/openai.yaml` for display metadata and point the agent at the skill folder.

## Running tests

```bash
python3 idea/tests/test_idea_md.py
python3 dao/tests/test_dao_md.py
python3 daily/tests/test_daily_md.py
```

## Conventions

- One Markdown file per record; raw user content is preserved verbatim.
- All paths resolve relative to the current working directory via `aha-workspace/`.
- Skills should never write outside `aha-workspace/<skill>/` at runtime.
- New skills follow the same shape: `SKILL.md`, optional `scripts/`, `tests/`, `references/`, `agents/`.
