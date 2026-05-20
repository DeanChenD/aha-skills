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
