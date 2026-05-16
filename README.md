# aha-skills

> **简体中文** | [English](README.en.md)

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
  - 复盘（`daily_md.py review` 写出，与 reflect.save 同款 write-once 纪律）：`./aha-workspace/daily/reviews/review-<period-id>.md`。
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
├── README.md               # 中文 README（本文件）
├── README.en.md            # 英文 README
├── .gitignore
└── skills/
    ├── _lib/
    │   ├── aha_md.py            # 4 个 skill 共用的原语：frontmatter / sanitize /
    │   │                        # section finder（line-based + fence-aware）/
    │   │                        # atomic_write / locked_record / workspace_anchor /
    │   │                        # schema_version / period_range/id 等
    │   └── tests/test_aha_md.py
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
    │   │   └── daily_md.py      # CLI：task / update / checkin / log / scan / review
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

> **重要**：四个 skill 的脚本都从同级 `_lib/aha_md.py` 导入共享原语
> （`scripts/*_md.py` 第一行 `sys.path.insert(0, .../skills/_lib)`）。
> **必须把整个 `skills/` 父目录复制/符号链接到 host**，或者保证 `_lib/` 与
> 被装的 skill 维持同级关系。**只装某一个 skill 而不带 `_lib/`，启动即
> ImportError**。

- **Claude Code**：把整个 `skills/` 目录链到 `~/.claude/skills/` 下
  （例：`ln -s "$(pwd)/skills" ~/.claude/skills/aha`），保留 `_lib/` 与
  四个 skill 的同级关系。也可以单独符号链接 `idea/ dao/ daily/ reflect/`，
  但同时 **必须** 同步链接 `_lib/`。
- **Hermes**：放在 `~/.hermes/skills/<parent>` 下，或把父目录加进
  `skills.external_dirs`；同样保留 `_lib/` 同级。`workdir` 设为一个稳定
  父目录，保证 `aha-workspace/` 跨次复用。

## Host 能力矩阵 — `[SILENT]` 协议

cron-prompt 例子里（特别是 `idea/SKILL.md` 末尾、`dao/SKILL.md:150`、`reflect/SKILL.md` 末尾）会让 agent "if nothing needs user attention, return `[SILENT]`"。这是个**host-side** 约定：host 看到回复是字面量 `[SILENT]` 时，应该把这次 run 当无操作处理，不发通知/邮件/IM。

| Host | `[SILENT]` 处理 | 推荐做法 |
|---|---|---|
| **Hermes** | 支持。返回 `[SILENT]` 时 cron run 完成但不送 user-facing notification | 直接按 SKILL.md cron prompt 写 |
| **Claude Code (interactive)** | 不适用——一次只跑一次，输出直接给用户 | cron prompt 段忽略；这套 skill 仍可手动调用 |
| **手写 cron + shell + curl** | host 端不识别；返回的字符串会原样进 stdout | 在 wrapper script 里 `grep -v '^\[SILENT\]$'` 或解析后 short-circuit notification |
| **其他** | 取决于实现；如果 host 把 agent 输出当通知正文，那 `[SILENT]` 会变成噪音 | 包一层「empty-output ⇒ skip notification」的中间层 |

降级方案：如果 host 不支持 `[SILENT]`，agent 仍可按 prompt 返回空字符串或一行 `(nothing to surface)`，host 端用关键字过滤。

## 跑测试

```bash
python3 skills/_lib/tests/test_aha_md.py
python3 skills/idea/tests/test_idea_md.py
python3 skills/dao/tests/test_dao_md.py
python3 skills/daily/tests/test_daily_md.py
python3 skills/reflect/tests/test_reflect_md.py
```

## 通用约定

- 每条记录一个 Markdown 文件；用户原始内容**渲染等价保留**（`## Raw` 永不被工具覆盖；存盘前会做两类最小转义以保护结构边界——见下两条——但 CommonMark 渲染结果与原文一致）。
- workspace 通过 `aha-workspace/.manifest.json` 锚定：CLI 从 cwd 向上找 manifest，找不到则在 cwd 创建一份。manifest 里记录 schema_version / timezone / host_id；TZ 不一致时 stderr 警告。
- 写路径全部走原子 rename（`atomic_write`）+ flock（`locked_record`），cron 与交互式 agent 并发安全；iCloud/Dropbox 同步不易出 conflict 副本。
- `update` / `refine` / `checkin` / `discuss` 拒绝写到 `aha-workspace/<skill>/` 之外的路径。
- 用户原文里的 `## Foo` 在写入时被转义为 `\## Foo`（CommonMark 渲染等同），章节定位是 line-based + fence-aware，不会被 raw text 里的伪标题误导。
- frontmatter 与章节单行的自由文本字段（`--note` / `--decision` / `--difficulty` 等）会把 `\n` 转为 ↵ 标记，防止 row-injection 伪造 `status: dropped` 等。
- 新增 skill 沿用同款骨架：`SKILL.md`，可选 `scripts/`、`tests/`、`references/`；从 `skills/_lib/aha_md.py` 复用所有原语。
- **shell 注入面**：所有接收原始用户文本的子命令（`capture --text`、`task --text`、`log --text`、`refine --text`、`discuss --conversation` 等）都额外提供 `--<name>-stdin` / `--<name>-file` 入口。**agent 在拼 bash 命令时永远走 stdin / file**——把 `$(...)` / 反引号 / 管道字符直接嵌进 `--text "..."` 双引号会被 shell 解释执行。README 的 quick-start 示例为了简洁仍写 `--text "..."`，**仅当文本是静态字面量时使用**。
- **同步工具 conflict 文件被跳过**：reflect / scan / daily review 的 rglob 自动过滤 basename 含 `conflict`（case-insensitive）的文件——Dropbox / Box / 老版 iCloud 在跨设备 race 时会写出 `task-X (laptop's conflicted copy 2026-05-10).md`，这是 sync 副产物不是真实记录。aha-skills 自己的原子 rename + flock 保证不会产生这种文件；如果你看到一个，应该 diff 后手动合并或删除。
- **跨 host 写冲突检测**：`flock` 只在本机有效（NFS / iCloud / Dropbox 不传播）。所有 `update / refine / checkin / discuss` 路径在保存前会对比 mtime——如果文件在 load 与 save 之间被改过（另一台同步过来的写入），CLI 拒绝覆盖并提示 `--force`。这是 best-effort 防御（mtime 解析粒度通常是秒级），不是分布式锁。多 host 共享同一 workspace 时仍建议错峰使用。

