---
name: insight
description: 当用户显式触发 /insight、说「记录一个洞察」「记录一个观察」、要求展开探讨已有 insight、或翻阅过往 insight 时使用。区别于 dao（向内顿悟）、idea（向外行动）、tip（实践捷径）、todo（带 deadline 任务）。判定规则——解读对象是外部现象 → insight；解读对象是自己/价值观 → dao。**不要**因为「我对 X 的看法是…」「为什么 X 总是…」「你怎么看 X」等日常发言自动触发。
---

# Insight — 对外部现象的解读沉淀场

捕捉用户对**外部现象**的解读为 Markdown，agent 在 chat 给自己的视角并征得同意后落档，可选地通过多轮深谈展开，并定期翻出旧 insight 回顾。

## Triggers（显式触发，不要宽泛语义）

- 中文:「记录一个洞察」「记录一个观察」「记下来这个洞察」「翻翻以前的 insight」「展开聊聊这个 insight」
- English: "record an insight", "log this observation", "look back at past insights"
- Slash: `/insight`

**不**触发:「我对 X 的看法是…」「为什么 X 总是…」「你怎么看 X」等日常发言。Agent 也**不**主动建议「要不要存成 insight」——除非用户已经表达了记录意图。

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
<可选:观察到的现象 / 触发情境>

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

1. 用户**显式**触发(见 Triggers)
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从 Raw 概括 1-3 个英文小写单词作 slug
3. Agent 用 `mkdir -p ~/aha-data/insight` 后用 Write 创建 `~/aha-data/insight/insight-<TS>-<slug>.md`，把原话原样写进 `## Raw`
4. 如果触发情境/被解读现象在原话之外被提到，填 `## Context`
5. **不自动起草 Summary**(结构里没有这个 section)
6. Agent 在 chat 给 1-2 个自己的视角，**问一句**:「要把这个视角存进去吗？」

### 保存 Agent Take

当用户口头肯定(「存」「保存」「记下来」「不错」「都存」等)：
1. Agent 在 `## Agent Takes` 追加 `### YYYY-MM-DD — <角度小标题>` + 1-3 句视角
2. 更新 frontmatter `updated_at`

如果用户没回应或说「先放着」「不用」：**什么都不做**，视角留在 chat 里。

### 深谈

当用户主动展开(「展开聊聊」「再谈谈」)：
1. 先在 chat 进行多轮对话
2. 结束时总结 1-3 句 **takeaway**
3. 在 `## Discussions` 追加 `### YYYY-MM-DD — <topic>` + takeaway + 要点
4. 更新 `updated_at`

**没有 takeaway 的 discuss 是 context leak。**

### 翻旧

当用户说「翻翻以前的 insight」：
- Agent 用 `ls ~/aha-data/insight/` 或 `grep` 找到记录
- 选一条，读出 Raw + 最新 Agent Take
- 提供选项:「再谈谈？加新视角？还是放着。」
- 一次只处理一条——回顾是慢的

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "用户说的像洞察，我顺手存一下" | 必须用户**显式**说「记录」/`/insight`。日常发言不建文件 |
| "原话有口语/错字，帮他清理一下" | 永远不动 `## Raw` |
| "agent take 写得不错，先存了用户应该不介意" | 必须用户口头同意才能 append 到 `## Agent Takes` |
| "discuss 完直接告诉用户结论" | 必须有 takeaway 并 append 到 `## Discussions`。无 takeaway = context leak |
| "用户说的其实是 dao(人生顿悟)我顺手归 insight" | 提示「听起来更像 dao，要换吗？」。不跨 skill |
| "Raw 太散，提炼一版 Summary" | 结构里没有 Summary。要更紧凑就在 chat 里说，不写文件 |

## Output Style

每次操作后告诉用户：

- 文件路径
- 一句话:发生了什么变更
- 至多一个具体的下一步建议

Markdown 文件是唯一事实源。
