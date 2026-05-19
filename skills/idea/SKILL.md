---
name: idea
description: Capture a fleeting outward-facing creative impulse — anything from a half-formed product idea to a future side project — and optionally iterate on it through multi-turn discussion until a decision lands. Triggers on Chinese 想法/灵感/点子/创意/idea/我有个想法/聊聊这条/继续聊 and English I have an idea / brainstorm / what if we / project idea / explore / continue idea / discuss this idea. Use when the user wants to record something they could later act on, or pick up an in-flight discussion of one, distinct from internal insight (dao), tactical shortcuts (tip), or to-dos (todo).
version: 0.1.0
---

# idea

`idea` captures outward-facing impulses — sparks of "we could build X" or "what if we tried Y." It is the entry point for the lifecycle: capture → refine → decide. The agent records, suggests refinements, and surfaces related ideas; it never decides for the user, never auto-promotes to todo, never overwrites raw.

## Triggers

- 我有个想法 / 想到一个点子 / 这个 idea 不错
- 聊聊这条 idea / 继续聊上次那条 idea / 我想好好聊聊这个想法
- I have an idea / what if we / project idea / brainstorm this
- discuss this idea / continue idea X / let's iterate on this idea
- Slash: /idea

## Storage

Records live at `$HOME/aha/idea.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/idea/scripts/idea.py <verb> ...`.

- `add <raw> [--tag T...] [--status S]` — capture a new idea. Outputs the full record as one JSON line.
- `list [--tag T...] [--status S] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL (one record per line). `--tsv` prints columns `id, raw, refined, status, tags, created_at` with truncated cells.
- `refine <id> <new_refined>` — set or update the refined wording. The previous `refined`, if non-null, is archived into `refinement_log[]` with timestamp. `raw` never changes.
- `log <id> <note>` — append a discussion note (one entry per discussion turn). Note is free-form text; see Discussion protocol below for write-style guidance. Empty note rejected.
- `set-status <id> <status>` — free-form status string (e.g. `incubating`, `decided`, `parked`).

## Constraints

- `raw` is immutable after first write. Refinement goes in `refined`; old `refined` versions are archived in `refinement_log` automatically.
- Status is free-form and advisory. Do not invent a state machine or auto-advance status.
- Cross-skill links use tags only. Do not mint links/parent fields.
- Suggest refinements; do not silently overwrite.

## Examples

```bash
python skills/idea/scripts/idea.py add "用 JSONL 替代 markdown 做事实源" --tag aha-skills --status incubating
python skills/idea/scripts/idea.py list --tag aha-skills --tsv
python skills/idea/scripts/idea.py refine 2026-05-19-a3f7 "数据是核心,工具附着"
python skills/idea/scripts/idea.py log 2026-05-19-a3f7 "本轮:澄清目标用户是谁;焦点:替代方案;下一步:问现在怎么解决"
python skills/idea/scripts/idea.py set-status 2026-05-19-a3f7 decided
```

## Discussion protocol

`idea` supports interruptible, resumable multi-turn discussion. The skill data itself (raw + refined + log[]) carries enough context for any agent to resume from where the last turn left off — no reliance on Claude Code transcripts.

### Entry points

| User says | Agent does |
|---|---|
| "我有个想法 …" | `idea add` writes raw, returns id; agent then proposes a first refined in conversation; user agrees → `idea refine` writes it. |
| "我想好好聊聊这条 idea" | Enter discussion mode. Each completed turn ends with `idea log`. |
| "继续聊上次那条 idea X" | Read raw + refined + log[]; reconstruct the picture; resume from the latest log's "下一步" cue. |

### Shape of one turn

- Agent asks one clarifying question (no overload)
- User answers
- Agent offers an opinion / contrast / suggestion
- After the turn settles, agent calls `idea log <id> <note>` to compress the turn

### How to write a log note

A note typically contains those of the following five dimensions that have content (skip the rest):

- **本轮聊了什么** (trail): condensed Q+A
- **达成了什么** (decisions): consensus formed this turn
- **否决了什么** (rejected): direction ruled out + brief reason
- **当前焦点** (focus): the question being chewed on right now
- **下一步** (next): where to start next time

Other dimensions are allowed: a sudden association, an external reference, a felt-sense / intuition, a third-party perspective. The template is a guide, not a checklist — let the agent decide what's worth keeping per turn.

**Iron rule: data syntax, not narrative syntax**:

- No "我"/"你" pronouns (avoids time-displacement when reading log later or across agents)
- Agent's questions / synthesis use labels: `问:` `焦点:` `下一步:` etc.
- User's exact phrases go in `""` quotes (echoes the immutable-`raw` principle)

#### Good note example

```
本轮:澄清"目标用户是谁"
- 问:脑海里第一个用户画像?答:"团队 lead"
- 问:什么规模的团队?答:10+ 人中大型团队
焦点:这类用户当前用什么工具补这个需求
下一步:先问替代方案——现在怎么解决这个问题
```

#### Bad note examples

```
聊了一些。
```
Density too low — can't reconstruct the picture.

```
讨论了用户/市场/商业模式/竞品/技术方案,详细列举:
1. 用户方面...(500 字)
2. 市场方面...(500 字)
...
```
Density too high — resuming agent has to digest a wall of mixed-confidence content.

### Resumption

When the user says "continue talking about idea X" / "接着上次聊":

1. **Locate**: id given → use it; otherwise `idea list` + raw / tag / status fuzzy match, confirm with user.
2. **Load**: read raw + refined + log[], sort log by `at`.
3. **Rebuild**: trail comes from the log stream; focus / next come from the latest log's note. If the latest entry has no `下一步:` / `焦点:` cue (those dimensions are optional per "How to write a log note"), look back through earlier entries for the most recent labeled cue; if none exists, open with a fresh clarifying question informed by the trail.
4. **Speak**: open with your own phrasing — don't parrot the previous "下一步" verbatim.

If the gap between two consecutive log entries' `at` is > 24h, treat it implicitly as a new resumption — no session boundary field needed.

### When to refine (not every turn)

Every turn writes a log; only turns where the **core proposition** of `refined` shifts also call `refine`.

- Picture sharpens after several turns → agent proposes "I'd update refined to X — sound right?" → user agrees → `refine`.
- A pivotal moment ("the real problem isn't A, it's B") → propose refine immediately.

**log vs refine boundary**: log is the per-turn process trace; refine is the periodic phrasing update.

### Closing out

When the discussion reaches an actionable plan / decision:

- Final `refine` writes the terminal phrasing
- Agent proposes `set-status decided` (or `parked` / `dropped`); user agrees → execute
- Optional: a closing log note "结论:X;为什么:Y;后续动作:Z"

### What not to do

- Don't auto-promote to `todo` (user says "I'll do this" → user calls `todo add`)
- Don't invent thread / session / conversation concepts between log entries
- Don't push focus / next into structured fields inside log elements (`{at, note}` stays simple)
- Don't decide for the user — focus / next are agent suggestions; refine / set-status need user assent
