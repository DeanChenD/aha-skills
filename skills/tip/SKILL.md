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
