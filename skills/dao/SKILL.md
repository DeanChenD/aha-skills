---
name: dao
description: Capture an inward-facing realization, principle, or methodology — the "道" or aha moment that names how things work — and optionally trace its meaning, boundaries, or relationships through multi-turn discussion. Triggers on Chinese 感悟/领悟/方法论/道/原则/aha/想明白了/深谈这条/继续聊这条 and English insight / realization / principle / methodology / lesson learned / discuss this dao / continue dao. Use when the user is naming a pattern they noticed (internal), or picking up an in-flight discussion of one, distinct from outward ideas (idea), tactical tips (tip), or work to do (todo).
version: 0.1.0
---

# dao

`dao` records the moment a pattern crystallizes. It preserves the user's exact words (`raw`), then optionally distills them (`refined`) without ever erasing the original. The agent may suggest a tighter phrasing, surface related dao through tags, or invite a deeper conversation — but the wording belongs to the user.

## Triggers

- 我突然意识到 / 这个其实就是 / 想明白了 / 这是一种 ...
- 深谈这条 dao / 继续聊上次那条 dao / 为什么这条让我有 aha
- insight / realization / lesson learned / I just realized
- discuss this dao / continue dao X / let's trace this dao further
- Slash: /dao

## Storage

Records live at `$HOME/aha/dao.jsonl` (resolved by `Path.home() / "aha"`, overridable via `AHA_HOME`). One JSON record per line.

## Verbs

Run scripts with `python skills/dao/scripts/dao.py <verb> ...`.

- `add <raw> [--tag T...]` — capture a dao. Outputs the full record as one JSON line.
- `list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]` — browse. Default JSONL. `--tsv` prints columns `id, raw, refined, tags, created_at`.
- `refine <id> <new_refined>` — set or update refined wording. Previous `refined`, if any, is archived to `refinement_log[]`. `raw` never changes.
- `log <id> <note>` — append a discussion note (one entry per discussion turn). Note is free-form text; see Discussion protocol below for write-style guidance. Empty note rejected.

## Constraints

- `raw` is immutable. Never edit a user's exact phrasing — refine into `refined` instead.
- A "deep talk" or follow-up conversation does not need its own verb; the outcome is one more refinement.
- No status — dao does not have stages.
- Cross-skill links via tags only.

## Examples

```bash
python skills/dao/scripts/dao.py add "好脚手架是替你说不的人,不是替你说是的人"
python skills/dao/scripts/dao.py list --tag 系统设计 --tsv
python skills/dao/scripts/dao.py refine 2026-05-19-1c2f "好的脚手架替你说不"
python skills/dao/scripts/dao.py log 2026-05-19-1c2f "本轮:边界澄清;焦点:反例搜索;下一步:列举 3 个不像脚手架的工具检验"
```

## Discussion protocol

`dao` discussions tend toward **meaning-tracing and boundary-clarification** rather than idea's actionable-plan exploration — but the mechanics are the same. The skill data itself (raw + refined + log[]) carries enough context for any agent to resume from where the last turn left off — no reliance on Claude Code transcripts.

### Entry points

| User says | Agent does |
|---|---|
| "我突然意识到 …" | `dao add` writes raw, returns id; agent may propose a tighter refined in conversation; user agrees → `dao refine` writes it. |
| "我想深谈这条 dao" | Enter discussion mode. Each completed turn ends with `dao log`. |
| "继续聊上次那条 dao X" | Read raw + refined + log[]; reconstruct the picture; resume from the latest log's "下一步" cue. |

### Shape of one turn

- Agent asks one clarifying question (no overload)
- User answers
- Agent offers an opinion / contrast / suggestion
- After the turn settles, agent calls `dao log <id> <note>` to compress the turn

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
本轮:澄清这条 dao 的边界
- 问:它适用于所有脚手架,还是只适用于决策类工具?答:"目前看是所有脚手架"
- 问:有反例吗?答:暂时想不到,但需要更多场景检验
焦点:寻找可能让这条 dao 失效的反例
下一步:列举 3 个不像脚手架的工具,看是否仍适用
```

#### Bad note examples

```
聊了一些。
```
Density too low — can't reconstruct the picture.

```
讨论了这条 dao 在所有场景下的适用性,详细列举:
1. 工具方面...(500 字)
2. 方法论方面...(500 字)
...
```
Density too high — resuming agent has to digest a wall of mixed-confidence content.

### Resumption

When the user says "continue talking about dao X" / "接着上次聊":

1. **Locate**: id given → use it; otherwise `dao list` + raw / tag fuzzy match, confirm with user.
2. **Load**: read raw + refined + log[], sort log by `at`.
3. **Rebuild**: trail comes from the log stream; focus / next come from the latest log's note. If the latest entry has no `下一步:` / `焦点:` cue (those dimensions are optional per "How to write a log note"), look back through earlier entries for the most recent labeled cue; if none exists, open with a fresh clarifying question informed by the trail.
4. **Speak**: open with your own phrasing — don't parrot the previous "下一步" verbatim.

If the gap between two consecutive log entries' `at` is > 24h, treat it implicitly as a new resumption — no session boundary field needed.

### When to refine (not every turn)

Every turn writes a log; only turns where the **core proposition** of `refined` shifts also call `refine`.

- Picture sharpens after several turns → agent proposes "I'd update refined to X — sound right?" → user agrees → `refine`.
- A pivotal moment ("the real essence isn't A, it's B") → propose refine immediately.

**log vs refine boundary**: log is the per-turn process trace; refine is the periodic phrasing update.

### Closing out

dao does not have a status machine, so no `set-status` step. When the discussion has done its work:

- Operationally, closure is signaled by (a) `refined` wording stabilizing across consecutive turns (no proposed updates land), or (b) the user explicitly indicating the picture has landed
- Final `refine` writes the terminal phrasing (if it has shifted)
- Optional: a closing log note "结论:X;为什么:Y"

dao discussions can also stay open indefinitely — that's normal. Don't force closure.

### What not to do

- Don't auto-promote dao realizations into `idea` or `todo` (user decides)
- Don't invent thread / session / conversation concepts between log entries
- Don't push focus / next into structured fields inside log elements (`{at, note}` stays simple)
- Don't decide for the user — focus / next are agent suggestions; refine needs user assent
