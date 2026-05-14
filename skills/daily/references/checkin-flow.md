# Check-in Workflow

Loaded by the `daily` skill when the user wants to talk through a task's progress ("X 现在进展..." / "聊聊 X 的卡点" / "想梳理一下 X" / "let's talk about X"). Pre-requisite: you have already read `daily/SKILL.md`.

## Procedure

1. Have the conversation in chat (multi-turn). Probe for:
   - what changed since last check-in
   - what's blocking
   - what the next concrete step is
2. When it winds down, summarize in **1-3 sentences** for the takeaway.
3. Run:
   ```bash
   python3 <skill-dir>/scripts/daily_md.py checkin <file> \
     --topic "<theme>" \
     --conversation "<full transcript>" \
     --takeaway "<1-3 sentences>" \
     [--difficulty "<surfaced blocker>"] \
     [--next-step "<concrete next>"]
   ```
4. The check-in transcript lands in `aha-workspace/daily/check-ins/`; the main task file gets a one-line summary linking to it. If `--difficulty` is provided, it's also appended to the task's `## Difficulty Log`.

## Hard rule

A check-in **without** a takeaway is a context leak — always summarize before writing.
