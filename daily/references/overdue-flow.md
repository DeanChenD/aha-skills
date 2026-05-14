# Overdue Reminder Workflow (core safety net)

Loaded by the `daily` skill when handling overdue tasks. Pre-requisite: you have already read `daily/SKILL.md`.

This is the user's primary safety net: when a task slips, the agent surfaces it, asks for the difficulty, and helps reschedule.

## Triggers

- The user asks "有什么过期的没?", "看看我有什么没做完的", "what's overdue", "anything I'm late on".
- A scheduled run.
- The agent notices in conversation that a task is now overdue.

## Procedure (handle **one task per turn**, oldest due first)

1. `scan --mode overdue` to list overdue tasks.
2. Pick the oldest. Tell the user: title + how long overdue.
3. Ask exactly **one** question: "<title> 为什么没按时完成？遇到了什么困难？"
4. Wait for the user's answer. Then choose ONE of:

   - **They describe a blocker**:
     - Run `update <file> --difficulty "<their answer>"` to record it.
     - Then ask: "想推迟到什么时候？" — once they answer, `update <file> --due "<new>" --postpone-reason "<the same blocker, restated briefly>"`.

   - **They say "其实做完了，忘了改"**: `update <file> --status done`.

   - **They say "算了不做了" / "没必要"**: `update <file> --status dropped --note "<reason>"`.

   - **They say "今天就做"**: do not modify; offer to set status to `in_progress` and check back later.

5. If more overdue tasks remain, ask if they want to handle the next one — do not steamroll.

## Hard rules

- Never modify due, status, or any record without a clear user answer.
- Do not auto-postpone.
- One task per turn. The user gets to choose whether to keep going.
