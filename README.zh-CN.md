# aha-skills

> [English](README.md) | **简体中文**

一组轻量级、基于文件的 AI agent skill 集合（适配 Claude Code、Hermes 等 host）。每个 skill 自包含在自己的目录里，通过 `SKILL.md` 描述何时及如何使用，并以纯 Markdown 持久化状态——人类和 agent 共读同一份事实源。

所有运行时数据存放在 host 当前工作目录下的共享 `aha-workspace/` 目录中，每个 skill 在其下拥有自己的子目录（例如 `aha-workspace/idea/`）。

## 设计哲学

`aha-skills` 不是一个工具集合，而是关于「如何把易逝的认知瞬间留下」的四个分工：

- `idea` — 向外的行动直觉：捕捉 → 孵化 → 决策成行
- `dao` — 向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- `daily` — 维持节奏：任务、日志、check-in、复盘
- `reflect` — 跨 skill 的模式挖掘：在一个时间窗口内跨着读 idea + dao + daily，surface 出共现的 tag、反复出现的困难、跨源的主题

四条贯穿其上的设计公约：

1. **Markdown 是单一事实源**。Agent 和人读同一份 `.md`，不存在 agent 私有 state。
2. **原文不可变**。`## Raw` 永远保留用户原话；提炼写在 `## Refined`，旧版进 `## Refinement Log`。这是用户认知演化的考古层，不是版本噪音。
3. **state mutation 走 deterministic CLI**。`*_md.py` 同时是 agent 的写入路径和测试边界，挡住 LLM 自由编辑时的格式漂移。
4. **不强加 workflow**。`dao` 没有状态机，`daily` 不自动顺延 due —— agent 提建议，用户做决定。

## 整体架构

```
                    ┌─────────────────────────────────┐
                    │       aha-workspace/            │  ← 共享运行时根目录
                    └─────────────────────────────────┘
                       │           │           │
        ┌──────────────┘           │           └──────────────┐
        ▼                          ▼                          ▼
  ┌──────────┐              ┌──────────┐              ┌──────────┐
  │  idea/   │              │   dao/   │              │  daily/  │
  │ 向外行动 │              │ 向内领悟 │              │ 节奏维持 │
  └──────────┘              └──────────┘              └──────────┘
        └─────────────────────────┬─────────────────────────┘
                                  ▼
                          ┌─────────────┐
                          │  reflect/   │   ← 跨 skill 模式挖掘
                          │ 跨 skill 复盘 │     只读上面三个的数据
                          └─────────────┘
```

三个 skill 各自管理自己的写入面；第四个 `reflect` 在它们之上，跨源做模式挖掘。每个 skill 占用 `aha-workspace/` 下的一个子目录；只有 `reflect` 在运行时跨目录读，且仅做只读。

### 该用哪个 skill

| 用户在说 | 用哪个 skill |
|---|---|
| 有 deadline 的待办 / 今天做了什么 / 周/月回顾 / overdue / postpone | `daily` |
| 一个外部行动方向，需要孵化、研究、决策 / "我有个想法" / idea inbox | `idea` |
| 一个内省式领悟、一句话顿悟、想再想想 / "我悟到了" / refine an insight | `dao` |
| 跨着看 idea + dao + daily 在一段时间内的共同 tag / 反复的困难 / 跨源主题 | `reflect` |

意图模糊时，宁可问一句也别猜——这是刻意区分的工作模式，不是可互换的桶。**单源**的回顾（"看看本周的任务"）留在那个 skill 里；只有显式跨源的综合才用 `reflect`。

## 各 Skill 介绍

### `idea/` — 想法收件箱与孵化器

捕捉灵光一闪的想法，打上时间戳、做分类，并把它们孵化成 Markdown 形式的研究计划。

- **触发**：`/idea`，或任何记录 / 回顾 / 推进 / 终止某个想法的请求。
- **存储**：`./aha-workspace/idea/idea-md/<idea-id>.md`（每个想法一个文件，原文永不覆盖）。
- **生命周期**：`inbox → researching → planning → completed`（外加 `paused` / `killed` 两个终止态）。
- **CLI**：`skills/idea/scripts/idea_md.py` 提供确定性的 `capture`、`update`、`scan` 子命令。

完整工作流、Markdown 结构和定时回顾模式见 [`skills/idea/SKILL.md`](skills/idea/SKILL.md)。

#### 快速上手

```bash
# 捕捉一个想法
python3 skills/idea/scripts/idea_md.py capture \
  --text "Build a tiny idea inbox" \
  --source chat \
  --status researching \
  --category product \
  --tags "idea,research"

# 列出陈旧或到期需回顾的想法
python3 skills/idea/scripts/idea_md.py scan --stale-days 7 --include-paused

# 推进一个想法
python3 skills/idea/scripts/idea_md.py update \
  ./aha-workspace/idea/idea-md/<file>.md \
  --status planning \
  --decision "Ready for a concrete plan." \
  --bump-review
```

### `dao/` — 个人感悟的捕捉、提炼与回顾（感悟 / 道）

逐字捕捉个人感悟，将它们打磨成"沉淀过的"提炼版，必要时通过多轮哲学探讨深入挖掘，并定期把旧感悟翻出来回顾。是 `idea` 的对偶：`idea` 处理向外的行动，`dao` 处理向内的领悟。

- **触发**：`/dao`、"我悟到了 / 想通了 / 感悟到 ..."、"再帮我提炼一下"、"展开聊聊"、"翻翻以前的感悟"。
- **存储**：
  - 主记录：`./aha-workspace/dao/dao-md/<dao-id>.md`（原文永不覆盖；`## Refined` 滚动更新；`## Refinement Log` 归档历史版本）。
  - 探讨记录：`./aha-workspace/dao/sessions/<dao-id>-session-NNN.md`（主文件以 1-3 句 takeaway 链接到此）。
- **动作**（不强加状态流转）：`capture`、`refine`、`discuss`、`scan`、`update`。
- **CLI**：`skills/dao/scripts/dao_md.py`。

触发条件、Markdown 结构和定时回顾模式见 [`skills/dao/SKILL.md`](skills/dao/SKILL.md)。

#### 快速上手

```bash
# 捕捉一条原始感悟
F=$(python3 skills/dao/scripts/dao_md.py capture \
  --text "Fear is a compass, not a stop sign" \
  --category life --tags "courage,fear")

# 提炼（自动把上一个版本归档进 ## Refinement Log）
python3 skills/dao/scripts/dao_md.py refine "$F" \
  --text "Fear marks the edge of where I should grow."

# 记录一次哲学探讨
python3 skills/dao/scripts/dao_md.py discuss "$F" \
  --topic "Fear vs aversion" \
  --conversation "user: ...\nagent: ..." \
  --takeaway "Distinguish fear (points at growth) from aversion (points at self-protection)."

# 随机翻出 3 条旧感悟回顾（同时累加 review_count）
python3 skills/dao/scripts/dao_md.py scan --mode random --limit 3
python3 skills/dao/scripts/dao_md.py scan --mode least-reviewed --tag courage
```

### `daily/` — 任务、日志、Check-in 与定期复盘

管理带明确 due 的待办（推迟必须显式记录）、记录阶段性进展和暴露的卡点、按天写自由日志、产出日 / 周 / 月复盘。是 `idea`（向外行动）和 `dao`（向内领悟）之外的"节奏型"补充。

- **触发**：`/daily`、"今天要做..."、"加个待办"、"今天没做完..."、"想推迟到..."、"聊聊 X 的进展"、"记一笔"、"今天感觉..."、"看看这周"、"周回顾"。
- **存储**：
  - 任务：`./aha-workspace/daily/tasks/task-<id>.md`（status 流转 + 困难 / 推迟 / check-in 三类日志）。
  - 日志：`./aha-workspace/daily/logs/log-YYYY-MM-DD.md`（每天一个文件，多个 `## HH:MM — title` 子段追加在内）。
  - Check-in 记录：`./aha-workspace/daily/check-ins/<task-id>-checkin-NNN.md`。
  - 复盘（agent 用 `Write` 写出）：`./aha-workspace/daily/reviews/review-<period-id>.md`。
- **动作**：`task` / `update` / `checkin` / `log` / `scan`（不强加状态流转）。
- **CLI**：`skills/daily/scripts/daily_md.py`。

过期任务的会话流程、check-in 模式和复盘骨架见 [`skills/daily/SKILL.md`](skills/daily/SKILL.md)。

#### 快速上手

```bash
# 创建一个任务
T=$(python3 skills/daily/scripts/daily_md.py task \
  --text "Write the v1 spec" --due "2030-01-15T18:00" \
  --priority high --tags "work,doc")

# 推迟（必须给理由，记进 ## Postponement Log）
python3 skills/daily/scripts/daily_md.py update "$T" \
  --due "2030-01-20T18:00" --postpone-reason "PRD review pending"

# 记一次 check-in
python3 skills/daily/scripts/daily_md.py checkin "$T" \
  --topic "Mid-build status" \
  --conversation "user: status?\nagent: 30% done." \
  --takeaway "Half a day to lock the data model." \
  --difficulty "data model still fuzzy" \
  --next-step "Lock model tomorrow morning"

# 追加一条当日日志
python3 skills/daily/scripts/daily_md.py log \
  --text "Got distracted three times this afternoon" \
  --time "14:30" --title "Focus dip" --tags "work,mood"

# 当前有什么 overdue
python3 skills/daily/scripts/daily_md.py scan --mode overdue

# 拉本周的任务 + 日志，准备复盘
python3 skills/daily/scripts/daily_md.py scan --mode period --period week --type all
```

### `reflect/` — 跨 skill 的周维度模式挖掘

在一个时间窗口内跨 `idea` + `dao` + `daily` 读取所有记录，surface 出可供讨论的模式——比如「本周 3 个 dao 都在讲『界限』」「2 个 overdue 都来自『答应别人太快』」「一个反复出现的 tag 横跨任务、感悟和想法」。位于其他三个之上；只读。

- **触发**：`/reflect`、「跨着想想」「跨 skill 复盘一下」「这周看下整体」「最近三周有什么 pattern」（完整短语清单见 [`skills/reflect/SKILL.md`](skills/reflect/SKILL.md)）。
- **存储**：`./aha-workspace/reflect/reflections/reflect-<period-id>.md`（每次 `save` 写一个新文件，**永不覆盖**）。
- **动作**：`aggregate` / `tags` / `difficulties` / `save`（reflect 自身不捕获任何新内容）。
- **CLI**：`skills/reflect/scripts/reflect_md.py`。

`save` 会用 CLI 把跨源数据切片预先填进 reflection 文件（idea / dao / daily.tasks / daily.logs / daily.difficulties + tag 词频）。`## 模式与启示` 和 `## 下阶段意图` 留空，由 agent 与用户在实际对话之后共同填写——不可由 LLM 自动产出。

#### 快速上手

```bash
# 本周跨三个源
python3 skills/reflect/scripts/reflect_md.py aggregate --period week
python3 skills/reflect/scripts/reflect_md.py tags --period week --min-count 2
python3 skills/reflect/scripts/reflect_md.py difficulties --period week

# 与用户讨论之后归档反思文件
python3 skills/reflect/scripts/reflect_md.py save --period week
# → ./aha-workspace/reflect/reflections/reflect-2026-W20.md

# 锚定到指定日期（比如上周）
python3 skills/reflect/scripts/reflect_md.py save --period week --date 2026-05-07
```

## 仓库结构

```
aha-skills/
├── README.md               # 英文 README
├── README.zh-CN.md         # 中文 README（本文件）
├── .gitignore
└── skills/
    ├── idea/
    │   ├── SKILL.md            # Skill 定义（frontmatter + 工作流）
    │   ├── references/         # skill 按需加载的参考资料
    │   ├── scripts/
    │   │   └── idea_md.py      # CLI：capture / update / scan
    │   └── tests/
    │       └── test_idea_md.py # idea_md.py 的 unittest 套件
    ├── dao/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── scripts/
    │   │   └── dao_md.py        # CLI：capture / refine / discuss / scan / update
    │   └── tests/
    │       └── test_dao_md.py
    ├── daily/
    │   ├── SKILL.md
    │   ├── references/          # 5 个子工作流：task-capture / overdue-flow / checkin-flow / log-flow / review-flow
    │   ├── scripts/
    │   │   └── daily_md.py      # CLI：task / update / checkin / log / scan
    │   └── tests/
    │       └── test_daily_md.py
    └── reflect/
        ├── SKILL.md
        ├── references/
        ├── scripts/
        │   └── reflect_md.py    # CLI：aggregate / tags / difficulties / save
        └── tests/
            └── test_reflect_md.py
```

## 安装到 host

- **Claude Code**：把 skill 目录放进 `~/.claude/skills/`（或建符号链接），然后通过 `Skill` 工具 / 斜杠命令调用。
- **Hermes**：放在 `~/.hermes/skills/<skill-name>` 下，或把父目录加进 `skills.external_dirs`；把 `workdir` 设为一个稳定父目录，保证 `aha-workspace/` 跨次复用。

## 跑测试

```bash
python3 skills/idea/tests/test_idea_md.py
python3 skills/dao/tests/test_dao_md.py
python3 skills/daily/tests/test_daily_md.py
python3 skills/reflect/tests/test_reflect_md.py
```

## 通用约定

- 每条记录一个 Markdown 文件；用户原始内容逐字保留。
- 所有路径相对当前工作目录，通过 `aha-workspace/` 解析。
- Skill 在运行时永远不要写到 `aha-workspace/<skill>/` 之外。
- 新增 skill 沿用同款骨架：`SKILL.md`，可选 `scripts/`、`tests/`、`references/`。

