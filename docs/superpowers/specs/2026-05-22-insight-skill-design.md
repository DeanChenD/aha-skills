# Insight Skill — 设计文档

**日期**: 2026-05-22
**状态**: 待实现
**作者**: brainstorming session

## 背景

aha-skills 现有四个 skill：`idea`（向外行动直觉）/ `dao`（向内顿悟）/ `tip`（实践捷径）/ `todo`（带 deadline 任务）。它们都缺一类认知瞬间：**用户对外部现象的解读**——既不是要立刻行动，也不是关于自我/价值观的内省，而是想把"我是这么看 X 现象的"沉淀下来，并听 agent 给出别的视角。

新增 `insight` skill 填这个空位。

## 定位与边界

`insight` 捕捉用户对**外部现象**的**解读本身**。Raw 是用户已有的洞察（不是现象描述也不是行动方向）；agent 在 chat 给出自己的视角，征得用户同意后落入文件。

| 用户在说 | 用 |
|---|---|
| 解读外部现象 / 想听 agent 的视角 / 「记录一个洞察」 | `insight` |
| 关于人生/自我/价值观的内省顿悟 | `dao` |
| 想做的事（行动方向） | `idea` |
| 绑定具体实践域的高效方法 | `tip` |
| 带 deadline 的任务 | `todo` |

**判定规则**：解读对象是**外部现象** → `insight`；解读对象是**自己/价值观** → `dao`。

## 设计公约（沿用项目四条）

1. Markdown 单一事实源
2. 用户原文不可变（`## Raw` 永不被覆盖）
3. Agent 自行读写 `.md`（用 Read/Edit/Write/Bash），不另写脚本
4. 不强加 workflow（agent 提建议，用户做决定）

## Storage

```
~/aha-data/insight/
└── insight-YYYYMMDD-HHMMSS-<slug>.md
```

每条 insight 一个文件。首次写入时 agent 用 `mkdir -p ~/aha-data/insight` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: insight-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

`insight` 没有 status——没有生命周期状态。

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

### 关键差异（vs dao）

- **没有 `Summary` / `Summary Log`**：用户要"尽可能简单"。Raw 不可改，要更紧凑就在 chat 里说，不写文件。
- **`Agent Takes` 是 timestamped append-only 列表**：每次保存一条新视角，旧的不动；不存在"覆盖+归档旧版"的概念。
- **`Context` 可选**：如果用户原话里现象已经描述清楚，不强制再写一遍。

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

### 捕捉（trigger 收窄）

**触发条件必须显式**：

- 中文：「记录一个洞察」「记录一个观察」「记下来这个洞察」
- Slash：`/insight`

**不**触发：「我对 X 的看法是…」「为什么 X 总是…」「你怎么看 X」等日常发言。Agent **不**主动建议「要不要存成 insight」——除非用户已经表达了记录意图。

捕捉步骤：
1. 用户显式说出记录意图
2. Agent 用 `date +%Y%m%d-%H%M%S` 取时间戳，从 Raw 概括 1-3 个英文小写单词作 slug
3. `mkdir -p ~/aha-data/insight && Write` 创建 `~/aha-data/insight/insight-<TS>-<slug>.md`，Raw 原样写入
4. 如果触发情境/被解读现象在原话之外被提到，填 `## Context`
5. **不自动起草 Summary**（结构里没有）
6. Agent 在 chat 给 1-2 个自己的视角，**问一句**：「要把这个视角存进去吗？」

### 保存 Agent Take

当用户口头肯定（「存」「保存」「记下来」「不错」等）：
1. Agent 在 `## Agent Takes` append `### YYYY-MM-DD — <角度小标题>` + 1-3 句视角
2. 更新 frontmatter `updated_at`

如果用户没回应或说「先放着」：**什么都不做**，视角留在 chat 里。

### 深谈

当用户主动展开（「展开聊聊」「再谈谈」）：
1. 先在 chat 进行多轮对话
2. 结束时总结 1-3 句 **takeaway**
3. 在 `## Discussions` append `### YYYY-MM-DD — <topic>` + takeaway + 要点
4. 更新 `updated_at`

**没有 takeaway 的 discuss 是 context leak。**（沿用 dao 红线）

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
- 一句话说明发生了什么变更（例：「新建 insight，Raw 已写入；Agent Take 还没存」）
- 至多一个具体下一步建议（例：「我刚那个视角要存吗？」「要展开聊吗？」）

Markdown 文件是唯一事实源。

## 对项目其他文件的影响

需要同步更新：

1. **`README.md`** —「该用哪个 skill」表格新增一行；「仓库结构」与「数据存储」两个代码块加 `insight/`；「设计哲学」段四 skill 改五 skill。
2. **`skills/insight/SKILL.md`** — 新建，按 dao/SKILL.md 的格式写。

不需要：CLI 脚本（沿用 idea/dao 等的"agent 直接读写"模式）。

## 验收标准

实现完成后应满足：

1. 用户说「记录一个洞察 X」→ agent 建 `~/aha-data/insight/insight-<TS>-<slug>.md`，Raw=X，并在 chat 给 1-2 视角问是否保存
2. 用户说「存」→ Agent Takes append 一条，updated_at 更新
3. 用户说「我对 X 的看法是 Y」（无显式记录意图）→ agent **不**建文件，正常对话
4. 用户原话有错字 → Raw 保持原样
5. 用户说「展开聊聊」→ 多轮后产出 takeaway 并 append 到 Discussions
6. 用户说人生顿悟 → agent 提示「这更像 dao，要换吗？」
7. README 表格 / 仓库结构 / 数据存储 三处都更新到位
