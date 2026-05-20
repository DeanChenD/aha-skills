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
