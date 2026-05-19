# aha-skills 重构设计

**Date**: 2026-05-19
**Status**: Awaiting user review
**Author**: 重新设计——抛弃现有 Markdown-as-source-of-truth 实现，回归 JSONL 单一事实源

---

## 1. 背景

当前项目（main 分支）以 Markdown 文件作为单条记录的存储格式，配套 ~4000 行 Python 解析/编辑/校验 Markdown。这套实现违背了项目的初衷——绝大部分 Python 代码服务于"维护 Markdown 文件结构"，而非服务于核心目标"低摩擦保存认知，让它未来可检索、可提炼、可复盘、可生长"。

本次重构**完全抛弃**现有代码、SKILL.md、文档、Markdown 模板，回到 JSONL 单一事实源。保留并严格遵循设计哲学、公约、约束。

## 2. 设计哲学（用户指定，已优化）

`aha-skills` 不是工具集合，而是关于"如何把易逝的认知瞬间留下并持续生长"的分工：

- **`idea`** —— 从灵光一闪的创意，到执行落地的项目。向外的行动直觉：捕捉 → 孵化 → 决策成行
- **`dao`** —— 道、感悟、方法论、认知。向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- **`tip`** —— 小妙招、小技巧、行动捷径。记录 → 复用 → 如有可能泛化推广
- **`task`** —— 待办事项 + 时候复盘提升 + 节奏维持：任务、日志、check-in、复盘
- **`reflect`** —— 跨 skill 的模式挖掘：在时间窗口内跨读 idea + dao + tip + task，surface 出共现的 tag、反复出现的困难、跨源主题

## 3. 设计公约

1. **JSONL 是唯一事实源和数据源**。Agent 和人读同一份 `.jsonl`。
2. **来自人的原始输入不可变**。`raw` 永远保留用户原话；提炼写在 `refined`，旧版进 `refinement_log`。这是认知演化的考古层。
3. **Agent 只能通过 Python 脚本编辑 `.jsonl`**。挡住 LLM 自由编辑时的格式漂移。
4. **不强加 workflow**。`dao` 没有状态机，`task` 不自动顺延 due——agent 提建议，用户做决定。

## 4. 设计约束

1. **第一性原理**——所有实现服务于"低摩擦保存人的原始认知，让它未来可检索、可提炼、可复盘、可生长"。说不清服务于此的功能不实现。
2. **奥卡姆剃刀**——优先级 `JSONL + 本地文件 + Python 脚本 > 数据库 > 服务端 > 框架化系统`。不引入非必要依赖、抽象、配置层、构建流程。
3. **YAGNI**——不为假设需求设计。多用户、权限、同步、插件系统暂不实现。
4. **数据优先于应用**——JSONL 是核心资产，脚本是辅助工具。schema 必须稳定、可读、可迁移、向后兼容。
5. **透明性优先**——人和 Agent 必须能读懂同一份数据。所有自动化结果可追溯到原始 `raw`。
6. **Agent 不越权**——Agent 可以建议、提炼、归类、关联、联想、复盘；不得擅自覆盖 `raw`、删除记录、推进状态、顺延任务、强加 workflow。涉及用户判断的动作默认只提议不执行。

---

## 5. 架构总览

```
┌─────────────────────── 用户视角 ──────────────────────┐
│  灵光一闪 → /idea       → ~/aha/idea.jsonl           │
│  内省感悟 → /dao        → ~/aha/dao.jsonl            │
│  小贴士  → /tip         → ~/aha/tip.jsonl            │
│  待办事项 → /task       → ~/aha/task.jsonl           │
│  跨源复盘 → /reflect    → 跨读上述四份,无写入         │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────── Agent 层 ─────────────────────┐
│  每 skill 由一份 SKILL.md 驱动 agent 行为              │
│  Agent 通过 CLI 脚本读写 JSONL,不直接编辑 JSONL 文件   │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────── Python 脚本层 ───────────────────┐
│  skills/<skill>/scripts/<skill>.py     per-skill CLI │
│  skills/_lib/store.py                   shared lib   │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────── 数据层 ────────────────────────┐
│  ~/aha/{idea,dao,tip,task}.jsonl                     │
│  每行 = 一条记录现态;refinement_log 内嵌              │
│  纯本地文件,无数据库无服务器                          │
└──────────────────────────────────────────────────────┘
```

跨层不变量：
- raw 不可变
- Agent 不直写 JSONL
- 无数据库、无服务器、无多用户

---

## 6. 数据层

### 6.1 路径布局

```
~/aha/
├── idea.jsonl
├── dao.jsonl
├── tip.jsonl
└── task.jsonl
```

**路径解析**（`store.aha_home()`）：

```python
def aha_home() -> Path:
    if env := os.environ.get("AHA_HOME"):
        return Path(env).expanduser().resolve()
    try:
        return (Path.home() / "aha").resolve()
    except RuntimeError as e:
        raise RuntimeError(
            "Could not determine home directory. "
            "Set AHA_HOME environment variable."
        ) from e
```

- 默认 `$HOME/aha/`（用 `Path.home()` 而非 shell `~`，跨 shell/agent 上下文都对）
- `AHA_HOME` env var 覆盖默认
- 首次写入时 lazy `mkdir -p` + `touch <skill>.jsonl`

### 6.2 共享核心字段（每条记录都有）

| 字段 | 类型 | 不可变 | 必填 | 说明 |
|---|---|---|---|---|
| `id` | `YYYY-MM-DD-xxxx` (4 hex) | ✓ | ✓ | 写入时生成 |
| `raw` | str | ✓ | ✓ | 用户原话；公约 #2 |
| `tags` | str[] | — | ✓ (默认 `[]`) | 跨 skill 共享命名空间 |
| `created_at` | ISO 8601 + offset | ✓ | ✓ | 写入时刻 |
| `updated_at` | ISO 8601 + offset | — | ✓ | 任何修改触发更新 |

时间戳格式示例：`2026-05-19T15:00:00+08:00`（用 `datetime.now().astimezone()` 自带本地 offset，不需 manifest 存时区）。

### 6.3 per-skill 扩展字段

**idea**：
```json
{
  ...core,
  "status": "incubating",            // free-form string, advisory; 默认 null
  "refined": "提炼后的当前一段话",     // string|null
  "refinement_log": [                 // refined 的旧版归档
    {"at": "2026-05-19T16:30:00+08:00", "prev_refined": "更早一版"}
  ]
}
```

**dao**：
```json
{
  ...core,
  "refined": "...",
  "refinement_log": [...]
}
```

**tip**：
```json
{
  ...core
  // 无额外字段
}
```

**task**：
```json
{
  ...core,
  "due": "2026-05-25",                // ISO date|null
  "status": "open",                    // "open"|"done"|"dropped"
  "done_at": null,                     // ISO ts|null
  "log": [                             // 过程流水,append-only
    {"at": "2026-05-19T15:00:00+08:00", "note": "今天搞了 brainstorming"}
  ],
  "reflection": null                   // string|null,完成或放弃后的事后总结
}
```

### 6.4 字段语义对应表

| skill 阶段 | 字段 |
|---|---|
| 捕捉 | `raw`（每 skill 都有） |
| 提炼 / 决策更新（idea, dao） | `refined` ← 旧版进 `refinement_log` |
| 状态标记（idea） | `status`（free-form） |
| 状态枚举（task） | `status` ∈ {open, done, dropped} |
| 任务过程记录（task） | `log`（append-only） |
| 任务复盘（task） | `reflection` |
| 跨 skill 关联 | `tags`（共享命名空间） |

### 6.5 不变量

| 不变量 | 实现 |
|---|---|
| `raw` 一旦写入永不修改 | store 层无任何函数修改它；测试覆盖 |
| `refined` 修改时旧版必须入 `refinement_log` | `refine_record()` 实现 |
| 首次设置 `refined`（旧值为 null）不入 log | `refine_record()` 检查旧值 |
| `task.log` 只追加 | `append_log()` 仅 append |
| `task.status == "done"` ⟹ `done_at` 非空 | `mark_done()` 同时设两字段 |

### 6.6 id 生成

```python
def new_id() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    suffix = secrets.token_hex(2)  # 4 hex chars, 65536 空间
    return f"{today}-{suffix}"
```

冲突检测：写入前 `find_by_id()`；冲突即重新生成（理论概率 < 0.01% / day @ 100 records/day）。

### 6.7 跨 skill 关联

仅通过 `tags`，命名空间共享。无 `links` / `parent` / `references` 字段（YAGNI）。

reflect 跨读时通过 tag 共现 + agent 在 context 里归纳主题，不在数据层挂关系。

---

## 7. 代码层

### 7.1 文件树

```
skills/
├── _lib/
│   ├── store.py                # ~250 LOC: JSONL CRUD + id + 时间戳 + 锁
│   └── tests/
│       ├── conftest.py
│       └── test_store.py       # ~200 LOC
├── idea/
│   ├── SKILL.md
│   ├── scripts/idea.py         # ~120 LOC: 4 verbs
│   └── tests/
│       ├── conftest.py
│       └── test_idea.py        # ~100 LOC
├── dao/
│   ├── SKILL.md
│   ├── scripts/dao.py          # ~100 LOC: 3 verbs
│   └── tests/test_dao.py       # ~80 LOC
├── tip/
│   ├── SKILL.md
│   ├── scripts/tip.py          # ~80 LOC: 2 verbs
│   └── tests/test_tip.py       # ~60 LOC
├── task/
│   ├── SKILL.md
│   ├── scripts/task.py         # ~150 LOC: 6 verbs
│   └── tests/test_task.py      # ~150 LOC
└── reflect/
    └── SKILL.md                # 仅 SKILL.md,无脚本无测试

scripts/
└── run_tests.py                # 调 pytest 跑 skills/

docs/
└── superpowers/specs/
    └── 2026-05-19-aha-skills-redesign-design.md   # 本文档
```

### 7.2 LOC 预算

| 部分 | 估算 |
|---|---|
| `store.py` (生产) | ~250 |
| 4 个 skill 脚本（生产） | ~450 |
| 测试代码 | ~590 |
| run_tests.py | ~5 |
| **总计** | **~1295** |
| 生产代码（无测试） | **~705** |

约束：生产 LOC ≤ 1050。

### 7.3 `store.py` 公共 API

```python
from typing import Literal, Callable

Skill = Literal["idea", "dao", "tip", "task"]

# === 路径 / 初始化 ===
def aha_home() -> Path
def jsonl_path(skill: Skill) -> Path
def ensure_initialized(skill: Skill) -> None

# === id / 时间戳 ===
def new_id() -> str
def now_iso() -> str

# === 读 ===
def read_all(skill: Skill) -> list[dict]
def find_by_id(skill: Skill, id: str) -> dict | None
def filter_records(records, *, since=None, until=None, tags=None,
                   status=None, due_before=None, limit=None) -> list[dict]

# === 写 ===
def append_record(skill: Skill, record: dict) -> None
def update_record(skill: Skill, id: str, mutator: Callable[[dict], dict]) -> dict

# === 高层操作 ===
def refine_record(skill: Skill, id: str, new_refined: str) -> dict
def append_log(skill: Skill, id: str, note: str) -> dict     # task only
def mark_done(skill: Skill, id: str, reflection: str | None = None) -> dict
def mark_dropped(skill: Skill, id: str, reflection: str | None = None) -> dict

# === 输出格式化 ===
def to_jsonl_line(record: dict) -> str
   # 实现: json.dumps(record, ensure_ascii=False, separators=(",", ":"))
   # ensure_ascii=False 保证中文 raw/refined 不被转义为 \uXXXX
def to_tsv_row(record: dict, columns: list[str]) -> str

# === 异常 ===
class AhaError(Exception): ...
class IdNotFound(AhaError): ...
class CorruptRecord(AhaError): ...

# === CLI 辅助 ===
class AhaArgParser(argparse.ArgumentParser):
    """Override argparse default exit code 2 → 1 for user-facing usage errors."""
```

输入校验由 argparse 完成（`type=` 自定义 parser + `choices=` 枚举），不需要单独异常。

### 7.4 模块边界

- `store.py` **不读 sys.argv，不调用 argparse**——纯函数 + I/O，可单测
- `<skill>.py` **不读写 JSONL**——只 parse args + 调 store + 打印
- 测试分层：
  - `test_store.py` 测全 lib 的不变量、错误、并发
  - `test_<skill>.py` 测 CLI 输出契约和集成路径，不重测 store 已覆盖的不变量

### 7.5 per-skill 脚本结构（统一模板）

每个 `<skill>.py` 长这样：

```python
#!/usr/bin/env python3
"""<skill> CLI."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
import store

SKILL = "<skill>"

def cmd_<verb>(args): ...

def main():
    p = store.AhaArgParser()  # subclass that exits 1 on usage error
    sub = p.add_subparsers(dest="cmd", required=True)
    # 各 verb 注册
    args = p.parse_args()
    try:
        args.fn(args)
    except store.IdNotFound as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except store.CorruptRecord as e:
        print(f"Data error: {e}", file=sys.stderr); sys.exit(2)
    except (OSError, RuntimeError) as e:
        print(f"System error: {e}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
```

### 7.6 Python 版本与依赖

- **Python 3.11+**（用 `Literal`、`X | None` 联合类型语法）
- **生产无外部依赖**（纯 stdlib：`json`, `pathlib`, `os`, `secrets`, `datetime`, `fcntl`, `argparse`, `sys`）
- **dev 唯一依赖**：`pytest`

---

## 8. CLI 形态

### 8.1 调用约定

```bash
python skills/<skill>/scripts/<skill>.py <verb> [args] [flags]
```

- stdout = 数据；stderr = 提示/错误
- exit code: 0 成功；1 用户错（id 不存在、参数非法）；2 系统错（文件 corrupt、IO 失败）

### 8.2 完整动词表（共 15）

```
═══ idea (4) ═══
idea add <raw> [--tag T...] [--status S]
idea list [--status S] [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]
idea refine <id> <new_refined>
idea set-status <id> <status>

═══ dao (3) ═══
dao add <raw> [--tag T...]
dao list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]
dao refine <id> <new_refined>

═══ tip (2) ═══
tip add <raw> [--tag T...]
tip list [--tag T...] [--since DATE] [--until DATE] [--limit N] [--tsv]

═══ task (6) ═══
task add <raw> [--due DATE] [--tag T...]
task list [--status S] [--tag T...] [--since DATE] [--until DATE] [--due-before DATE] [--limit N] [--tsv]
task log <id> <note>
task done <id> [--reflection R]
task drop <id> [--reflection R]
task set-due <id> <date>
```

### 8.3 输出形态

**写入动词**（add / refine / set-status / log / done / drop / set-due）成功后输出**写入后整条记录的 JSON line**：

```bash
$ python skills/idea/scripts/idea.py add "test idea" --tag foo
{"id":"2026-05-19-a3f7","raw":"test idea","tags":["foo"],"created_at":"...","updated_at":"...","status":null,"refined":null,"refinement_log":[]}
```

**list 默认 JSONL**（每行一完整记录）：

```bash
$ python skills/idea/scripts/idea.py list --tag aha-skills
{"id":"2026-05-19-a3f7",...}
{"id":"2026-05-18-7c2a",...}
```

**list `--tsv`**（人浏览）：列固定 `id, raw, refined, status, tags, created_at`，缺失字段显示 `-`，`raw`/`refined` 超 60 字符截断带 `…`：

```
id              raw                            refined                  status      tags          created_at
2026-05-19-a3f7 用 JSONL 替代 Markdown 做事实源  -                       incubating  aha-skills    2026-05-19 15:00
2026-05-18-7c2a 重构 aha-skills                数据是核心,工具附着       decided     aha-skills,重构 2026-05-18 14:32
```

### 8.4 故意不实现的动词（YAGNI）

| 动词 | 不做的理由 |
|---|---|
| `delete <id>` | 违反公约 #2 / #6；真要删用户手编 JSONL |
| `get <id>` | `grep <id> ~/aha/<skill>.jsonl` 一行解决 |
| `tag <id> --add/--remove` | 罕见操作；用户手编或重写记录 |
| `search <text>` | `grep` 已是 search |
| dao `discuss` | 折叠进 `refine`——深谈 = 一次 refined 更新 |
| `idea promote-to-task` | 跨 skill 自动转换违反公约 #4 |
| `task pause / move-due` | `set-due` 覆盖；pause 是状态机 |
| `tip generalize` | 泛化 = 写新 dao，不改 tip |

### 8.5 输入校验规则

- 日期：`YYYY-MM-DD`，否则 exit 1 + 提示
- task `--status`：枚举 `open|done|dropped`，否则 exit 1
- idea `--status`：free-form 字符串，不校验
- `--tag` 可重复给

---

## 9. reflect skill

### 9.1 实现形态

**仅 SKILL.md，无 .py 脚本，无 tests**。

```
skills/reflect/
└── SKILL.md
```

### 9.2 工作机制

reflect 是 agent 主导的剧本：
1. 确定时间窗口（默认 last 14 days；用户可指定）
2. 并行调用四个 skill 的 `list --since YYYY-MM-DD`
3. agent 在 context 里聚合：tag 频次、跨源 tag 共现、task 状态分布、各 skill 时间密度
4. agent 归纳 3-5 条主题，每个挂引用 id
5. agent 给出建议清单（不执行任何动作）

### 9.3 严守约束

- **不调用任何写入动词**
- **不擅自构图**（公约 #5 / #6）：不创建 tag、不挂记录间关系
- **建议归建议**：所有"要不要 ..."标"建议"，等用户回应再触发对应 skill
- **引用回 raw**：任何模式归纳必须 cite ≥1 条原始 id

### 9.4 不做脚本的理由

- 真实工作（读、聚合、综合）全是 agent 已具备的能力
- 写脚本等于把 agent 能力固化进死代码
- 综合质量不可重现是 reflect 的 feature 不是 bug——每次综合视角不同正符合"复盘"本质

---

## 10. 并发与文件锁

### 10.1 风险模型

单用户单机，但可能多 terminal / 多 agent 调用并发。read-modify-write 操作（refine / log / done / set-status）有覆盖丢失风险。

### 10.2 方案

写操作全走 `fcntl.flock(LOCK_EX)` + atomic temp + rename：

```python
@contextmanager
def locked(path: Path):
    path.touch()
    with open(path, "r+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try: yield f
        finally: fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write("\n".join(lines) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atomic on POSIX
```

读不上锁——POSIX 原子 rename 保证 reader 看到旧文件或新文件，无撕裂。

### 10.3 跨平台

- macOS / Linux：`fcntl.flock` 工作
- Windows：YAGNI（用户在 macOS）

### 10.4 死锁防护

- 锁仅在 read-modify-write 期间持有（毫秒级）
- `with` 块自动释放
- 进程崩溃 kernel 自动清

---

## 11. 错误处理

### 11.1 三类错误

| 类 | 来源 | exit code | 用户期望 |
|---|---|---|---|
| 用户错误 | 参数非法、id 不存在、status 取值错 | 1 | 清晰提示该怎么改 |
| 数据错误 | JSONL 文件 corrupt、字段类型错 | 2 | 报具体行号 |
| 系统错误 | 磁盘满、HOME 解析失败、权限不足 | 2 | 报 OS 异常 + 怎么办 |

### 11.2 异常体系

```python
class AhaError(Exception): pass
class IdNotFound(AhaError): ...
class CorruptRecord(AhaError): ...   # 包含 path + line_no + reason
```

**输入校验**：argparse 的 `type=` 自定义 parser + `choices=` 枚举处理参数非法。task `--status` 用 `choices=["open","done","dropped"]`；日期参数用 `type=lambda s: datetime.date.fromisoformat(s)` 强制 `YYYY-MM-DD`。

**argparse 退出码统一**：argparse 默认 `error()` 退 2；为了让用户错误统一在 exit 1（§11.1），每个 `<skill>.py` 子类化 ArgumentParser 覆盖 error()：

```python
class AhaArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"Error: {message}\n")
        self.print_usage(sys.stderr)
        sys.exit(1)
```

### 11.3 数据错误检出

读 JSONL 时每行独立 try/except，遇 `JSONDecodeError` 立刻抛 `CorruptRecord(path, line_no, reason)`。**不容错半读**——半读让 agent 拿错状态。

### 11.4 不做

- 不重试网络/IO
- 不"自动修复" corrupt 行
- 不写错误日志文件（stderr 够用）

---

## 12. 测试策略

### 12.1 框架

- **pytest**（唯一 dev 依赖）
- 不引 mocker / hypothesis / factory_boy

### 12.2 隔离机制

每个测试通过 fixture 拿到独立 `AHA_HOME` tmp 目录：

```python
@pytest.fixture
def aha_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AHA_HOME", str(tmp_path))
    return tmp_path
```

### 12.3 分层

| 测试文件 | 测什么 |
|---|---|
| `test_store.py` | 业务不变量、错误抛出、并发安全 |
| `test_<skill>.py` | CLI 输出契约（JSON shape、TSV 列、exit code） |

reflect 无测试（SKILL.md 不可单测）。

### 12.4 关键不变量测试

```python
def test_raw_is_immutable_after_refine(aha_home): ...
def test_refine_archives_old_to_log(aha_home): ...
def test_first_refine_does_not_log_null(aha_home): ...
def test_log_append_only(aha_home): ...
def test_done_sets_status_and_done_at(aha_home): ...
def test_concurrent_appends_no_loss(aha_home): ...
def test_concurrent_update_no_overwrite(aha_home): ...
def test_corrupt_jsonl_line_reported_with_line_no(aha_home): ...
```

### 12.5 不做

- 不做 property-based testing（YAGNI）
- 不做覆盖率门
- 不在 CI 跑（本地 `make test` 够）
- 不模拟时间（断言"是合法 ISO + 含 offset"即可）

---

## 13. SKILL.md 结构（每 skill 统一骨架）

```markdown
---
name: <skill>
description: <一段精确触发条件,区分本 skill 与其他 4 个;包含中英 trigger 词>
version: 0.1.0
---

# <skill>

<一段:这个 skill 在做什么,在哲学里的位置>

## Triggers

- 中文示例
- English examples
- Slash: /<skill>

## Storage

记录落 `$HOME/aha/<skill>.jsonl`(由 `Path.home() / "aha"` 解析,可由 `AHA_HOME` 覆盖)。每行一条记录。

## Verbs

(每 verb: 调用语法 + 用途 + 输出形态 + 何时用)

## Constraints

- raw 一旦写入不可改
- 不擅自推进状态
- 涉及用户判断默认提议不执行
- (per-skill 特定约束)

## Examples

(2-3 个真实使用例子,中英)
```

reflect 的 SKILL.md 略不同——无 verbs 段，改为 "Approach" 段（见 §9.2）。

---

## 14. 实现起点：清理与重建

### 14.1 删除清单

```
skills/_lib/                    # 1413 LOC Markdown lib
skills/idea/                    # 整个,包括 SKILL.md/scripts/tests
skills/dao/
skills/daily/                   # 整个(被 task 取代)
skills/reflect/                 # 重写
scripts/                        # run_tests.py 重写
aha-workspace/                  # 整个目录,包括 .manifest.json
docs/audit-backlog-2026-05-15.md
README.md
README.en.md
Makefile
```

### 14.2 保留

```
.git/, .gitignore, .claude/     # repo 基础设施
docs/                           # 留壳,新 spec 已在内
```

### 14.3 新建

按 §7.1 文件树创建。所有文件按本 spec 实现。

### 14.4 数据迁移

无现有数据需迁移（`aha-workspace/` 当前仅含 `.manifest.json`，无实际记录）。`~/aha/` 目录由首次写入时 lazy 创建。

---

## 15. 范围之外（YAGNI 列表）

明确不做：

- 多用户、权限、共享
- 多机同步（iCloud / git / Dropbox 同步是用户层的事，与本项目无关）
- 数据库或服务端
- 插件系统、可配置 schema、动态 skill 加载
- 跨记录关联 `links` / `parent` / `children` 字段
- 全文搜索引擎（grep 即 search）
- 自动迁移工具（schema breaking change 时再写）
- Markdown 输出 / 报告生成
- 提醒 / 通知 / 定时任务
- 交互式 prompt / shell 补全
- Web UI / 桌面 UI
- 国际化 / 翻译

---

## 16. 验收标准

实现完成的判定：

1. ✅ 所有路径 `~/aha/*.jsonl` 由 `Path.home() / "aha"` 解析，`AHA_HOME` 覆盖工作
2. ✅ 5 个 skill 的 SKILL.md 写完，trigger 区分明确
3. ✅ 4 个 skill 的 CLI 共 15 verbs 实现并测试
4. ✅ store.py 公共 API 全实现
5. ✅ 生产代码 LOC ≤ 1050
6. ✅ 测试全过：`pytest skills/` 0 失败
7. ✅ §6.5 的 5 条不变量全有测试覆盖
8. ✅ §10 并发场景测试通过
9. ✅ JSONL line 中文 raw / refined 不被转义为 `\uXXXX`（`ensure_ascii=False`）
10. ✅ list 默认 JSONL 输出可被 agent 直接 `json.loads` 解析
11. ✅ 错误退出码符合 §11.1
12. ✅ Makefile / run_tests.py 一行跑全测

---

## 附录 A：决策日志（与本文档主体的对应）

| Q | 决策 | §对应 |
|---|---|---|
| Q1 | JSONL: 单文件 / 每行=记录现态 / refinement 内嵌追加 | §6.1, §6.3 |
| Q2 | Schema: 共享核心 + per-skill 平铺扩展 | §6.2, §6.3 |
| Q3 | `refined`: 字符串(idea/dao 用) | §6.3 |
| Q4 | 脚本入口: per-skill + shared lib, LOC ≤ 1050 | §7 |
| Q5 | 跨 skill: 仅 tags | §6.7 |
| Q6 | 核心字段: id/raw/tags/created_at/updated_at | §6.2 |
| Q6b | per-skill 字段(idea/dao/tip/task) | §6.3 |
| Q7 | id: 日期 + 4 hex | §6.6 |
| Q8 | 路径: `~/aha/`, `AHA_HOME` 覆盖, lazy create | §6.1 |
| Q8b | `Path.home()` 而非 shell `~`(跨 agent 上下文稳定) | §6.1 |
| Q9 | 15 verbs across 4 skills, reflect 无 .py | §8.2, §9 |
| Q9b | list 默认 JSONL, `--tsv` 可选 | §8.3 |
| Q9c | reflect: 仅 SKILL.md | §9 |
| Q10 | 命名: hack → tip | 全文 |
| Q11 | task `check_ins` → `log` | §6.3 |

---

**End of design.**
