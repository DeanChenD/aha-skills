# aha-skills 设计文档

- 日期：2026-05-21
- 版本：v0
- 目的：定义 aha-skills 的完整设计——四个 skill 的认知分工、数据形态、Agent 协作方式

---

## 1. 设计哲学

aha-skills 是关于「如何把易逝的认知瞬间留下并持续生长」的一组 file-based agent skill。它不是工具集合，而是围绕这件事的认知分工：

- `idea` — 从灵光一闪的创意想法，到执行落地的实际项目，向外的行动直觉：捕捉 → 孵化 → 决策成行
- `dao` — "道"、"感悟"、"方法论"、"认知"，向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- `tip` — "小妙招"、"小技巧"、"邪修方法"，行动上总结的捷径：记录 → 复用 → 如有可能泛化推广
- `todo` — 从待办事项到事后复盘提升，维持节奏：任务（带 due / 状态 / 推迟记录）

四个 skill 之间不是 CRUD bucket，而是认知模式的差异。能选对 skill，往往就已经在做提炼了。

---

## 2. 设计公约

1. **Markdown 是唯一事实源和数据源**。Agent 和人读同一份 `.md`。
2. **来自人的原始输入不可变**。`## Raw` 永远保留用户原话；提炼写在 `## Summary`，旧版进 `## Summary Log`。这是用户认知演化的考古层，不是版本噪音。
3. **Agent 自行读取和编辑 `.md` 文件**。优先用已有的通用工具（`Read` / `Edit` / `Write` / `Glob` / `Grep` / `Bash`）读写 md，不重复造轮子，不额外封装脚本。
4. **不强加 workflow**。`idea`、`todo` 等可以有状态定义，但没有状态机做约束，不强制推进。Agent 适时给出状态建议，用户做决定。

---

## 3. 设计约束

1. **第一性原理**：所有实现必须服务于核心目标——把易逝的认知瞬间留下并持续生长。不能清楚说明服务于该目标的功能，一律不实现。
2. **奥卡姆剃刀**：选择能解决当前问题的最简单方案。优先级：Markdown + 本地文件 > 数据库 > 服务端 > 框架化系统。不引入非必要依赖、抽象、配置层、构建流程或运行时。
3. **YAGNI**：不为假设中的未来需求提前设计。不做多用户、权限、同步、插件系统等能力。只有真实、明确出现的需求，才允许进入设计。
4. **数据优先于程序**：Markdown 是核心资产，程序脚本只是辅助工具。
5. **透明性优先**：人和 Agent 必须能读懂同一份数据。禁止让系统变成只能由 Agent 理解和维护的黑箱。
6. **Agent 不越权**：Agent 可以建议、提炼、归类、关联、联想和复盘。Agent 不得擅自覆盖 `Raw`、删除记录、推进状态、顺延任务或强加 workflow。涉及用户判断的动作，默认只提出建议，不自动执行。

---

## 4. 仓库形态

```
aha-skills/
├── README.md              # 哲学 / 公约 / 约束 / 该用哪个 skill
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── tip/SKILL.md
    └── todo/SKILL.md
```

仓库只有 SKILL.md 与说明文档：没有共享库、没有 CLI 脚本、没有测试套件、没有 references/ 子流程、没有 Makefile。每个 SKILL.md 自身写清楚 Agent 需要做什么、不要做什么。

---

## 5. 数据形态

### 5.1 工作区

所有运行时数据放在**当前操作系统用户的家目录**下的共享 `aha-data/` 目录中（`~/aha-data/`），每个 skill 在其下拥有自己的子目录：

```
~/aha-data/
├── idea/
│   └── idea-YYYYMMDD-HHMMSS-<slug>.md
├── dao/
│   └── dao-YYYYMMDD-HHMMSS-<slug>.md
├── tip/
│   └── tip-YYYYMMDD-HHMMSS-<slug>.md
└── todo/
    └── todo-YYYYMMDD-HHMMSS-<slug>.md
```

一个 skill 的所有记录平铺在该子目录里，不分二级结构。Agent 在第一次写入时若目录不存在，用 `mkdir -p` 创建。

**为什么用绝对家目录路径而不是 cwd 相对路径**：cwd 在不同 host / IDE / cron / shell 启动方式下解析为不同位置，会导致同一用户的笔记**散落在多个 aha-data/ 目录**互相看不见。绑定到家目录就消除了这种碎片化——idea / dao / tip / todo 都是个人认知，跨项目共享是应有之义（特别是 tip："pytest -x" 这条捷径在任何项目里都该查得到）。

### 5.2 单个 Markdown 文件结构

Markdown 文件由两部分组成：

**Frontmatter**（YAML），公共字段：

```yaml
---
id: <skill>-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

- `id`：文档全局唯一标识，与文件名（去掉 `.md`）一致
- `created_at` / `updated_at`：ISO 8601 with local UTC offset
- 各 skill 可按需追加字段（详见 §6）

**正文**，公共字段：

- `## Raw`：用户原始输入。**永不被覆盖、永不被改写**。

各 skill 在 Raw 之外按需追加 section（详见 §6）。

### 5.3 ID 生成

Agent 用 Bash 生成时间戳与 slug：

```bash
TS=$(date +%Y%m%d-%H%M%S)
SLUG=<1-3 个英文小写单词,hyphen 分隔,从 Raw 概括>
ID=<skill>-${TS}-${SLUG}
```

slug 由 Agent 从 Raw 概括（不是用户提供，也不需要去重——时间戳保证唯一性）。

### 5.4 时间戳

所有 `created_at` / `updated_at` / `due_at` 都用 ISO 8601 with local UTC offset：

```
2026-05-21T15:30:00+08:00
```

Agent 用 Bash 取当前时间（前提：用户在 +08:00 时区）：

```bash
date "+%Y-%m-%dT%H:%M:%S+08:00"
```

如果将来跨时区使用，再换成 `date +%Y-%m-%dT%H:%M:%S%z` 并给 offset 加冒号。v0 不预设。

### 5.5 「考古层」模式

承载"用户认知演化"的 section（Summary、Refined 之类反复打磨的提炼版本）遵循同一模式：

- 当前版本写在 `## <SectionName>`
- 修订时把旧版本追加到 `## <SectionName> Log` 末尾，格式为：
  ```
  - YYYY-MM-DD (vN): <旧内容>
  ```

具体哪些 section 适用本模式由各 skill 显式列出（详见 §6）。Agent 修改这些 section 之前，必须先把当前内容追加到对应 Log 的尾部，再用新内容覆盖。这一规则由 SKILL.md 的硬约束保障，不靠代码（详见 §7）。

**不适用本模式的 section** 不享有"考古"待遇——它们要么是不可变的（`## Raw`），要么是结构化的事实流水（`## Decision Log` / `## Postponement Log` / `## Discussions`，本身就是 append-only），要么是低价值不必版本化的（todo 的 `## Description`，覆盖即可）。

### 5.6 Raw 的不可变性

`## Raw` 一旦写入永不被覆盖、永不被 Agent 改写——**即使用户说"原话有错字帮我改"**。这是公约 2 的红线。

如果用户希望「修正"看起来更对"的版本」，Agent 引导走 `## Summary` 的修订（旧 Summary 进 `## Summary Log`）。

这条不可变性由各 SKILL.md 的"Red Flags"区块强约束，不靠代码边界。

---

## 6. 四个 skill 的具体设计

### 6.1 `idea` — 行动想法的孵化器

**定位**：从灵光一闪到执行落地。捕捉 → 分类 → 研究 → 决策。

**触发**：`/idea`、"我有个想法/灵感"、"想到一个"、"记一下这个点子"、"灵光一闪"、"pause 一下"、"kill 那个"、"idea inbox"……

**与 dao / tip / todo 的边界**：
- vs `dao`：dao 是向内顿悟（"我对 X 的理解是…"），idea 是向外行动（"我们可以做 X"）
- vs `tip`：tip 是已经验证过的捷径，idea 是尚未孵化的方向
- vs `todo`：todo 是有 due 的具体任务；idea 是没有 due / 形态未定的探索

**Frontmatter 完整结构**（公共三字段 + skill 扩展）：

```yaml
---
id: idea-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
status: inbox | researching | planning | completed | paused | killed
---
```

`status` 是软状态，Agent 提议 / 用户决定。状态语义：

- `inbox`：仅记录，未开始处理
- `researching`：需要进一步探索 / 验证
- `planning`：信息够了可以形成具体 plan
- `completed`：已经成了能跑的方案 / artifact
- `paused`：明确暂时挂起
- `killed`：明确放弃，附原因

**Body 结构**：

```markdown
# <根据 Raw 提炼的简短 title>

## Raw
<用户原话,永不被覆盖>

## Summary
<latest 提炼版;首次 capture 后 Agent 立刻起草一版>

## Plan
- [ ] <下一步行动>
- [ ] ...

## Question
- [ ] <澄清类问题、启发式问题...>

## Decision Log
- YYYY-MM-DD: Captured.
- YYYY-MM-DD: Moved to researching because <原因>.

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary>
```

**典型工作流（Agent 视角）**：

1. 用户说"我有个灵感 X"
2. Agent 用 Bash 取时间戳生成 ID，用 Write 创建文件，把 X 原样写进 `## Raw`
3. Agent 立即起草 `## Summary`（总结精炼）、`## Plan`（具体的下一步）和 `## Question`（澄清类问题、启发式问题），并写一条 `## Decision Log` 记录 captured
4. 给用户一个具体选择：「set status to researching 并把 plan 推下去？」「先 inbox 放着？」「killed 因为 X？」
5. 用户回答后，Agent 用 Edit 改 frontmatter `status` 和 `updated_at`，并在 `## Decision Log` 追加一行

**Red Flags（写进 SKILL.md）**：

| 看到自己想 | 实际是 |
|---|---|
| "原话不通顺,帮他润色一下 Raw" | 不要动 `## Raw`。改 `## Summary`,旧 Summary 进 `## Summary Log` |
| "用户没回答 paused 的提议,那就当 paused 吧" | 不要替用户做 paused/killed 决定 |
| "stale 5 天了我顺手 kill 了" | 不要 auto-kill。明确提议 + 等用户确认 |
| "我问个开放问题让他想想" | 不问"你想做什么"。给具体选项（continue / answer / pause / kill） |

---

### 6.2 `dao` — 向内顿悟的提炼场

**定位**：用户对人 / 世界 / 自我的领悟。捕捉原话 → 提炼成"沉淀过的"版本 → 必要时多轮深谈。

**触发**：`/dao`、"我悟到了"、"想通了"、"感悟到"、"想明白了"、"再帮我提炼一下"、"展开聊聊"、"翻翻以前的感悟"……

**与 idea / tip / todo 的边界**（关键判定口径，写进 SKILL.md）：

> 一句话能不能**剥离任何具体实践 / 工具 / 域**还完整说出来？
> - 能（"关于恐惧 / 承诺 / 自我 / 抗拒,我发现…"）→ **dao**
> - 不能（必须带"调试时…" / "写 spec 时…" / "用 X 工具…"才说得通）→ **tip**

典型例子：
- "答应别人前先睡一觉" → **dao**（关于自我对承诺的关系）
- "恐惧是指南针,不是停止线" → **dao**
- "心里抗拒一件小事,往往不是事本身" → **dao**
- "卡 30 分钟以上的 bug,先去散步" → **tip**（绑定调试域）
- "PR review 长 PR 时先看 test 改了什么" → **tip**（绑定代码评审域）
- "spec 写出来就有 push back,说明文档起作用了" → **tip**（绑定写文档域）

**Frontmatter 完整结构**（公共三字段，无扩展）：

```yaml
---
id: dao-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

**Body 结构**：

```markdown
# <根据 Raw 提炼的简短 title>

## Raw
<用户原话,永不被覆盖>

## Summary
<latest 提炼版;首次 capture 后 Agent 立刻起草一版>

## Context
<可选:触发情境——什么时候 / 为什么想到这个>

## Discussions
### YYYY-MM-DD — <topic>
<多轮探讨的对话原文 / 摘要 + 1-3 句 takeaway>

### YYYY-MM-DD — <另一个 topic>
...

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary>
```

多轮深谈直接以 `### <date> — <topic>` append 到主文件的 `## Discussions`，不分拆到 sessions 子目录。一份 dao 永远是一份文件。

**典型工作流**：

1. 用户说"我刚刚悟到 X"
2. Agent 创建 dao 文件，把 X 写进 `## Raw`
3. **除非用户明确说"先放着"**，Agent 立刻起草一版 `## Summary`（比 Raw 更紧、更清晰，不加新主张、不说教）
4. 如果用户提到了 trigger，把它放到 `## Context`
5. 如果是哲学性话题且用户开放，提议一个具体角度展开（不自动开始）
6. 用户希望深谈时：Agent 先在聊天里走多轮探讨，结束后总结 1-3 句 takeaway，再 append `### <date> — <topic>` 到 `## Discussions`
7. 如果探讨实质改变了"沉淀"，立即触发一次 `## Summary` 的修订（旧版进 `## Summary Log`）

**Red Flags（写进 SKILL.md）**：

| 看到自己想 | 实际是 |
|---|---|
| "原话有错字 / 口语,帮他改一下" | 永远不动 `## Raw`。改 `## Summary` |
| "discuss 完直接告诉用户结论" | discuss 必须有 takeaway 并 append 到 `## Discussions`。无 takeaway = context leak |
| "重新 refine 一版直接覆盖旧的" | 旧版本必须存到 `## Summary Log`。永不丢历史 |

---

### 6.3 `tip` — 实践域里的捷径合集

**定位**：绑定在某个实践域（工具、流程、某类任务）里的方法。"卡 30 分钟的 bug 先散步"、"PR review 先看 test"、"pytest -x 比 -v 省调试时间"。

**触发**：`/tip`、"小妙招"、"小技巧"、"邪修"、"我发现一个高效做法"、"快捷"、"省时间"……

**与 dao / idea / todo 的边界**：

- vs `dao`：见 §6.2 的判定口径——能不能脱离实践域说出来。**人换了 tip 还能用,人变了 dao 才作用**
- vs `idea`：tip 是已经验证有效的捷径；idea 是还没孵化的方向
- vs `todo`：tip 不带 due,是一条经验；todo 是一件具体的事

**Frontmatter 完整结构**（公共三字段，无扩展）：

```yaml
---
id: tip-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

**Body 结构**：

```markdown
# <根据 Raw 提炼的简短 title>

## Raw
<用户原话,永不被覆盖>

## Summary
<latest 提炼版;首次 capture 后 Agent 立刻起草一版>

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary>
```

**关键取舍：不单独保留 Domain / Reuse Log / Generalization 三个 section**。Domain 融进 Summary 的开头（"在 PR 评审场景下,先看 test……"自然就锚定了 domain）。复用次数和泛化推广不在文件里追踪，谁要用谁口头说，需要的时候 Agent 用 Grep 一搜就有。

**典型工作流**：

1. 用户说"我发现一个高效做法:X"
2. Agent 创建 tip 文件，把 X 写进 `## Raw`
3. Agent 立即起草 `## Summary`，确保**开头就锚定实践域**（"在 X 场景下,..."）
4. 不主动追踪 reuse / 不主动询问"是否泛化"。当用户说"上次那个 tip 还能用吗"或"这个 tip 是不是也适用 Y"时，Agent 用 Grep / Read 现场处理，必要时触发一次 `## Summary` 的修订

**Red Flags（写进 SKILL.md）**：

| 看到自己想 | 实际是 |
|---|---|
| "Summary 不写实践域,太啰嗦了" | Summary 开头必须锚定 domain,否则与 dao 无法区分 |
| "用户说'这个对人生也适用',我顺手把它泛化成 dao" | 不要跨 skill 迁移。提议用户在 dao 里另起一条 |
| "原话啰嗦,帮他改一下 Raw" | 永远不动 Raw |

---

### 6.4 `todo` — 带 due 的任务台账

**定位**：纯任务管理。创建 → 状态流转 → 推迟（必须有理由） → 完成或放弃。

**触发**：`/todo`、"今天要做……"、"加个待办"、"明天前帮我做 X"、"想推迟到……"、"这件事完成了"、"砍掉那个"、"看看待办"……

**与其他三个的边界**：

- vs `idea`：todo 有 due 或至少是"具体可执行的事"；idea 是形态未定的探索
- vs `dao` / `tip`：dao 和 tip 都不带 due，都不是要"做完"的事

> 当用户在 `idea` 里成熟到了"明天前推下去"，Agent 提议「在 todo 里建一条任务，并在 idea 的 Decision Log 里链接过去」——idea 仍保留为探索的考古层，不被 todo 取代。

**Frontmatter 完整结构**（公共三字段 + skill 扩展）：

```yaml
---
id: todo-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
status: pending | in_progress | blocked | done | dropped
due_at: YYYY-MM-DDTHH:MM:SS+08:00   # 可选;只有日期时按当地 23:59:59 解释
---
```

`status` 是软状态：

- `pending`：未开始
- `in_progress`：进行中
- `blocked`：被阻塞
- `done`：完成
- `dropped`：放弃（必须在正文里写理由）

**Body 结构**：

```markdown
# <根据 Raw 提炼的简短 title>

## Raw
<用户原话,永不被覆盖>

## Description
<可选:把任务的具体要求展开>

## Postponement Log
- YYYY-MM-DD: <old due> → <new due>: <reason>
```

任务文件就是任务文件：没有日志、没有阶段对话记录、没有周/月汇总。

**典型工作流**：

1. 用户说"明天前完成 X"
2. Agent 取时间戳生成 ID，创建 todo 文件，把 X 原样写进 `## Raw`，frontmatter `status: pending` + `due_at: <明天 23:59:59 当地>`
3. 如果任务需要展开，Agent 起草 `## Description`
4. 用户说"这个推迟到周五"：Agent 在 `## Postponement Log` append 一条 `- YYYY-MM-DD: <old> → <new>: <reason>`，更新 frontmatter `due_at` 和 `updated_at`。**没有 reason，Agent 必须先问。**
5. 用户说"这个完成了"：Agent 把 frontmatter `status: done`，正文里追加一行注解（可选）；不另外开 completed_at 字段，updated_at 等价
6. 用户问"什么 overdue 了"：Agent 用 Bash 现场扫：

   ```bash
   NOW=$(date +%Y-%m-%dT%H:%M:%S%z)
   grep -lE '^status: (pending|in_progress|blocked)' ~/aha-data/todo/*.md \
     | xargs grep -lE "^due_at: " \
     | while read f; do
         due=$(grep '^due_at:' "$f" | head -1 | awk '{print $2}')
         [[ "$due" < "$NOW" ]] && echo "$f"
       done
   ```

   一次只处理一条 overdue（oldest first），处理完问要不要下一条。

**Red Flags（写进 SKILL.md）**：

| 看到自己想 | 实际是 |
|---|---|
| "overdue 了我顺手帮他延 3 天" | 永远不要 auto-postpone。先问 difficulty / 目标 due |
| "用户没说 due 我猜个明天" | 不要猜 due。明确问;他说没有就接受无 due 创建 |
| "用户写了一句感想,要不要我顺手 todo 一下" | 不要 auto-create todo。问 |
| "推迟没说理由,我替他写一个" | 不要替用户写 reason。先问 |

---

## 7. SKILL.md 的形态约束

每个 SKILL.md 必须包含这些区块（顺序可以微调）：

1. **Frontmatter**（YAML）：`name` + `description`。description 用 active voice 写清楚"何时用、与其他 skill 的边界"
2. **Triggers**：触发的中英文短语样例 + slash 命令。说明这些不是穷举
3. **Storage**：本 skill 的 workspace 路径
4. **Markdown Shape**：本 skill 的 frontmatter + body 结构（含示例文件）
5. **Workflow**：捕捉 / 推进 / 修订的标准流程，按 Agent 第一视角写
6. **Red Flags**：表格形式列出"看到自己想 X，实际是 Y"
7. **Output Style**：每次操作之后告诉用户什么（一般是：文件路径 + 一句变更摘要 + 至多一个具体下一步建议）

---

## 8. 跨源查询

**完全不在 skill 里设计这件事**。

当用户问"这周所有 idea"、"idea 与 tip 有没有共同主题"、"我最近 dao 几条"时，Agent **临场**用通用工具：

```bash
ls ~/aha-data/idea/idea-2026-05*.md           # 按文件名前缀的日期过滤
grep -l 'status: researching' ~/aha-data/idea/*.md
grep -ri '<keyword>' ~/aha-data/                # 跨 skill 关键词
find ~/aha-data/ -name '*.md' -newer <ref-file>
```

README 里**不放** cookbook，让 Agent 现场推理。原因：任何固定的查询模板都是"我提前想到这个用法"，违反 YAGNI。

---

## 9. 安装与运行假设

- **单机使用**。不考虑多 host 共享同一 workspace 的情形
- **数据落在家目录**：`~/aha-data/`
- **无并发写**：用户和 Agent 不同时写同一个文件。一旦有并发需求再回头加 atomic write / flock，现在不预先设计
- **无外部依赖**：Bash + 标准 Unix utilities（`date` / `ls` / `grep` / `find` / `awk`）即可

---

## 10. 不在 v0 范围内

明确声明本版本不实现的能力，以便未来若变成真实痛点时单独立 spec 讨论：

- 跨 skill 模式挖掘 / 周月复盘 / 自动汇总文件
- 多机 / 多用户 / cron 同步
- `[SILENT]` 类协议
- atomic write / flock / mtime conflict 检测
- schema_version / migration 工具
- shell 注入面专项防御（前提：用户走 chat 而不是把 raw text 直接拼进 shell）
- conflict 文件扫描（`*conflict*.md`）
- 测试套件
- frontmatter 里的 tags / priority / next_review_at / refine_count / reuse_count / domain

---

## 11. 待观察问题

留作真实使用一段时间后再回头评估：

- v0 跑一段时间后，是否真的不需要任何 tag 系统？grep 关键词在文件量上千之后还够用吗？
- `## Discussions` 直接 inline 在 dao 主文件里，长 dao 是否会膨胀到不便阅读？真出现了再考虑分拆
- `idea` 推到 `todo` 的链接现在是"在 idea 的 Decision Log 里写一条"。是否需要一个更结构化的 cross-reference 字段？真出现需要再考虑

---

*— end of design v0 —*
