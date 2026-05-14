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

## Repository layout

```
aha-skills/
├── README.md
├── .gitignore
└── idea/
    ├── SKILL.md            # Skill definition (frontmatter + workflow)
    ├── agents/
    │   └── openai.yaml     # OpenAI agent interface metadata
    ├── references/         # Reference material the skill may load
    ├── scripts/
    │   └── idea_md.py      # CLI: capture / update / scan
    └── tests/
        └── test_idea_md.py # unittest suite for idea_md.py
```

## Installing a skill into a host

- **Claude Code**: drop the skill folder into `~/.claude/skills/` (or symlink it), then invoke via the `Skill` tool / slash command.
- **Hermes**: install under `~/.hermes/skills/<skill-name>` or add the parent directory to `skills.external_dirs`. Set `workdir` to a stable parent so `aha-workspace/` is reused across runs.
- **OpenAI agents**: load `agents/openai.yaml` for display metadata and point the agent at the skill folder.

## Running tests

```bash
python3 -m unittest discover -s idea/tests -t idea
```

## Conventions

- One Markdown file per record; raw user content is preserved verbatim.
- All paths resolve relative to the current working directory via `aha-workspace/`.
- Skills should never write outside `aha-workspace/<skill>/` at runtime.
- New skills follow the same shape: `SKILL.md`, optional `scripts/`, `tests/`, `references/`, `agents/`.
