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
