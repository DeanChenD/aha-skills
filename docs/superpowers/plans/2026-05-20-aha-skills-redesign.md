# aha-skills Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely replace the current aha-skills implementation (Python CLIs, _lib, tests, scripts) with 4 minimal SKILL.md files that let the Agent read/write Markdown directly, plus a rewritten README.

**Architecture:** Each skill is a single `SKILL.md` file (no scripts, no tests, no references subdirectories). Agent uses built-in tools (Read/Edit/Write/Bash) to manipulate `~/aha-data/<skill>/` Markdown files. No shared library, no CLI boundary, no atomic-write infrastructure.

**Tech Stack:** Pure Markdown + YAML frontmatter. Agent tools only.

---

## File Structure

After implementation, the repo looks like:

```
aha-skills/
├── README.md
├── docs/superpowers/specs/2026-05-20-aha-skills-redesign.md
├── docs/superpowers/plans/2026-05-20-aha-skills-redesign.md
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── tip/SKILL.md
    └── todo/SKILL.md
```

Files/directories to **remove**:
- `skills/_lib/` (shared Python library)
- `skills/idea/scripts/`, `skills/idea/tests/`, `skills/idea/references/`
- `skills/dao/scripts/`, `skills/dao/tests/`, `skills/dao/references/`
- `skills/daily/` (entire directory — replaced by `tip/` + `todo/`)
- `skills/reflect/` (entire directory — dropped)
- `scripts/` (test runner)
- `Makefile`
- `README.en.md`

Files to **create**:
- `skills/idea/SKILL.md` (new content)
- `skills/dao/SKILL.md` (new content)
- `skills/tip/SKILL.md` (new content)
- `skills/todo/SKILL.md` (new content)
- `README.md` (rewritten)

---

### Task 1: Remove old implementation

**Files:**
- Remove: `skills/_lib/` (entire directory)
- Remove: `skills/idea/scripts/`, `skills/idea/tests/`, `skills/idea/references/`
- Remove: `skills/dao/scripts/`, `skills/dao/tests/`, `skills/dao/references/`
- Remove: `skills/daily/` (entire directory)
- Remove: `skills/reflect/` (entire directory)
- Remove: `scripts/` (entire directory)
- Remove: `Makefile`
- Remove: `README.en.md`

- [ ] **Step 1: Remove all old Python/test/script infrastructure**

```bash
rm -rf skills/_lib
rm -rf skills/idea/scripts skills/idea/tests skills/idea/references
rm -rf skills/dao/scripts skills/dao/tests skills/dao/references
rm -rf skills/daily
rm -rf skills/reflect
rm -rf scripts
rm -f Makefile
rm -f README.en.md
```

- [ ] **Step 2: Remove old SKILL.md files (will be replaced with new content)**

```bash
rm -f skills/idea/SKILL.md
rm -f skills/dao/SKILL.md
```

- [ ] **Step 3: Verify clean state**

Run: `find skills/ -type f`
Expected: only `skills/tip/` and `skills/todo/` directories exist (both empty).

Run: `ls Makefile README.en.md scripts/ 2>&1`
Expected: all "No such file or directory"

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove old implementation (Python CLIs, _lib, tests, scripts, daily, reflect)

Prepares for rewrite per docs/superpowers/specs/2026-05-20-aha-skills-redesign.md.
Old skills (idea/dao with scripts, daily, reflect) and shared infrastructure
(_lib/aha_md.py, Makefile, scripts/run_tests.py, README.en.md) are no longer needed.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Create `skills/idea/SKILL.md`

**Files:**
- Create: `skills/idea/SKILL.md`

- [ ] **Step 1: Write `skills/idea/SKILL.md`**

```markdown
---
name: idea
description: 当用户触发 /idea、提出一个向外的行动想法（需要孵化才能落地的方向）、或要求维护 idea inbox / 继续 / 终止某个想法时使用。区别于 dao（向内领悟）、tip（已验证的实践域捷径）、todo（带 deadline 的具体任务）。
---

# Idea — 行动想法的孵化器

把灵光一闪的想法变为持久的 Markdown 记录，推动它走过轻量孵化循环：捕捉 → 研究 → 规划 → 决策。

## Triggers（示例，非穷举）

- 中文：「我有个想法」「想到一个」「记一下这个点子」「灵光一闪」「帮我看看这个 idea」「有什么 idea 还没处理」「这个先放着孵化」「pause 一下」「kill 那个」「idea inbox」
- English: "I have an idea", "let me park this", "what's in my idea inbox", "kill that one", "let's incubate this"
- Slash: `/idea`

## Storage

```
~/aha-data/idea/
└── idea-YYYYMMDD-HHMMSS-<slug>.md
```

每个想法一个文件。首次写入时若目录不存在，Agent 用 `mkdir -p ~/aha-data/idea` 创建。

## Markdown Shape

### Frontmatter

```yaml
---
id: idea-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
status: inbox | researching | planning | completed | paused | killed
---
```

状态语义（软状态——Agent 提议，用户决定）：
- `inbox`：仅记录，未开始处理
- `researching`：需要进一步探索 / 验证
- `planning`：信息够了，可以形成具体 plan
- `completed`：已经产出可执行的方案 / artifact
- `paused`：明确暂时挂起
- `killed`：明确放弃（原因记在 Decision Log）

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话，永不被覆盖>

## Summary
<最新提炼版；首次 capture 后 Agent 立刻起草一版>

## Plan
- [ ] <下一步行动>
- [ ] ...

## Question
- [ ] <澄清类问题、启发式问题>
- [ ] ...

## Decision Log
- YYYY-MM-DD: Captured.

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary，修订时归档到此>
```

### 示例文件

```markdown
---
id: idea-20260520-143000-cli-bookmarks
created_at: 2026-05-20T14:30:00+08:00
updated_at: 2026-05-20T14:30:00+08:00
status: inbox
---

# 命令行书签管理器

## Raw
想做一个命令行的书签管理器，可以给目录打标签然后快速跳转

## Summary
一个 CLI 工具：给目录打标签，然后用标签名快速跳转——类似 `z` 但是用户主动定义标签。

## Plan
- [ ] 调研现有工具（z, autojump, zoxide）的不足
- [ ] 定义 MVP：tag add / remove / jump

## Question
- [ ] 是集成到 shell cd 里，还是做独立二进制？
- [ ] 只管目录，还是也管文件/URL？

## Decision Log
- 2026-05-20: Captured.

## Summary Log
```

## Workflow

1. 用户说"我有个灵感 X"
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从 X 概括 1-3 个英文小写单词作为 slug
3. Agent 用 Write 创建 `~/aha-data/idea/idea-<TS>-<slug>.md`，把 X 原样写进 `## Raw`，frontmatter `status: inbox`
4. Agent 立即起草 `## Summary`（比 Raw 更紧凑，不加新主张）、`## Plan`（具体下一步）、`## Question`（澄清/启发式问题）
5. 写一条 `## Decision Log`：`- YYYY-MM-DD: Captured.`
6. 给用户一个具体选择：「设为 researching 并推 plan？先 inbox 放着？还是直接 kill？」
7. 用户回答后：Agent 用 Edit 改 frontmatter `status` + `updated_at`，并在 Decision Log 追加一行

**修订 Summary**：覆盖前，先把当前内容追加到 `## Summary Log`（格式：`- YYYY-MM-DD (vN): <旧内容>`），再写新版本。

**跨源查询**：Agent 临场用 Bash：
```bash
ls ~/aha-data/idea/idea-2026-05*.md
grep -l 'status: researching' ~/aha-data/idea/*.md
```

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "原话不通顺，帮他润色一下 Raw" | 不要动 `## Raw`。改 `## Summary`，旧 Summary 进 `## Summary Log` |
| "用户没回答 paused 的提议，那就当 paused 吧" | 不要替用户做 paused/killed 决定 |
| "stale 5 天了我顺手 kill 了" | 不要 auto-kill。明确提议 + 等用户确认 |
| "我问个开放问题让他想想" | 不问"你想做什么"。给具体选项（continue / answer / pause / kill） |

## Output Style

每次操作后告诉用户：

- 文件路径
- 一句话：发生了什么变更
- 至多一个具体的下一步建议

Markdown 文件是唯一事实源。
```

- [ ] **Step 2: Verify the file exists and is well-formed**

Run: `head -5 skills/idea/SKILL.md`
Expected: YAML frontmatter starting with `---`

- [ ] **Step 3: Commit**

```bash
git add skills/idea/SKILL.md
git commit -m "feat: add idea SKILL.md (v0 rewrite)

Minimal skill definition — no scripts, no tests. Agent uses Read/Edit/Write
to manage ~/aha-data/idea/*.md directly.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Create `skills/dao/SKILL.md`

**Files:**
- Create: `skills/dao/SKILL.md`

- [ ] **Step 1: Write `skills/dao/SKILL.md`**

```markdown
---
name: dao
description: 当用户触发 /dao、分享一个向内的领悟或感悟（想沉淀而非行动的认知）、要求提炼已有感悟、或要求展开哲学探讨时使用。区别于 idea（向外行动）、tip（绑定实践域的捷径）、todo（带 deadline 的任务）。判定规则——能不能脱离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。
---

# Dao — 向内顿悟的提炼场

捕捉个人感悟（"道"）为 Markdown，将它们打磨为提炼版本，可选地通过多轮深谈探索，并定期翻出旧感悟回顾。

## Triggers（示例，非穷举）

- 中文：「我悟到了」「想通了」「感悟到」「想明白了」「再帮我提炼一下」「重新整理一下」「展开聊聊」「和我探讨一下」「翻翻以前的感悟」「回顾一下感悟」
- English: "I just realized", "I had an insight", "refine this further", "let's discuss this more deeply", "look back at past insights"
- Slash: `/dao`

## Storage

```
~/aha-data/dao/
└── dao-YYYYMMDD-HHMMSS-<slug>.md
```

每条感悟一个文件。探讨内容 inline 在同一个文件里（不再有单独的 sessions/ 目录）。首次写入时 Agent 用 `mkdir -p ~/aha-data/dao` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: dao-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

dao 没有 status 字段——没有生命周期状态。

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话，永不被覆盖>

## Summary
<最新提炼版；首次 capture 后 Agent 立刻起草一版>

## Context
<可选：触发情境——什么时候 / 为什么想到这个>

## Discussions
### YYYY-MM-DD — <topic>
<多轮探讨摘要 + 1-3 句 takeaway>

### YYYY-MM-DD — <另一个 topic>
...

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary，修订时归档到此>
```

### 示例文件

```markdown
---
id: dao-20260520-091500-fear-compass
created_at: 2026-05-20T09:15:00+08:00
updated_at: 2026-05-20T09:15:00+08:00
---

# 恐惧是指南针，不是停止线

## Raw
恐惧是指南针，不是停止线。每次我害怕一件事，回头看其实都是在告诉我该往那个方向走。

## Summary
恐惧可靠地指向成长的边缘。当我注意到恐惧时，应该把它解读为方向信号——而非停下来的理由。

## Context
在反思为什么一直回避和经理聊转岗的事。

## Discussions

## Summary Log
```

## Workflow

### 捕捉

1. 用户说"我悟到了 X"或等价表达
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从 X 概括 1-3 个英文小写单词作为 slug
3. Agent 用 Write 创建 `~/aha-data/dao/dao-<TS>-<slug>.md`，把 X 原样写进 `## Raw`
4. **除非用户明确说"先放着"**：Agent 立刻起草 `## Summary`——比 Raw 更紧凑、更清晰，不说教、不加新主张
5. 如果用户提到了触发情境，填 `## Context`
6. 如果话题偏哲学且用户看起来开放：提议一个具体角度展开（不自动开始）

### 提炼

当用户说"再帮我提炼一下" / "重新整理一下"：
1. Agent 把当前 `## Summary` 内容追加到 `## Summary Log`：`- YYYY-MM-DD (vN): <旧内容>`
2. Agent 用新版本覆盖 `## Summary`
3. 更新 frontmatter `updated_at`

### 深谈

当用户想深入探讨（"展开聊聊"、"和我探讨一下"）：
1. 先在聊天里进行多轮对话
2. 对话结束时，总结 1-3 句 **takeaway**
3. 在 `## Discussions` 追加 `### YYYY-MM-DD — <topic>`，写入 takeaway + 对话要点
4. 如果探讨实质改变了感悟本身，同时触发一次 Summary 修订（旧版 → Summary Log）
5. 更新 `updated_at`

**没有 takeaway 的 discuss 是 context leak。**

### 翻旧

当用户说"翻翻以前的感悟"：
- Agent 用 `ls ~/aha-data/dao/` 或 `grep` 找到记录
- 选一条，读出 `## Summary`，提供选项："要重新提炼？深谈？加个注？还是就放着。"
- 一次只处理一条——回顾是慢的

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "原话有错字 / 口语，帮他改一下" | 永远不动 `## Raw`。改 `## Summary` |
| "discuss 完直接告诉用户结论" | discuss 必须有 takeaway 并 append 到 `## Discussions`。无 takeaway = context leak |
| "重新 refine 一版直接覆盖旧的" | 旧版本必须存到 `## Summary Log`。永不丢历史 |
| "用户说的像 tip，我顺手归到 dao" | 能不能脱离实践域说出来？不能 → tip。不要跨 skill |

## Output Style

每次操作后告诉用户：

- 文件路径
- 一句话：发生了什么变更
- 至多一个具体的下一步建议

Markdown 文件是唯一事实源。
```

- [ ] **Step 2: Verify the file**

Run: `head -5 skills/dao/SKILL.md`
Expected: YAML frontmatter starting with `---`

- [ ] **Step 3: Commit**

```bash
git add skills/dao/SKILL.md
git commit -m "feat: add dao SKILL.md (v0 rewrite)

Minimal skill definition — discussions inline in main file, no separate
sessions directory. Agent manages ~/aha-data/dao/*.md directly.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Create `skills/tip/SKILL.md`

**Files:**
- Create: `skills/tip/SKILL.md`

- [ ] **Step 1: Write `skills/tip/SKILL.md`**

```markdown
---
name: tip
description: 当用户触发 /tip、分享一个绑定特定实践域的高效方法或捷径时使用。区别于 dao（脱离实践域仍成立的向内领悟）——判定规则：能不能剥离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。区别于 idea（未验证的探索方向）和 todo（带 deadline 的任务）。
---

# Tip — 实践域里的捷径合集

记录已验证的高效方法（"小妙招" / "小技巧" / "邪修方法"），绑定特定实践域。每条 tip 一个文件，实践域在 Summary 开头锚定。

## Triggers（示例，非穷举）

- 中文：「小妙招」「小技巧」「邪修」「我发现一个高效做法」「快捷」「省时间」「这招好用」「记一下这个方法」
- English: "pro tip", "shortcut", "trick I found", "efficient way to", "hack for"
- Slash: `/tip`

### 路由判定：tip vs dao

> 能不能剥离任何具体实践/工具/域，还能完整说出来？
> - **能**（"答应别人前先睡一觉"、"恐惧是指南针"）→ **dao**
> - **不能**（必须说"调试时…" / "写 spec 时…" / "用 X 工具…"才有意义）→ **tip**

例子：
- "卡 30 分钟以上的 bug，先去散步" → **tip**（绑定调试域）
- "PR review 长 PR 时先看 test 改了什么" → **tip**（绑定代码评审域）
- "答应别人前先睡一觉" → **dao**（关于自我与承诺，无实践域）

## Storage

```
~/aha-data/tip/
└── tip-YYYYMMDD-HHMMSS-<slug>.md
```

每条 tip 一个文件。首次写入时 Agent 用 `mkdir -p ~/aha-data/tip` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: tip-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

没有 status、没有 tags、没有 domain 字段——domain 在 Summary 正文开头锚定。

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话，永不被覆盖>

## Summary
<最新提炼版；开头必须锚定实践域>

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary，修订时归档到此>
```

### 示例文件

```markdown
---
id: tip-20260520-160000-pr-review-tests-first
created_at: 2026-05-20T16:00:00+08:00
updated_at: 2026-05-20T16:00:00+08:00
---

# Review 长 PR 时先看 test

## Raw
PR review 长 PR 时先看 test 改了什么，再看实现，效率高很多

## Summary
在代码评审场景下，面对大 PR 时：先看 test 的变更来理解意图，再看实现代码。这样能更快建立理解，也更容易发现意图与实现的不一致。

## Summary Log
```

## Workflow

1. 用户说"我发现一个高效做法：X"
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从 X 概括 1-3 个英文小写单词作为 slug
3. Agent 用 Write 创建 `~/aha-data/tip/tip-<TS>-<slug>.md`，把 X 原样写进 `## Raw`
4. Agent 立即起草 `## Summary`——**开头必须锚定实践域**（"在 X 场景下，…" / "做 Y 时，…"）
5. 完成。不主动追踪复用、不主动询问是否泛化。

**修订 Summary**（当用户说"这个 tip 是不是也适用 Y"或"上次那个 tip 还能用吗"）：
1. Agent 用 Grep/Read 找到并读取该 tip
2. 如需修订：把当前 Summary 追加到 `## Summary Log`，写新版本
3. 更新 `updated_at`

**不要**主动询问复用或泛化。只在用户提出时处理。

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "Summary 不写实践域，太啰嗦了" | Summary 开头必须锚定 domain，否则与 dao 无法区分 |
| "用户说'这个对人生也适用'，我顺手泛化成 dao" | 不要跨 skill 迁移。提议用户在 dao 里另起一条 |
| "原话啰嗦，帮他改一下 Raw" | 永远不动 Raw |

## Output Style

每次操作后告诉用户：

- 文件路径
- 一句话：发生了什么变更
- 不主动追问

Markdown 文件是唯一事实源。
```

- [ ] **Step 2: Verify the file**

Run: `head -5 skills/tip/SKILL.md`
Expected: YAML frontmatter starting with `---`

- [ ] **Step 3: Commit**

```bash
git add skills/tip/SKILL.md
git commit -m "feat: add tip SKILL.md (v0 rewrite)

New skill replacing part of old daily. Practice-bound shortcuts with
domain anchored in Summary opening. Agent manages ~/aha-data/tip/*.md.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Create `skills/todo/SKILL.md`

**Files:**
- Create: `skills/todo/SKILL.md`

- [ ] **Step 1: Write `skills/todo/SKILL.md`**

```markdown
---
name: todo
description: 当用户触发 /todo、添加任务（带或不带 deadline）、问什么 overdue 了、推迟任务（必须有理由）、标记完成/放弃、或查看待办时使用。区别于 idea（形态未定的探索，无 deadline）、dao（向内领悟）、tip（已验证的捷径）。todo 是一件具体要做的事。
---

# Todo — 带 due 的任务台账

纯任务管理。创建 → 状态流转 → 推迟（必须有理由）→ 完成或放弃。

## Triggers（示例，非穷举）

- 中文：「今天要做……」「加个待办」「明天前帮我做 X」「想推迟到……」「这件事完成了」「砍掉那个」「看看待办」「有什么 overdue」
- English: "todo: …", "add a task", "what's overdue", "postpone X to …", "done with that", "drop it", "show my tasks"
- Slash: `/todo`

## Storage

```
~/aha-data/todo/
└── todo-YYYYMMDD-HHMMSS-<slug>.md
```

每个任务一个文件。首次写入时 Agent 用 `mkdir -p ~/aha-data/todo` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: todo-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
status: pending | in_progress | blocked | done | dropped
due_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

状态语义（软状态——Agent 提议，用户决定）：
- `pending`：未开始
- `in_progress`：进行中
- `blocked`：被阻塞
- `done`：完成（`updated_at` 等价于完成时间）
- `dropped`：放弃（正文里写理由）

`due_at` 可选。用户只给日期时，按当天 `23:59:59+08:00` 解释。

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话，永不被覆盖>

## Description
<可选：把任务的具体要求展开>

## Postponement Log
- YYYY-MM-DD: <old due> → <new due>: <reason>
```

### 示例文件

```markdown
---
id: todo-20260520-100000-write-spec
created_at: 2026-05-20T10:00:00+08:00
updated_at: 2026-05-20T10:00:00+08:00
status: pending
due_at: 2026-05-21T23:59:59+08:00
---

# 写完 v1 重新设计文档

## Raw
明天前把 aha-skills 的重新设计文档写完

## Description
完成完整 spec：哲学、公约、约束、仓库形态、数据形态、四个 skill 的具体设计。

## Postponement Log
```

## Workflow

### 创建

1. 用户说"明天前完成 X"
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从 X 概括 1-3 个英文小写单词作为 slug
3. Agent 用 Write 创建文件：X 写进 `## Raw`，`status: pending`，从用户话语中解析 due
4. 如果任务需要展开，起草 `## Description`
5. **用户没指定 due**：问一次。他说没有就接受无 `due_at` 创建

### 推迟

1. 用户说"这个推迟到周五"
2. **Agent 必须先问理由**——绝不自动填理由
3. Agent 在 `## Postponement Log` 追加：`- YYYY-MM-DD: <old> → <new>: <reason>`
4. Agent 更新 frontmatter `due_at` + `updated_at`

### 完成 / 放弃

- 用户说"完成了"：Agent 设 `status: done`，更新 `updated_at`
- 用户说"砍掉"：Agent 设 `status: dropped`，更新 `updated_at`。如果没给理由则先问

### 检查 overdue

当用户问"什么 overdue 了"或 Agent 被要求检查：

```bash
NOW=$(date +%Y-%m-%dT%H:%M:%S+08:00)
grep -lE '^status: (pending|in_progress|blocked)' ~/aha-data/todo/*.md \
  | xargs grep -l "^due_at:" \
  | while read f; do
      due=$(grep '^due_at:' "$f" | head -1 | awk '{print $2}')
      [[ "$due" < "$NOW" ]] && echo "$f"
    done
```

一次只处理一条 overdue（oldest first）。处理完问要不要下一条。

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "overdue 了我顺手帮他延 3 天" | 永远不要 auto-postpone。先问 difficulty / 目标 due |
| "用户没说 due 我猜个明天" | 不要猜 due。明确问；他说没有就接受无 due 创建 |
| "用户写了一句感想，要不要我顺手 todo 一下" | 不要 auto-create todo。问 |
| "推迟没说理由，我替他写一个" | 不要替用户写 reason。先问 |

## Output Style

每次操作后告诉用户：

- 文件路径
- 一句话：发生了什么变更（状态 / due / 推迟）
- 至多一个具体的下一步建议

Markdown 文件是唯一事实源。
```

- [ ] **Step 2: Verify the file**

Run: `head -5 skills/todo/SKILL.md`
Expected: YAML frontmatter starting with `---`

- [ ] **Step 3: Commit**

```bash
git add skills/todo/SKILL.md
git commit -m "feat: add todo SKILL.md (v0 rewrite)

New skill replacing task management from old daily. Pure task lifecycle
with mandatory postponement reasons. Agent manages ~/aha-data/todo/*.md.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Rewrite `README.md`

**Files:**
- Modify: `README.md` (complete rewrite)

- [ ] **Step 1: Write new `README.md`**

```markdown
# aha-skills

一组轻量级 AI agent skill，用于把易逝的认知瞬间留下并持续生长。适配 Claude Code 等支持 SKILL.md 的 host。

---

## 设计哲学

`aha-skills` 不是一个工具集合，而是关于「如何把易逝的认知瞬间留下并持续生长」的分工：

- **idea** — 从灵光一闪的创意想法，到执行落地的实际项目，向外的行动直觉：捕捉 → 孵化 → 决策成行
- **dao** — "道"、"感悟"、"方法论"、"认知"，向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- **tip** — "小妙招"、"小技巧"、"邪修方法"，行动上总结的捷径，高效的方法：记录 → 复用 → 如有可能泛化推广
- **todo** — 从待办事项，到时候复盘提升，维持节奏：任务（带 due / 状态 / 推迟记录）

## 设计公约

1. **Markdown 是唯一事实源和数据源**。Agent 和人读同一份 `.md`。
2. **来自人的原始输入不可变**。`## Raw` 永远保留用户原话；提炼写在 `## Summary`，旧版进 `## Summary Log`。
3. **Agent 自行读取和编辑 `.md` 文件**。使用已有工具（Read / Edit / Write / Bash），不额外提供脚本。
4. **不强加 workflow**。Agent 适时给出状态建议，用户做决定。

## 设计约束

1. **第一性原理**：所有实现必须服务于核心目标——把易逝的认知瞬间留下并持续生长。
2. **奥卡姆剃刀**：选择能解决当前问题的最简单方案。
3. **YAGNI**：不为假设中的未来需求提前设计。
4. **数据优先于程序**：Markdown 是核心资产，程序脚本只是辅助工具。
5. **透明性优先**：人和 Agent 必须能读懂同一份数据。
6. **Agent 不越权**：Agent 可以建议、提炼、归类、关联。不得擅自覆盖 Raw、删除记录、推进状态、顺延任务。

## 该用哪个 skill

| 用户在说 | 用哪个 skill |
|---|---|
| 一个外部行动方向，需要孵化、研究、决策 / "我有个想法" | `idea` |
| 一个内省式领悟、一句话顿悟 / "我悟到了" | `dao` |
| 一个绑定实践域的高效方法 / "小妙招" / "这招好用" | `tip` |
| 有 deadline 的待办 / "今天要做" / "推迟到" / "完成了" | `todo` |

**tip vs dao 判定**：能不能剥离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。

## 仓库结构

```
aha-skills/
├── README.md
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── tip/SKILL.md
    └── todo/SKILL.md
```

## 数据存储

所有运行时数据放在 `~/aha-data/`：

```
~/aha-data/
├── idea/   idea-YYYYMMDD-HHMMSS-<slug>.md
├── dao/    dao-YYYYMMDD-HHMMSS-<slug>.md
├── tip/    tip-YYYYMMDD-HHMMSS-<slug>.md
└── todo/   todo-YYYYMMDD-HHMMSS-<slug>.md
```

绑定家目录消除了 cwd 碎片化——认知记录跨项目共享。

## 安装

把 `skills/` 目录（或其中任意子目录）链接/复制到 host 的 skill 加载路径：

- **Claude Code**：`ln -s "$(pwd)/skills/idea" ~/.claude/skills/idea`（每个 skill 独立）
- 无外部依赖，无 Python，无构建步骤
```

- [ ] **Step 2: Verify README renders correctly**

Run: `wc -l README.md`
Expected: approximately 70-80 lines

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for v0 redesign

Reflects new 4-skill structure (idea/dao/tip/todo), ~/aha-data/ storage,
and no-script philosophy. Removes all references to Python CLIs, _lib,
tests, and old skills (daily/reflect).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Final verification

**Files:** (none — read-only checks)

- [ ] **Step 1: Verify repo structure matches spec §5**

Run: `find . -type f | grep -v '.git/' | grep -v 'docs/' | sort`
Expected:
```
./README.md
./skills/dao/SKILL.md
./skills/idea/SKILL.md
./skills/tip/SKILL.md
./skills/todo/SKILL.md
```

- [ ] **Step 2: Verify no Python/test/script remnants**

Run: `find . -name '*.py' -o -name 'Makefile' -o -name '*.en.md' | grep -v '.git/'`
Expected: no output

- [ ] **Step 3: Verify each SKILL.md has required §8 sections**

Run:
```bash
for f in skills/*/SKILL.md; do
  echo "=== $f ==="
  grep -c '^## Triggers' "$f"
  grep -c '^## Storage' "$f"
  grep -c '^## Markdown Shape' "$f"
  grep -c '^## Workflow' "$f"
  grep -c '^## Red Flags' "$f"
  grep -c '^## Output Style' "$f"
done
```
Expected: each count is 1 for every file

- [ ] **Step 4: Verify .gitignore excludes aha-data**

Check if `.gitignore` contains `aha-data/`. If not, add it:

```bash
echo 'aha-data/' >> .gitignore
git add .gitignore
git commit -m "chore: add aha-data/ to .gitignore

Runtime data lives in ~/aha-data/ — never committed to repo.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Summary

| Task | What | Commit message prefix |
|------|------|-----------------------|
| 1 | Remove old implementation | `chore:` |
| 2 | Create `skills/idea/SKILL.md` | `feat:` |
| 3 | Create `skills/dao/SKILL.md` | `feat:` |
| 4 | Create `skills/tip/SKILL.md` | `feat:` |
| 5 | Create `skills/todo/SKILL.md` | `feat:` |
| 6 | Rewrite `README.md` | `docs:` |
| 7 | Final verification + .gitignore | `chore:` |

Total: 7 tasks, ~20 steps, estimated 15-25 minutes for an agentic worker.
