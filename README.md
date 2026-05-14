# aha-skills

A collection of lightweight, file-based skills for AI agents (Claude Code, Hermes, OpenAI agents). Each skill is self-contained in its own folder, exposes a `SKILL.md` describing when and how to use it, and persists state as plain Markdown so the human and the agent share the same source of truth.

All runtime data lives under a shared `aha-workspace/` directory in the host's working directory. Each skill owns a sub-folder there (e.g. `aha-workspace/idea/`).

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
└── dao/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── references/
    ├── scripts/
    │   └── dao_md.py       # CLI: capture / refine / discuss / scan / update
    └── tests/
        └── test_dao_md.py
```

## Installing a skill into a host

- **Claude Code**: drop the skill folder into `~/.claude/skills/` (or symlink it), then invoke via the `Skill` tool / slash command.
- **Hermes**: install under `~/.hermes/skills/<skill-name>` or add the parent directory to `skills.external_dirs`. Set `workdir` to a stable parent so `aha-workspace/` is reused across runs.
- **OpenAI agents**: load `agents/openai.yaml` for display metadata and point the agent at the skill folder.

## Running tests

```bash
python3 -m unittest discover -s idea/tests -t idea
python3 -m unittest discover -s dao/tests -t dao
```

## Conventions

- One Markdown file per record; raw user content is preserved verbatim.
- All paths resolve relative to the current working directory via `aha-workspace/`.
- Skills should never write outside `aha-workspace/<skill>/` at runtime.
- New skills follow the same shape: `SKILL.md`, optional `scripts/`, `tests/`, `references/`, `agents/`.
