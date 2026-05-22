# Insight Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 aha-skills 仓库新增 `insight` skill —— 捕捉用户对外部现象的解读、agent 在 chat 给视角并征得同意后落档。

**Architecture:** 沿用项目既有「Markdown 单一事实源 + Agent 直接 Read/Edit/Write」模式，无 CLI、无新依赖、无测试框架。新增一个 `skills/insight/SKILL.md`（描述 trigger / 文件结构 / workflow），并在 `README.md` 四处同步登记新 skill。

**Tech Stack:** Markdown only. 验证靠 `grep` 检查关键 section 是否齐备 + 对照 spec 验收清单逐条 review。

**Spec:** `docs/superpowers/specs/2026-05-22-insight-skill-design.md`

---

## File Structure

- **Create:** `skills/insight/SKILL.md` — 单文件，定义 insight skill 的 trigger、storage、markdown shape、workflow、red flags、output style
- **Modify:** `README.md` — 四个区块同步：设计哲学列表 / 该用哪个 skill 表格 + 判定规则 / 仓库结构代码块 / 数据存储代码块

---

## Task 1: 创建 `skills/insight/SKILL.md`

**Files:**
- Create: `skills/insight/SKILL.md`

- [ ] **Step 1: 创建 SKILL.md 写入完整内容**

用 Write 工具写入以下完整内容到 `skills/insight/SKILL.md`：

````markdown
---
name: insight
description: 当用户显式触发 /insight、说「记录一个洞察」「记录一个观察」、要求展开探讨已有 insight、或翻阅过往 insight 时使用。区别于 dao（向内顿悟）、idea（向外行动）、tip（实践捷径）、todo（带 deadline 任务）。判定规则——解读对象是外部现象 → insight；解读对象是自己/价值观 → dao。**不要**因为「我对 X 的看法是…」「为什么 X 总是…」「你怎么看 X」等日常发言自动触发。
---

# Insight — 对外部现象的解读沉淀场

捕捉用户对**外部现象**的解读为 Markdown，agent 在 chat 给自己的视角并征得同意后落档，可选地通过多轮深谈展开，并定期翻出旧 insight 回顾。

## Triggers（显式触发，不要宽泛语义）

- 中文：「记录一个洞察」「记录一个观察」「记下来这个洞察」「翻翻以前的 insight」「展开聊聊这个 insight」
- English: "record an insight", "log this observation", "look back at past insights"
- Slash: `/insight`

**不**触发：「我对 X 的看法是…」「为什么 X 总是…」「你怎么看 X」等日常发言。Agent 也**不**主动建议「要不要存成 insight」——除非用户已经表达了记录意图。

## Storage

```
~/aha-data/insight/
└── insight-YYYYMMDD-HHMMSS-<slug>.md
```

每条 insight 一个文件。首次写入时 Agent 用 `mkdir -p ~/aha-data/insight` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: insight-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

insight 没有 status——没有生命周期状态。

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话——洞察/解读本身，永不被覆盖>

## Context
<可选：观察到的现象 / 触发情境>

## Agent Takes
### YYYY-MM-DD — <角度小标题>
<agent 在 chat 口述、用户同意保存后落入的视角，1-3 句>

### YYYY-MM-DD — <下一个角度>
...

## Discussions
### YYYY-MM-DD — <topic>
<多轮探讨摘要 + 1-3 句 takeaway>
```

### 示例文件

```markdown
---
id: insight-20260522-103045-team-ai-rush
created_at: 2026-05-22T10:30:45+08:00
updated_at: 2026-05-22T10:35:12+08:00
---

# 团队卷 AI 是身份焦虑而非生产力需求

## Raw
我觉得团队最近都在卷 AI 工具，本质不是生产力需求，是身份焦虑——大家怕"不会用 AI"会被贴上落伍标签。

## Context
周会上一半时间在比谁用了什么新工具，但实际产出并没变。

## Agent Takes
### 2026-05-22 — 信号 vs 实质
表演性使用是组织里的常见信号——重要的是被看到在用，而不是用得是否有效。这种动力下，工具选型会偏向"显眼"而非"合用"。

## Discussions
```

## Workflow

### 捕捉

1. 用户**显式**触发（见 Triggers）
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从 Raw 概括 1-3 个英文小写单词作 slug
3. Agent 用 `mkdir -p ~/aha-data/insight` 后用 Write 创建 `~/aha-data/insight/insight-<TS>-<slug>.md`，把原话原样写进 `## Raw`
4. 如果触发情境/被解读现象在原话之外被提到，填 `## Context`
5. **不自动起草 Summary**（结构里没有这个 section）
6. Agent 在 chat 给 1-2 个自己的视角，**问一句**：「要把这个视角存进去吗？」

### 保存 Agent Take

当用户口头肯定（「存」「保存」「记下来」「不错」「都存」等）：
1. Agent 在 `## Agent Takes` 追加 `### YYYY-MM-DD — <角度小标题>` + 1-3 句视角
2. 更新 frontmatter `updated_at`

如果用户没回应或说「先放着」「不用」：**什么都不做**，视角留在 chat 里。

### 深谈

当用户主动展开（「展开聊聊」「再谈谈」）：
1. 先在 chat 进行多轮对话
2. 结束时总结 1-3 句 **takeaway**
3. 在 `## Discussions` 追加 `### YYYY-MM-DD — <topic>` + takeaway + 要点
4. 更新 `updated_at`

**没有 takeaway 的 discuss 是 context leak。**

### 翻旧

当用户说「翻翻以前的 insight」：
- Agent 用 `ls ~/aha-data/insight/` 或 `grep` 找到记录
- 选一条，读出 Raw + 最新 Agent Take
- 提供选项：「再谈谈？加新视角？还是放着。」
- 一次只处理一条——回顾是慢的

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "用户说的像洞察，我顺手存一下" | 必须用户**显式**说「记录」/`/insight`。日常发言不建文件 |
| "原话有口语/错字，帮他清理一下" | 永远不动 `## Raw` |
| "agent take 写得不错，先存了用户应该不介意" | 必须用户口头同意才能 append 到 `## Agent Takes` |
| "discuss 完直接告诉用户结论" | 必须有 takeaway 并 append 到 `## Discussions`。无 takeaway = context leak |
| "用户说的其实是 dao（人生顿悟）我顺手归 insight" | 提示「听起来更像 dao，要换吗？」。不跨 skill |
| "Raw 太散，提炼一版 Summary" | 结构里没有 Summary。要更紧凑就在 chat 里说，不写文件 |

## Output Style

每次操作后告诉用户：

- 文件路径
- 一句话：发生了什么变更
- 至多一个具体的下一步建议

Markdown 文件是唯一事实源。
````

- [ ] **Step 2: 校验关键 section 都齐备**

Run:
```bash
cd /Users/chending.cd/workspace/github/self/aha-skills
grep -c '^## ' skills/insight/SKILL.md
grep -E '^(## Triggers|## Storage|## Markdown Shape|## Workflow|## Red Flags|## Output Style)$' skills/insight/SKILL.md
```

Expected: 第一条 `grep -c` 返回 `>= 6`；第二条 grep 列出全部六个 section 标题。

- [ ] **Step 3: Commit**

```bash
cd /Users/chending.cd/workspace/github/self/aha-skills
git add skills/insight/SKILL.md
git commit -m "$(cat <<'EOF'
feat: add insight skill

Captures user's interpretation of external phenomena. Agent offers
its own takes in chat and only appends to file on explicit consent.
Triggers are narrow ("记录一个洞察"/`/insight`) — no auto-capture
from casual remarks.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 同步更新 `README.md`

**Files:**
- Modify: `README.md`（四处区块同步）

- [ ] **Step 1: 更新「设计哲学」列表加入 insight**

用 Edit 把 `README.md` 中的：

```
- **idea** — 从灵光一闪的创意想法，到执行落地的实际项目，向外的行动直觉：捕捉 → 孵化 → 决策成行
- **dao** — "道"、"感悟"、"方法论"、"认知"，向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- **tip** — "小妙招"、"小技巧"、"邪修方法"，行动上总结的捷径，高效的方法：记录 → 复用 → 如有可能泛化推广
- **todo** — 从待办事项，到时候复盘提升，维持节奏：任务（带 due / 状态 / 推迟记录）
```

替换为：

```
- **idea** — 从灵光一闪的创意想法，到执行落地的实际项目，向外的行动直觉：捕捉 → 孵化 → 决策成行
- **dao** — "道"、"感悟"、"方法论"、"认知"，向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- **insight** — 对外部现象的解读：记下解读 → agent 给视角 → 必要时深谈
- **tip** — "小妙招"、"小技巧"、"邪修方法"，行动上总结的捷径，高效的方法：记录 → 复用 → 如有可能泛化推广
- **todo** — 从待办事项，到时候复盘提升，维持节奏：任务（带 due / 状态 / 推迟记录）
```

- [ ] **Step 2: 更新「该用哪个 skill」表格 + 判定规则**

用 Edit 把：

```
| 用户在说 | 用哪个 skill |
|---|---|
| 一个外部行动方向，需要孵化、研究、决策 / "我有个想法" | `idea` |
| 一个内省式领悟、一句话顿悟 / "我悟到了" | `dao` |
| 一个绑定实践域的高效方法 / "小妙招" / "这招好用" | `tip` |
| 有 deadline 的待办 / "今天要做" / "推迟到" / "完成了" | `todo` |

**tip vs dao 判定**：能不能剥离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。
```

替换为：

```
| 用户在说 | 用哪个 skill |
|---|---|
| 一个外部行动方向，需要孵化、研究、决策 / "我有个想法" | `idea` |
| 一个内省式领悟、一句话顿悟 / "我悟到了" | `dao` |
| 对外部现象的解读 / "记录一个洞察" / "记录一个观察" | `insight` |
| 一个绑定实践域的高效方法 / "小妙招" / "这招好用" | `tip` |
| 有 deadline 的待办 / "今天要做" / "推迟到" / "完成了" | `todo` |

**tip vs dao 判定**：能不能剥离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。

**insight vs dao 判定**：解读对象是**外部现象** → `insight`；解读对象是**自己/价值观** → `dao`。
```

- [ ] **Step 3: 更新「仓库结构」代码块**

用 Edit 把：

```
aha-skills/
├── README.md
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── tip/SKILL.md
    └── todo/SKILL.md
```

替换为：

```
aha-skills/
├── README.md
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── insight/SKILL.md
    ├── tip/SKILL.md
    └── todo/SKILL.md
```

- [ ] **Step 4: 更新「数据存储」代码块**

用 Edit 把：

```
~/aha-data/
├── idea/   idea-YYYYMMDD-HHMMSS-<slug>.md
├── dao/    dao-YYYYMMDD-HHMMSS-<slug>.md
├── tip/    tip-YYYYMMDD-HHMMSS-<slug>.md
└── todo/   todo-YYYYMMDD-HHMMSS-<slug>.md
```

替换为：

```
~/aha-data/
├── idea/    idea-YYYYMMDD-HHMMSS-<slug>.md
├── dao/     dao-YYYYMMDD-HHMMSS-<slug>.md
├── insight/ insight-YYYYMMDD-HHMMSS-<slug>.md
├── tip/     tip-YYYYMMDD-HHMMSS-<slug>.md
└── todo/    todo-YYYYMMDD-HHMMSS-<slug>.md
```

注意：列宽对齐——把 `idea/` `dao/` `tip/` `todo/` 后面的空格调整为 4 个、5 个、5 个、4 个，新加 `insight/` 后跟 1 个空格，使三列对齐。

- [ ] **Step 5: 校验四处都已更新**

Run:
```bash
cd /Users/chending.cd/workspace/github/self/aha-skills
grep -c 'insight' README.md
```

Expected: `>= 5`（哲学段 1 处 + 表格 1 处 + 判定规则 1 处 + 仓库结构 1 处 + 数据存储 1 处）。

进一步逐项确认：
```bash
grep -E '\*\*insight\*\* —' README.md   # 哲学段
grep -E '\| .* \| `insight` \|' README.md   # 表格行
grep -E 'insight vs dao 判定' README.md   # 判定规则段
grep -E 'insight/SKILL\.md' README.md   # 仓库结构
grep -E 'insight/ +insight-YYYYMMDD' README.md   # 数据存储
```

Expected: 五条 grep 都各匹配到至少 1 行。

- [ ] **Step 6: Commit**

```bash
cd /Users/chending.cd/workspace/github/self/aha-skills
git add README.md
git commit -m "$(cat <<'EOF'
docs: register insight skill in README

Add insight to 设计哲学 list, 该用哪个 skill table (with
insight-vs-dao decision rule), 仓库结构 tree, and 数据存储 tree.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 验收 — 对照 Spec 7 条 acceptance criteria 走查

**Files:** read-only walkthrough

> 这个 skill 没有自动化测试 framework；验收靠对照 spec 的 7 条 acceptance criteria 逐条 mental walk-through SKILL.md，验证文档**描述了**符合预期的行为。这一步不改文件，只是确认 SKILL.md 自洽。

- [ ] **Step 1: 验收 #1 — 显式触发建文件 + chat 给视角**

打开 `skills/insight/SKILL.md`，找到 `## Workflow` → `### 捕捉` 6 步：
- 第 1 步明确「显式触发」
- 第 3 步包含 `mkdir -p ~/aha-data/insight` 和 Write
- 第 6 步包含「问一句：要把这个视角存进去吗？」

确认这三条都在文件里。

- [ ] **Step 2: 验收 #2 — 用户说「存」→ append Agent Takes**

`### 保存 Agent Take` 段：
- 列出肯定信号
- 描述 append `### YYYY-MM-DD — <角度小标题>` 到 `## Agent Takes`
- 描述更新 `updated_at`

确认。

- [ ] **Step 3: 验收 #3 — 无显式记录意图 → 不建文件**

`## Triggers` 段最后一行明确列出**不**触发的语句类型（「我对 X 的看法是…」等），且 Red Flags 第一行重申。确认。

- [ ] **Step 4: 验收 #4 — Raw 不可变**

Red Flags 表格第二行：「永远不动 `## Raw`」。确认。

- [ ] **Step 5: 验收 #5 — 深谈产出 takeaway append Discussions**

`### 深谈` 段四步明确 takeaway + append + `没有 takeaway 的 discuss 是 context leak`。确认。

- [ ] **Step 6: 验收 #6 — 用户说人生顿悟 → 提示换 dao**

Red Flags 表格倒数第二行：「提示『听起来更像 dao，要换吗？』。不跨 skill」。确认。

- [ ] **Step 7: 验收 #7 — README 三处都更新**

打开 `README.md`，肉眼检查：
- 设计哲学列表有 5 个 skill
- 该用哪个 skill 表格有 5 行 + 两条判定规则（tip vs dao、insight vs dao）
- 仓库结构 tree 有 5 个 SKILL.md
- 数据存储 tree 有 5 个目录

确认。

- [ ] **Step 8: 不创建 commit**

本任务为只读 walk-through。如果上述任何一步发现文档与 spec 不匹配，回到 Task 1 或 Task 2 修订；如果全部通过，本 plan 实现完成。

---

## Out of Scope（明确不做的事）

下列项**不在本 plan 范围内**，避免 scope creep：

- 修改 `README.md` 的「设计公约」第 2 条措辞（公约第 2 句提到「提炼写在 `## Summary`」，与 insight 的「无 Summary」结构形式上不一致；但精神上对齐——Raw 不可改、修订不丢历史。如果未来想统一措辞，单独开 plan）
- 新增 CLI / 校验脚本（沿用 idea/dao 的 agent-direct-IO 模式）
- 自动化测试 / lint
- 其他 skill 的 SKILL.md 调整
