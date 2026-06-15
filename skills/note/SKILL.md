---
name: note
description: 当用户触发 /note、说「记一笔」「备忘一下」「随手记」「记住这个」「帮我记下这个信息/这件事」、要求查找/补充/整理日常杂项 note 时使用。用于低仪式感记录不属于 idea/dao/insight/tip/keep/todo 的日常信息、事实、链接、临时上下文、经历片段、人物/地点/物品备忘。不要因为普通聊天自动触发；若内容明确是行动想法、感悟、外部洞察、实践捷径、习惯承诺或任务，优先使用对应 skill。
---

# Note — 日常杂项的低摩擦备忘

记录那些「不值得开成一个 workflow，但又不想丢」的日常信息和事情。note 是杂物抽屉：负责留下、补充、找回，不负责孵化、追踪、承诺或判断优先级。

## Triggers（显式触发，不要宽泛语义）

- 中文：「记一笔」「备忘一下」「随手记」「帮我记住」「记下这个信息」「这个也存一下」「查一下我之前记的 note」「给上次那条 note 补一句」
- English: "note this", "quick note", "log this", "remember this", "find my note about..."
- Slash: `/note`

**不**触发：用户只是闲聊、讲述一天发生了什么、贴了一个链接、随口提到某个人/地点/物品，但没有表达「要记录/找回/补充」的意图。

### 路由判定

> 它是不是已经有更窄的归宿？
> - 向外行动想法，需要孵化/研究/决策 → **idea**
> - 向内领悟、价值观、人生感悟 → **dao**
> - 对外部现象的明确记录型洞察 → **insight**
> - 绑定实践域、已经验证的高效做法 → **tip**
> - 持续性习惯、仪式、自我行为承诺 → **keep**
> - 具体任务、deadline、完成/推迟/放弃状态 → **todo**
> - 只是日常事实、材料、片段、参考信息、临时上下文 → **note**

如果用户显式使用 `/note`，一般尊重用户的归类；但当内容包含明确 deadline、状态追踪或行为承诺时，先提示「这更像 todo/keep，要换吗？」不要静默错分。

## Storage

```
~/aha-data/note/
└── note-YYYYMMDD-HHMMSS-<slug>.md
```

每条 note 一个文件。首次写入时 Agent 用 `mkdir -p ~/aha-data/note` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: note-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
kind: memo | reference | event | link | quote | contact | other
---
```

`kind` 是低成本检索线索，不是严格分类。拿不准时用 `other`，不要为了分类打断捕捉。

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话，永不被覆盖>

## Summary
<一两句话概括这条 note 的可检索核心>

## Details
- <可选：名称 / 时间 / 地点 / 人物 / 链接 / 数字 / 关键事实>

## Source
<可选：来源、场景、URL、是谁说的>

## Updates
- YYYY-MM-DD: <补充、修正、后续变化>

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary，修订时归档到此>
```

### 示例文件

```markdown
---
id: note-20260615-203015-repair-shop-hours
created_at: 2026-06-15T20:30:15+08:00
updated_at: 2026-06-15T20:30:15+08:00
kind: reference
---

# 小区东门修表店营业时间

## Raw
记一笔：小区东门那家修表店周二到周日开，上午 10 点到晚上 7 点，老板说换电池一般 20 块。

## Summary
小区东门修表店周二到周日 10:00-19:00 营业；普通手表换电池约 20 元。

## Details
- 地点：小区东门
- 营业：周二到周日，10:00-19:00
- 价格：普通换电池约 20 元

## Source
老板口头说明。

## Updates

## Summary Log
```

## Workflow

### 捕捉

1. 用户显式要求记一笔日常杂项（见 Triggers）
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳，从内容概括 1-3 个英文小写单词作 slug
3. Agent 判断 `kind`：
   - `memo`：短期或模糊备忘，无明确 deadline
   - `reference`：可复用事实、流程、价格、地址、规则
   - `event`：发生过的一件事、一次交流、一个经历片段
   - `link`：URL、资源、文章、视频、工具入口
   - `quote`：某人说过的话、摘录
   - `contact`：人物/机构联系方式或偏好，不含敏感凭据
   - `other`：无法归类或没必要归类
4. Agent 用 `mkdir -p ~/aha-data/note` 后创建 `~/aha-data/note/note-<TS>-<slug>.md`
5. 把用户原话原样写进 `## Raw`，不可润色、不可删改
6. 立刻起草 `## Summary`；如有明确事实，拆到 `## Details`
7. 如果来源、链接、是谁说的、发生场景明确，写进 `## Source`

### 补充 / 修正

当用户说「给上次那条 note 补一句」「这个信息更新了」：
1. Agent 用 `rg` / `ls -t` 在 `~/aha-data/note/` 找到候选 note；不确定时给 2-3 个候选让用户选
2. 新信息追加到 `## Updates`：`- YYYY-MM-DD: <新增/修正内容>`
3. 如果新信息改变了可检索核心，把当前 `## Summary` 追加到 `## Summary Log`，再覆盖 `## Summary`
4. 如需同步结构化事实，更新 `## Details`
5. 更新 frontmatter `updated_at`

### 查找 / 回顾

当用户说「查一下我记过的...」「翻翻 note」：
- 先用 `rg -n -i "<关键词>" ~/aha-data/note` 找候选；如果用户说「最近」，用 `ls -t ~/aha-data/note/*.md | head`
- 读取最相关的 1-3 条，返回标题、Summary、关键 Details 和文件路径
- 找不到时直说找不到，并给出实际搜索过的关键词
- 不要根据记忆编造 note 内容；Markdown 文件是唯一事实源

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "用户随口说了一件事，我帮他自动记下来" | 必须有显式记录意图，普通聊天不建 note |
| "这条有 deadline，但用户说 note，我就照记" | 明确 deadline/完成状态更像 todo，先提示用户 |
| "这是一句人生感悟，但很短，放 note 吧" | 向内领悟归 dao，不要用 note 稀释 dao |
| "这是小技巧，但也算杂项" | 绑定实践域的高效方法归 tip |
| "Raw 有错字，顺手修一下" | 永远不动 Raw；要清晰就改 Summary |
| "用户要记密码/API key/证件号" | Markdown 不加密。先提醒风险，建议用密码管理器；若用户坚持，建议遮蔽敏感部分 |
| "找不到也凭印象答一下" | 不要编造。说明没找到，并列出搜索关键词 |
| "给 note 加 status 追踪" | note 没有 lifecycle。需要状态就转 todo/idea/keep |

## Output Style

每次写入或修改后告诉用户：

- 文件路径
- 一句话：发生了什么变更
- 至多一个具体的下一步建议

查找时最多先展示 3 条；用户要更多再继续。
