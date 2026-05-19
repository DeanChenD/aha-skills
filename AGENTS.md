# AGENTS.md

本项目对所有在此目录中工作的 AI agent 的行为公约。**先读完再动手。**

人类视角的项目介绍见 `README.md`;完整设计动机见 `docs/superpowers/specs/2026-05-19-aha-skills-redesign-design.md`。本文件只列必须遵守的规则。

---

## 1. 项目要旨

5 个 skill (`idea` / `dao` / `tip` / `todo` / `reflect`) 用于低摩擦地捕获瞬间认知,让它日后可被检索、提炼、回顾、生长。前 4 个产生记录(JSONL),`reflect` 只读、由 agent 主导穿透它们。**数据是核心,工具附着。**

---

## 2. 设计哲学(铁则,不要协商)

1. **JSONL 是唯一事实源**。一个 skill 一个文件 (`~/aha/<skill>.jsonl`),一行一条 JSON 记录。任何"派生 Markdown / 索引 / 视图"都是临时产物,不要把它们当真。
2. **`raw` 不可变**。用户原话首次写入后永不改写。提炼写到 `refined`,旧 `refined` 入 `refinement_log[]` 归档。
3. **agent 只通过 `skills/_lib/store.py` 改 JSONL**。绝不直接 `open('xxx.jsonl', 'w')`、`sed`、`Edit` 编辑 .jsonl 文件。
4. **不强加 workflow**。agent 提建议,用户做决定。不自动延 due、不自动 promote 跨 skill、不自动归档、不自动状态推进。
5. **小且可拒绝**。新需求先看能不能用现有 verb / refine / log / tag 解决。新增 verb 或 schema 字段是高门槛动作。

---

## 3. 数据公约

| 字段 | 规范 |
|---|---|
| `id` | `YYYY-MM-DD-xxxx` (4 hex chars,`secrets` 生成) |
| `created_at` / `updated_at` | ISO 8601 + 本地 UTC offset |
| 跨 skill 关联 | **仅 tag**,共享命名空间。不要发明 `parent` / `links` / `related_ids` 字段 |
| JSON 输出 | `ensure_ascii=False`(必须支持中文原文)|
| TSV 输出 | 仅给人眼浏览,不可作为机器输入再回流 |

**数据位置**: `$HOME/aha/<skill>.jsonl`,可用 `AHA_HOME=/path/to/dir` 覆盖。

**退出码**: `0` 成功 / `1` 用户错误(参数/未知 id) / `2` 数据/系统错误(损坏/IO/权限)。

---

## 4. 实施约束

- **Python 3.11+,仅 stdlib**(`json` `pathlib` `os` `secrets` `datetime` `fcntl` `argparse` `threading` `contextlib` `sys`)。pytest 仅作为 dev 依赖。
- **macOS / Linux only**(用 `fcntl.flock`)。Windows 是 YAGNI。
- **所有 CRUD 走 `_lib/store.py`**。每个 skill 的 CLI 只是 verb→primitive 的薄编排。
- **写文件必须**:
  - 进 `locked(path)` 上下文(threading.Lock + fcntl.flock 两层,缺一不可——POSIX flock 是 per-OFD,同进程多线程不锁)。
  - 通过 `_atomic_write_lines()`:写到临时文件 → `os.fsync()` → `os.replace()`。**不要**直接 `path.write_text()`。
- **测试纪律**: 每个 verb 一组 pytest;TDD 5 步循环(写失败用例 → 跑确认失败 → 最小实现 → 跑确认通过 → 提交)。提交前 `make test` 必须全绿。

---

## 5. 字段语义铁则

| 规则 | 强制位置 |
|---|---|
| `raw` 不可改写 | 任何 update path 必须保留首版 `raw` |
| `refined` 可覆盖,旧值入 `refinement_log[]` | `store.refine_record()` 已封装 |
| `log[]` 仅追加,不重写不删除 | `store.append_log()`(目前仅 `todo` 用)|
| `status` 是系统中**唯一**枚举,值 `open` / `done` / `dropped`(仅 `todo`)| 不要发明 `paused` / `blocked` / `archived`,把状态描述写进 `log` 笔记 |
| `done_at` **只**在 `status=="done"` 时设置 | `mark_dropped` 不设 `done_at`(字段名要诚实)|
| 其他 skill 的 `status`(如 `idea.status`)是自由文本,**advisory**,不是状态机 | 不要为它加 transition 校验 |

---

## 6. 跨 skill 行为铁则

- **不要**自动 `idea → todo` / `tip → dao` / 任何方向的转换。建议放进对话,等用户开口。
- **`reflect` 严格只读**。绝不调 `add` / `refine` / `log` / `done` / `drop` / `set-due` / `set-status`。
- **"深聊" / 后续讨论 / 多次思考的产物 = 一次 `refine`**,不要发明 "follow-up" / "thread" / "discussion" 之类的新 verb。
- **关联通过 tag**。需要把两条记录"挂起来"时,给它们打同一个 tag,不要写 `linked_to: <id>`。

---

## 7. 加新 skill / 新 verb 时的最小清单

**加新 skill** (高门槛——先确定它和现有 4 个 skill 的边界):
1. `skills/<name>/SKILL.md`(frontmatter + Triggers + Storage + Verbs + Constraints + Examples)
2. `skills/<name>/scripts/<name>.py`(CLI,仅做 argparse → store primitive 编排)
3. `skills/<name>/tests/{conftest.py, test_<name>.py}`
4. 在 `skills/_lib/store.py` 的 `Skill` Literal 与 `SKILLS` tuple 中加上 skill 名(否则 `jsonl_path()` 拒绝)
5. `Makefile` 加一个 target

**加新 verb**:
1. 优先在 `_lib/store.py` 提供 primitive(避免 CLI 自己拼装写路径)
2. 在对应 CLI 加 subparser
3. pytest 覆盖至少:正常路径、未知 id、参数校验失败
4. 同步 SKILL.md 的 Verbs 段

**警惕信号**: 想加 status 枚举 / 想加 link 字段 / 想给 `_lib` 加跨 skill 复合操作 → 多半设计错了,回到第 2 节哲学复核。

---

## 8. 工具与协作

- **绝不**用 `--no-verify` 绕 git hook,绝不在未授权时 `git push --force` / `reset --hard` / 删 branch。
- 提交前必须 `make test` 全过。flaky 测试要么修要么标注,不要默默接受。
- **不要回头修 `docs/superpowers/specs/` 与 `docs/superpowers/plans/` 里的历史 spec/plan**,除非是明确的同步操作(如 2026-05-19 把 `task` 重命名为 `todo` 时,在文档顶部加更名说明、对 spec 全文同步、plan 留migration note)。历史可追溯比表面整洁更重要。
- 用户偏好:跨 AI 多轮独立验证(codex + claude)再下结论;终态变更前先口头说服而非直接动手。

---

## 9. 出错时

- 看到不熟的 `.jsonl` 文件、不熟的 branch、不熟的未提交改动 → **先调查**,不要清理或覆盖,可能是用户在工作中。
- 任何破坏性操作(`rm` / `git reset --hard` / `branch -D` / 改 shared infra)前先口头确认,即便用户之前为类似动作授权过——授权范围不外溢。
- 修 bug 优先找根因,不为绕过断言而 `--no-verify`、不为绕 type check 而 `# type: ignore`。

---

变更本文件本身需要在 PR / commit 中说明动机。本文件不是 wishlist,是合同。
