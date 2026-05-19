# idea / dao Discussion Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable interruptible, resumable multi-turn discussions on idea / dao records by reusing the existing `log[]` primitive (currently todo-only). Zero new top-level fields, zero new file types.

**Architecture:** `store.append_log` already exists and is skill-agnostic (`store.py:240-248`). Each of idea / dao gets a thin `log <id> <note>` CLI subparser that delegates to it (mirroring todo). The `add` verb in idea / dao starts seeding `"log": []` for schema consistency. The product surface — *how* agents write/read log notes during a discussion — is governed by a "Discussion protocol" section added to each SKILL.md. AGENTS.md §5 and §6.3 are updated to reflect that `log[]` is no longer todo-exclusive and that discussion process goes through `log` while distilled phrasing goes through `refine`.

**Tech Stack:** Python 3.11+ stdlib only, pytest (dev). No new dependencies.

**Spec:** [`docs/superpowers/specs/2026-05-19-idea-dao-discussion-design.md`](../specs/2026-05-19-idea-dao-discussion-design.md)

---

## File Map

**Modify:**
- `AGENTS.md` — §5 table row for `log[]`, §6.3 wording
- `skills/idea/scripts/idea.py` — `cmd_add` seeds `"log": []`; new `cmd_log`; `log` subparser
- `skills/dao/scripts/dao.py` — same shape as idea
- `skills/idea/tests/test_idea.py` — extend `test_add_emits_full_record`; add 5 log tests
- `skills/dao/tests/test_dao.py` — extend `test_add_emits_record`; add 5 log tests
- `skills/idea/SKILL.md` — Verbs gets `log`; new Discussion protocol section; Examples gets `log`
- `skills/dao/SKILL.md` — same as idea, with a one-sentence dao-specific framing note

**Create:** none.

---

## Task 1: Sync AGENTS.md §5 and §6.3

**Files:**
- Modify: `AGENTS.md` (line 60 table row and §6.3 paragraph)

**Why first:** Locking in the new contract before code change prevents writing implementation that violates the soon-to-be-updated rules.

- [ ] **Step 1: Edit AGENTS.md §5 table row for `log[]`**

Locate the row (around line 60):

```
| `log[]` 仅追加,不重写不删除 | `store.append_log()`(目前仅 `todo` 用)|
```

Replace with:

```
| `log[]` 仅追加,不重写不删除 | `store.append_log()`,idea / dao / todo 均可用 |
```

- [ ] **Step 2: Edit AGENTS.md §6.3 paragraph**

Locate (around line 70):

```
- **"深聊" / 后续讨论 / 多次思考的产物 = 一次 `refine`**,不要发明 "follow-up" / "thread" / "discussion" 之类的新 verb。
```

Replace with:

```
- **多次讨论的过程用 `log` 追加;多次讨论后形成的精炼表述走一次 `refine`**(旧 refined 入 `refinement_log[]`)。不要发明 "follow-up" / "thread" / "discussion" / "session" / "conversation" 之类的新 verb 或字段。
```

- [ ] **Step 3: Verify edits with `grep`**

Run:
```bash
grep -n "log\[\] 仅追加" AGENTS.md
grep -n "多次讨论的过程" AGENTS.md
```
Expected: each finds exactly one line, with the new wording.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "$(cat <<'EOF'
docs(AGENTS): open log[] to idea/dao; clarify log vs refine boundary

§5 table: log[] is no longer todo-exclusive — store.append_log() is
usable from idea / dao / todo. §6.3 splits "process" (log) from
"distilled phrasing" (refine), so multi-turn discussion has an
explicit append-only home without inventing thread/session verbs.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: idea — `log` verb (TDD)

**Files:**
- Modify: `skills/idea/scripts/idea.py`
- Test: `skills/idea/tests/test_idea.py`

- [ ] **Step 1: Extend `test_add_emits_full_record` to assert `log == []`**

In `skills/idea/tests/test_idea.py`, find:

```python
def test_add_emits_full_record(run, aha_home):
    proc = run("add", "first idea", "--tag", "x", "--tag", "y")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "first idea"
    assert rec["tags"] == ["x", "y"]
    assert rec["status"] is None
    assert rec["refined"] is None
    assert rec["refinement_log"] == []
    assert rec["id"]
    assert rec["created_at"]
    assert rec["updated_at"] == rec["created_at"]
```

Add one more assertion right after `assert rec["refinement_log"] == []`:

```python
    assert rec["log"] == []
```

- [ ] **Step 2: Add 5 log tests at the bottom of `test_idea.py`**

Append to `skills/idea/tests/test_idea.py`:

```python


def test_log_appends_note(run):
    rid = json.loads(run("add", "discuss me").stdout)["id"]
    proc = run("log", rid, "本轮:澄清目标用户\n焦点:替代方案\n下一步:问现在怎么解决")
    rec = json.loads(proc.stdout.strip())
    assert len(rec["log"]) == 1
    entry = rec["log"][0]
    assert entry["note"] == "本轮:澄清目标用户\n焦点:替代方案\n下一步:问现在怎么解决"
    assert entry["at"]


def test_log_multiple_appends_in_order(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    run("log", rid, "first")
    run("log", rid, "second")
    proc = run("log", rid, "third")
    rec = json.loads(proc.stdout.strip())
    notes = [e["note"] for e in rec["log"]]
    assert notes == ["first", "second", "third"]
    ats = [e["at"] for e in rec["log"]]
    assert ats == sorted(ats)


def test_log_unknown_id_exits_1(run):
    proc = run("log", "missing-id", "note", expect_code=1)
    assert "not found" in proc.stderr


def test_log_empty_note_exits_1(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("log", rid, "", expect_code=1)
    assert "empty" in proc.stderr.lower() or "must not be empty" in proc.stderr.lower()


def test_log_preserves_other_fields(run):
    rid = json.loads(run("add", "rough", "--tag", "t1").stdout)["id"]
    run("refine", rid, "polished")
    proc = run("log", rid, "trail note")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "rough"
    assert rec["refined"] == "polished"
    assert rec["refinement_log"] == []
    assert rec["tags"] == ["t1"]
    assert len(rec["log"]) == 1
    assert rec["log"][0]["note"] == "trail note"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
python -m pytest skills/idea/tests/test_idea.py -v
```

Expected:
- `test_add_emits_full_record` fails on `KeyError: 'log'` (new assertion)
- All 5 `test_log_*` fail with argparse error "invalid choice: 'log'" (subparser missing)

- [ ] **Step 4: Modify `idea.py` — seed `log: []` in `cmd_add`**

In `skills/idea/scripts/idea.py`, locate `cmd_add`:

```python
def cmd_add(args) -> None:
    ts = store.now_iso()
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": ts,
        "updated_at": ts,
        "status": args.status,
        "refined": None,
        "refinement_log": [],
    }
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))
```

Add `"log": [],` after `"refinement_log": [],` so the dict becomes:

```python
def cmd_add(args) -> None:
    ts = store.now_iso()
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": ts,
        "updated_at": ts,
        "status": args.status,
        "refined": None,
        "refinement_log": [],
        "log": [],
    }
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))
```

- [ ] **Step 5: Add `cmd_log` function**

In `skills/idea/scripts/idea.py`, after `cmd_refine` (around line 33), insert:

```python
def cmd_log(args) -> None:
    if not args.note.strip():
        print("Error: note must not be empty", file=sys.stderr)
        sys.exit(1)
    out = store.append_log(SKILL, args.id, args.note)
    print(store.to_jsonl_line(out))
```

- [ ] **Step 6: Register `log` subparser in `main()`**

In `skills/idea/scripts/idea.py`, inside `main()` after the `set-status` subparser block (around line 88), add:

```python
    g = sub.add_parser("log", help="append a discussion note")
    g.add_argument("id")
    g.add_argument("note")
    g.set_defaults(fn=cmd_log)
```

The block should be added before `args = p.parse_args()`.

- [ ] **Step 7: Run tests to verify they pass**

Run:
```bash
python -m pytest skills/idea/tests/test_idea.py -v
```

Expected: all tests pass (including 5 new log tests and the extended `test_add_emits_full_record`).

- [ ] **Step 8: Commit**

```bash
git add skills/idea/scripts/idea.py skills/idea/tests/test_idea.py
git commit -m "$(cat <<'EOF'
feat(idea): log verb for discussion notes

Mirrors todo's log primitive — thin wrapper over store.append_log so
ideas can carry an append-only stream of discussion notes (trail /
decisions / rejected / focus / next written into a free-form note
field per turn). cmd_add now seeds log: [] for schema consistency.
Empty note rejected with exit 1.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: dao — `log` verb (TDD)

**Files:**
- Modify: `skills/dao/scripts/dao.py`
- Test: `skills/dao/tests/test_dao.py`

Mirrors Task 2 — full code repeated below for out-of-order reading.

- [ ] **Step 1: Extend `test_add_emits_record` to assert `log == []`**

In `skills/dao/tests/test_dao.py`, find:

```python
def test_add_emits_record(run, aha_home):
    proc = run("add", "原话很重要", "--tag", "认知")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "原话很重要"
    assert rec["tags"] == ["认知"]
    assert rec["refined"] is None
    assert rec["refinement_log"] == []
    assert "status" not in rec
```

Add right after `assert rec["refinement_log"] == []`:

```python
    assert rec["log"] == []
```

- [ ] **Step 2: Add 5 log tests at the bottom of `test_dao.py`**

Append to `skills/dao/tests/test_dao.py`:

```python


def test_log_appends_note(run):
    rid = json.loads(run("add", "深谈我").stdout)["id"]
    proc = run("log", rid, "本轮:意义溯源\n焦点:边界澄清\n下一步:问反例")
    rec = json.loads(proc.stdout.strip())
    assert len(rec["log"]) == 1
    entry = rec["log"][0]
    assert entry["note"] == "本轮:意义溯源\n焦点:边界澄清\n下一步:问反例"
    assert entry["at"]


def test_log_multiple_appends_in_order(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    run("log", rid, "first")
    run("log", rid, "second")
    proc = run("log", rid, "third")
    rec = json.loads(proc.stdout.strip())
    notes = [e["note"] for e in rec["log"]]
    assert notes == ["first", "second", "third"]
    ats = [e["at"] for e in rec["log"]]
    assert ats == sorted(ats)


def test_log_unknown_id_exits_1(run):
    proc = run("log", "missing-id", "note", expect_code=1)
    assert "not found" in proc.stderr


def test_log_empty_note_exits_1(run):
    rid = json.loads(run("add", "x").stdout)["id"]
    proc = run("log", rid, "", expect_code=1)
    assert "empty" in proc.stderr.lower() or "must not be empty" in proc.stderr.lower()


def test_log_preserves_other_fields(run):
    rid = json.loads(run("add", "原话", "--tag", "认知").stdout)["id"]
    run("refine", rid, "提炼")
    proc = run("log", rid, "trail note")
    rec = json.loads(proc.stdout.strip())
    assert rec["raw"] == "原话"
    assert rec["refined"] == "提炼"
    assert rec["refinement_log"] == []
    assert rec["tags"] == ["认知"]
    assert len(rec["log"]) == 1
    assert rec["log"][0]["note"] == "trail note"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
python -m pytest skills/dao/tests/test_dao.py -v
```

Expected:
- `test_add_emits_record` fails on `KeyError: 'log'`
- All 5 `test_log_*` fail with argparse error "invalid choice: 'log'"

- [ ] **Step 4: Modify `dao.py` — seed `log: []` in `cmd_add`**

In `skills/dao/scripts/dao.py`, locate `cmd_add` and add `"log": [],` after `"refinement_log": [],` so the dict becomes:

```python
def cmd_add(args) -> None:
    ts = store.now_iso()
    rec = {
        "id": store.new_id(),
        "raw": args.raw,
        "tags": args.tag or [],
        "created_at": ts,
        "updated_at": ts,
        "refined": None,
        "refinement_log": [],
        "log": [],
    }
    store.ensure_initialized(SKILL)
    store.append_record(SKILL, rec)
    print(store.to_jsonl_line(rec))
```

- [ ] **Step 5: Add `cmd_log` function**

In `skills/dao/scripts/dao.py`, after `cmd_refine` (around line 33), insert:

```python
def cmd_log(args) -> None:
    if not args.note.strip():
        print("Error: note must not be empty", file=sys.stderr)
        sys.exit(1)
    out = store.append_log(SKILL, args.id, args.note)
    print(store.to_jsonl_line(out))
```

- [ ] **Step 6: Register `log` subparser in `main()`**

In `skills/dao/scripts/dao.py`, inside `main()` after the `refine` subparser block (around line 73), add:

```python
    g = sub.add_parser("log", help="append a discussion note")
    g.add_argument("id")
    g.add_argument("note")
    g.set_defaults(fn=cmd_log)
```

Add this block before `args = p.parse_args()`.

- [ ] **Step 7: Run tests to verify they pass**

Run:
```bash
python -m pytest skills/dao/tests/test_dao.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add skills/dao/scripts/dao.py skills/dao/tests/test_dao.py
git commit -m "$(cat <<'EOF'
feat(dao): log verb for discussion notes

Mirrors idea's log verb — append-only stream of discussion notes for
multi-turn talks. cmd_add seeds log: [] for schema consistency. Empty
note rejected.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: idea SKILL.md — Discussion protocol

**Files:**
- Modify: `skills/idea/SKILL.md`

- [ ] **Step 1: Add `log` to the Verbs section**

In `skills/idea/SKILL.md`, find the Verbs section. Right after the `refine` line (around line 27), add:

```
- `log <id> <note>` — append a discussion note (one entry per discussion turn). Note is free-form text; see Discussion protocol below for write-style guidance. Empty note rejected.
```

The `set-status` line should remain right below this new line.

- [ ] **Step 2: Append the Discussion protocol section**

At the end of `skills/idea/SKILL.md` (after the Examples section closes), append the following block verbatim:

````markdown

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
3. **Rebuild**: trail comes from the log stream; focus / next come from the latest log's note.
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
````

- [ ] **Step 3: Add a `log` line to the Examples section**

In `skills/idea/SKILL.md`, find the Examples block (around lines 39-44):

```bash
python skills/idea/scripts/idea.py add "用 JSONL 替代 markdown 做事实源" --tag aha-skills --status incubating
python skills/idea/scripts/idea.py list --tag aha-skills --tsv
python skills/idea/scripts/idea.py refine 2026-05-19-a3f7 "数据是核心,工具附着"
python skills/idea/scripts/idea.py set-status 2026-05-19-a3f7 decided
```

Add a `log` line after the `refine` line so the block becomes:

```bash
python skills/idea/scripts/idea.py add "用 JSONL 替代 markdown 做事实源" --tag aha-skills --status incubating
python skills/idea/scripts/idea.py list --tag aha-skills --tsv
python skills/idea/scripts/idea.py refine 2026-05-19-a3f7 "数据是核心,工具附着"
python skills/idea/scripts/idea.py log 2026-05-19-a3f7 "本轮:澄清目标用户是谁\n焦点:替代方案\n下一步:问现在怎么解决"
python skills/idea/scripts/idea.py set-status 2026-05-19-a3f7 decided
```

- [ ] **Step 4: Verify edits**

Run:
```bash
grep -n "^- \`log " skills/idea/SKILL.md
grep -n "## Discussion protocol" skills/idea/SKILL.md
grep -n "log 2026-05-19-a3f7" skills/idea/SKILL.md
```
Expected: each finds at least one match.

- [ ] **Step 5: Commit**

```bash
git add skills/idea/SKILL.md
git commit -m "$(cat <<'EOF'
docs(idea): discussion protocol section

Adds the agent-facing protocol for multi-turn idea discussion: entry
points, turn shape, log note write-style (data syntax / no pronouns
/ good and bad examples), resumption procedure, when-to-refine, and
closing-out rules. Verbs and Examples updated to reflect the new log
verb.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: dao SKILL.md — Discussion protocol

**Files:**
- Modify: `skills/dao/SKILL.md`

dao reuses idea's protocol; only the opening note differs.

- [ ] **Step 1: Add `log` to the Verbs section**

In `skills/dao/SKILL.md`, find the Verbs section. Right after the `refine` line (around line 27), add:

```
- `log <id> <note>` — append a discussion note (one entry per discussion turn). Note is free-form text; see Discussion protocol below for write-style guidance. Empty note rejected.
```

- [ ] **Step 2: Append the Discussion protocol section**

At the end of `skills/dao/SKILL.md` (after the Examples section), append the following block verbatim. Note the **opening sentence is dao-specific**; the rest mirrors idea.

````markdown

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
3. **Rebuild**: trail comes from the log stream; focus / next come from the latest log's note.
4. **Speak**: open with your own phrasing — don't parrot the previous "下一步" verbatim.

If the gap between two consecutive log entries' `at` is > 24h, treat it implicitly as a new resumption — no session boundary field needed.

### When to refine (not every turn)

Every turn writes a log; only turns where the **core proposition** of `refined` shifts also call `refine`.

- Picture sharpens after several turns → agent proposes "I'd update refined to X — sound right?" → user agrees → `refine`.
- A pivotal moment ("the real essence isn't A, it's B") → propose refine immediately.

**log vs refine boundary**: log is the per-turn process trace; refine is the periodic phrasing update.

### Closing out

dao does not have a status machine, so no `set-status` step. When the discussion has done its work:

- Final `refine` writes the terminal phrasing (if it has shifted)
- Optional: a closing log note "结论:X;为什么:Y"

### What not to do

- Don't auto-promote dao realizations into `idea` or `todo` (user decides)
- Don't invent thread / session / conversation concepts between log entries
- Don't push focus / next into structured fields inside log elements (`{at, note}` stays simple)
- Don't decide for the user — focus / next are agent suggestions; refine needs user assent
````

- [ ] **Step 3: Add a `log` line to the Examples section**

In `skills/dao/SKILL.md`, find the Examples block (around lines 38-42):

```bash
python skills/dao/scripts/dao.py add "好脚手架是替你说不的人,不是替你说是的人"
python skills/dao/scripts/dao.py list --tag 系统设计 --tsv
python skills/dao/scripts/dao.py refine 2026-05-19-1c2f "好的脚手架替你说不"
```

Add a `log` line after the `refine` line so the block becomes:

```bash
python skills/dao/scripts/dao.py add "好脚手架是替你说不的人,不是替你说是的人"
python skills/dao/scripts/dao.py list --tag 系统设计 --tsv
python skills/dao/scripts/dao.py refine 2026-05-19-1c2f "好的脚手架替你说不"
python skills/dao/scripts/dao.py log 2026-05-19-1c2f "本轮:边界澄清\n焦点:反例搜索\n下一步:列举 3 个不像脚手架的工具检验"
```

- [ ] **Step 4: Verify edits**

Run:
```bash
grep -n "^- \`log " skills/dao/SKILL.md
grep -n "## Discussion protocol" skills/dao/SKILL.md
grep -n "log 2026-05-19-1c2f" skills/dao/SKILL.md
```
Expected: each finds at least one match.

- [ ] **Step 5: Commit**

```bash
git add skills/dao/SKILL.md
git commit -m "$(cat <<'EOF'
docs(dao): discussion protocol section

Mirrors the idea protocol with a dao-specific opening framing
(meaning-tracing / boundary-clarification rather than actionable
plan), and replaces the closing-out section with one that drops
set-status (dao has no status machine).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Full suite + smoke test (no commit)

**Files:** none modified.

- [ ] **Step 1: Run the full pytest suite**

Run:
```bash
make test
```
Expected: all tests pass (existing todo / tip / etc. unaffected; idea + dao have 5 + 5 new log tests + extended add tests all green).

If any test fails, fix the underlying issue and re-run before continuing.

- [ ] **Step 2: Manual smoke test — one full discussion cycle**

Run each command in order. Substitute `<ID>` with the id printed by the previous `add` or `refine`.

```bash
# 1. capture
make idea ARGS="add '用 JSONL 替代 Markdown 做事实源' --tag smoke --status incubating"

# Note the id from output (looks like 2026-05-19-XXXX)

# 2. first refined (agent proposes; user accepts)
make idea ARGS="refine <ID> '数据是核心,工具附着'"

# 3. three discussion turns
# (single-line notes to keep shell quoting simple; real agent usage may
# include newlines via a Python wrapper, which is what tests exercise.)
make idea ARGS="log <ID> '本轮:澄清目标用户;焦点:替代方案;下一步:问现在怎么解决'"
make idea ARGS="log <ID> '本轮:替代方案;[决定] 关键差距:零散 markdown 难检索;焦点:JSONL 是否够'"
make idea ARGS="log <ID> '本轮:收尾;[决定] 方向锁定:JSONL + 单一事实源;下一步:进入实施'"

# 4. read-back: list and confirm log[] contains 3 entries in order
make idea ARGS="list"
```

Expected: the `list` output's record contains a `"log"` array with three entries, each with `"at"` and `"note"` fields, ordered by `at`. Reading the three notes in order should let you reconstruct the discussion arc without ambiguity.

- [ ] **Step 3: Clean up the smoke test record**

The smoke test wrote to `~/aha/idea.jsonl`. If you want it gone:

```bash
# Inspect first to be safe
grep "smoke" ~/aha/idea.jsonl

# If only the smoke record matched and you want it removed, delete that line manually with your editor; do NOT bulk-delete the file (other real records may be there).
```

If you'd rather keep the smoke record as a real example, leave it.

- [ ] **Step 4: Confirm the spec's verification checklist is fully green**

Open `docs/superpowers/specs/2026-05-19-idea-dao-discussion-design.md` §6.2 and tick each box:
- [ ] `make test` 全绿 (Task 6 Step 1)
- [ ] AGENTS.md §5 / §6.3 修订 (Task 1)
- [ ] `skills/idea/SKILL.md` Verbs + Discussion protocol + Examples (Task 4)
- [ ] `skills/dao/SKILL.md` Verbs + Discussion protocol + Examples (Task 5)
- [ ] `skills/idea/scripts/idea.py` + `skills/dao/scripts/dao.py` log subparsers (Task 2 + 3)
- [ ] Spec committed (already done at `ae31478`)
- [ ] Manual smoke test passed (Task 6 Step 2)

---

## Notes for the executor

- **TDD discipline**: don't skip the "run failing tests" step. Seeing the test fail confirms the test is exercising the right surface; if it doesn't fail, the test is broken before the implementation has a chance.
- **One commit per task**: Tasks 1-5 each produce exactly one commit. Task 6 is verification only.
- **No `--no-verify`**: per AGENTS.md §8. If a hook fails, fix it and create a new commit.
- **No `git add -A` / `git add .`**: stage files explicitly (see each Step 5 commit block).
- **idea / dao mirror by design**: if you find yourself diverging the two CLIs (different log help text, different validation), pause and check whether the divergence is intentional. The protocol divergence (idea vs dao SKILL.md framing) is intentional; CLI divergence is not.
