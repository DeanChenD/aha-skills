# idea / dao 讨论协议设计

**Date**: 2026-05-19
**Status**: Awaiting user review
**Author**: 在不破坏 raw-immutable + JSONL 单一事实源 + 现有 `log[]` 原语的前提下,为 idea / dao 启用"可中断、可续聊"的多轮讨论能力。

---

## 1. 背景与动机

aha-skills 的现有契约（见 `2026-05-19-aha-skills-redesign-design.md` 与 `AGENTS.md`）已经覆盖了"用户主动捕捉 + agent 单次建议提炼"的路径。但有一个真实场景没有被显式承载:

> 用户灵光一闪抛出一条 idea → agent 立刻把 raw 记下并提议 refined → 双方开始**多轮发散讨论**,目标是把这条 idea 一步步澄清到可落地方案 / 明确结论。但讨论可能**随时中断**(用户去做别的事、Claude Code 会话被其它任务搅乱)。用户希望**通过 skill 数据本身**(而非 Claude Code transcript)随时从某条 idea 上次聊到的地方再次开始。

约束(不可妥协):
- 不能依赖 Claude Code 的 transcript/会话——会被搅乱、跨设备/跨 agent 用不了
- 上下文必须挂在 idea/dao 这条记录自身上
- 不破 AGENTS.md 既有铁则(尤其 §2.5 加新字段高门槛、§6.3 不发明 thread/discussion verb)

dao 同理但场景更窄:dao 的"深谈"也可能多轮发生(意义溯源、边界澄清、和其它 dao 的关系)。

---

## 2. 不变量(保留)

本次设计**不动**以下内容:

- AGENTS.md §2 全部 5 条设计哲学
- AGENTS.md §3 数据公约(id 格式、时间戳、tag-only 关联、JSON 中文不转义、退出码)
- AGENTS.md §4 实施约束(Python 3.11+ stdlib、locked + atomic write)
- 顶层 JSONL schema:`raw` / `refined` / `refinement_log[]` / `tags[]` / `status` / `created_at` / `updated_at` / `id`
- `log[]` 元素结构 `{at, note}` 不变
- `store.refine_record` / `store.append_log` 等已有 primitive 签名不变
- reflect skill 仍严格只读
- todo 既有用法不变

---

## 3. 第一性原理推演:续聊需要哪些信息?

把"用户一周后回来续聊一条 idea"反向解构成最小信息集。

### 3.1 必备 4 项(已被现有 schema 覆盖)

| 信息 | 字段 |
|---|---|
| 哪条记录 | `id` |
| 灵感原话 | `raw`(不可变) |
| 当前最佳表述 | `refined` |
| 表述的版本演进 | `refinement_log[]` |

### 3.2 真正的难点:"聊到哪了"——5 个维度

| 维度 | 形态 | 用途 | 不记录的后果 |
|---|---|---|---|
| **trail** 已走过的路 | append-only Q&A 流 | 避免重复提问 | agent 像第一次见,把所有问题再问一遍 |
| **decisions** 已达成的小结论 | append-only 共识列表 | 续聊知道哪些已板上钉钉 | 已经想清楚的部分被反复再讨论 |
| **rejected** 已否决的岔路 | append-only 否决+理由 | 不再走过的死路重提 | agent 兴致勃勃推荐已经否过的方向 |
| **focus** 当前讨论焦点 | 最新快照 | 续聊第一句的锚点 | agent 不知从哪下手 |
| **next** 下一步行动 | 最新快照 | 续聊第一个问题 | agent 干瞪眼或乱问 |

### 3.3 关键观察

- trail/decisions/rejected 形态是**历史事实流**——append-only,即便结论日后改变,事实本身值得保留
- focus/next 形态是**最新态**——但它们的**演变**也是认知足迹(参见 `refined` 的设计:当前值好取 + 旧值入 `refinement_log[]`,不丢演变)
- agent 在讨论中可能涌现**其它**值得记录的维度(突发联想、外部参考、情绪/直觉、第三方视角)——schema 化"今天能想到的维度"是过早 commit

### 3.4 结论:全部 5 维度装进 `log[]`,note 保持自由文本

`log[]` 已经是项目内的 append-only note 数组原语(目前限于 todo),其 `{at, note}` 结构正是承载这 5 维度的最小形状。**note 用自由文本而非结构化字段**,既保留 agent 表达柔性,又让 focus/next 的演变天然在流里(读最新一条即得当前态,读全流即得演变)。

零新顶层字段。零新文件类型。零新原语(`log` verb 是已有 `store.append_log` 的薄包装,在 todo 中已使用)。

---

## 4. 设计增量

### 4.1 数据层(零改动)

JSONL schema 一字不变。`log[]` 元素仍是 `{at, note}`,和 todo 的 log 同构。

### 4.2 工具层

**`store.py` 零改动**。`append_log(skill, id, note)` 已存在(`store.py:240-248`),接受任意 `skill` 字符串,无 todo 硬编码。

**idea / dao CLI 各加一个 `log` verb**:

```bash
python skills/idea/scripts/idea.py log <id> <note>
python skills/dao/scripts/dao.py log <id> <note>
```

实现:薄编排,直接调 `store.append_log(skill, id, note)`,输出更新后记录的 JSONL 行。

校验:
- 未知 id → exit 1(`IdNotFound`,store 已抛)
- note 为空字符串 → exit 1(参数校验,与 `idea add` 拒绝空 raw 同精神)

**tip 不开放 log**:tip 是"小战术快捷方式",不发生发散讨论。门槛低,将来真需要再加。

**reflect 不变**:严格只读;读取 idea/dao 的 `log[]` 用于穿透是天然能力,不需新接口。

**不加 `show <id>` 糖**:`list` 默认 JSONL 输出已含全记录(包括 `log[]`),YAGNI。

### 4.3 协议层(写进 idea / dao SKILL.md)

详见第 5 节。这是本次设计的真正重头戏——schema 几乎不动,产品形态由 SKILL.md 里的 Discussion protocol 段落定义。

### 4.4 文档与铁则同步

**AGENTS.md §5 字段语义铁则**——表格中 `log[]` 一行的"目前仅 `todo` 用"括注更新:

```
| `log[]` 仅追加,不重写不删除 | `store.append_log()`,idea / dao / todo 均可用 |
```

**AGENTS.md §6.3**——区分**过程**与**产物**:

旧:
> "深聊" / 后续讨论 / 多次思考的产物 = 一次 `refine`,不要发明 "follow-up" / "thread" / "discussion" 之类的新 verb。

新:
> 多次讨论的**过程**用 `log` 追加;多次讨论后**形成的精炼表述**走一次 `refine`(旧 refined 入 `refinement_log[]`)。不要发明 "follow-up" / "thread" / "discussion" / "session" / "conversation" 之类的新 verb 或字段。

**README.md 不动**——已有"agent suggests refinements"足够,新协议是其细化。

**旧 spec / plan 不动**——按 AGENTS.md §8,不回头改历史 spec/plan;本次新增独立 spec(本文)。

---

## 5. 讨论协议(SKILL.md 中"Discussion protocol"段)

idea 与 dao 共用同一协议;dao 的 SKILL.md 在协议开头加一句小注:**dao 的讨论侧重意义溯源 / 边界澄清,而非 idea 的可落地方案探索**。

### 5.1 入口

不需要新 verb。用户表达即触发:

| 用户表达 | agent 动作 |
|---|---|
| "我有个想法 …" | `idea add` 写 raw 拿到 id;agent 在对话中提议第一版 refined,用户认可后调 `idea refine` 写入 |
| "我想好好聊聊这条" | 进入讨论模式,每轮结束写一条 log |
| "继续聊上次那条 idea X" | 读 `raw + refined + log[]` 重建画面,从最新 log 的 next 起手 |

### 5.2 一轮讨论的形状

- agent 一次问一个澄清问题(不 overload)
- 用户答
- agent 给观点 / 对照 / 建议
- 这一轮稳住后,agent 写一条 log 把本轮浓缩进去

### 5.3 log note 写作守则

note 通常包含 5 维度中**有内容的那几个**(没内容就略):

- **本轮聊了什么**(trail):Q+A 浓缩
- **达成了什么**(decisions):本轮形成的共识
- **否决了什么**(rejected):本轮排除的方向 + 简短理由
- **当前焦点**(focus):现在停在哪个问题上
- **下一步**(next):下次开聊从哪起

**也允许其它**:突发联想、外部参考、情绪/直觉、第三方视角。模板不是审查表,agent 自己判断这一轮值得记什么。

**铁则:数据语法,不是叙事语法**:
- 不用"我"/"你"等人称代词(避免读 log 时的时间错位)
- agent 的提问/综合用 `问:` `焦点:` `下一步:` 等标签
- 用户原话用引号 `""` 包裹保留(呼应 raw 不可变精神)

#### 好的 note 示范

```
本轮:澄清"目标用户是谁"
- 问:脑海里第一个用户画像?答:"团队 lead"
- 问:什么规模的团队?答:10+ 人中大型团队
焦点:这类用户当前用什么工具补这个需求
下一步:先问替代方案——现在怎么解决这个问题
```

#### 反例

```
聊了一些。
```
密度过低,续聊拼不出画面。

```
讨论了用户/市场/商业模式/竞品/技术方案,详细列举:
1. 用户方面...(500 字)
2. 市场方面...(500 字)
...
```
密度过高,续聊要消化大段且混入未确认内容。

### 5.4 续聊触发

用户说"继续聊 idea X" / "接着上次聊"。agent:

1. **找记录**:用户给 id 直接定位;没给则 `idea list` + raw/tag/status 模糊匹配,跟用户确认
2. **读取**:`raw + refined + log[]`,按 `at` 排序
3. **重建画面**:trail 从 log 流提取;focus / next 从最新一条 log 提取
4. **开口**:**用自己的话**起一句,不照念上次的 next(避免机械感)

如果两条 log 之间间隔 > 24h,自然认为是"新一次续聊";不专门记录会话边界。

### 5.5 何时 refine

每轮讨论都写一条 log;**只有 `refined` 的核心命题发生跃迁的轮**才同时调 `refine`。

- 累积几轮后画面变清晰 → agent 提议"我建议把 refined 更新为 X,你觉得?" → 用户同意后 `refine`
- 跃迁性瞬间("其实真问题不是 A 是 B")→ 立刻提议 refine

**log 与 refine 边界**:log 是过程足迹(每轮),refine 是阶段性表述更新(跃迁触发)。

### 5.6 收尾

讨论达成可落地结论时:
- 最后一次 refine 写定终态表述
- agent 提议 `set-status decided`(或 `parked` / `dropped`),用户同意后执行
- 可选:最后一条 log 写"结论:X;为什么:Y;后续动作:Z"

### 5.7 不要做的(呼应 AGENTS.md §2.4 / §6)

- 不要自动把讨论 promote 到 todo(用户说"这个我要做"才转,由用户调 `todo add`)
- 不要在 log 之间发明 thread / session / conversation 的概念
- 不要往 log 元素里塞 focus / next 等结构化字段(保持 `{at, note}` 简单形态)
- 不要替用户做决定——focus / next 是 agent 的建议,refine / set-status 必须用户同意才执行

---

## 6. 测试与验收

### 6.1 测试覆盖(CLI 集成层)

按 AGENTS.md §4.4 TDD 5 步循环逐 case 写。`skills/idea/tests/test_idea.py` 新增(dao 镜像同款):

| 测试 | 断言 |
|---|---|
| `test_log_appends_note` | `add → log → list` 后记录 `log[]` 含一条 `{at, note}` |
| `test_log_multiple_appends_in_order` | log 多次 → `log[]` 按 `at` 升序、append-only |
| `test_log_unknown_id` | `log <unknown_id>` → exit 1 |
| `test_log_empty_note` | `log <id> ""` → exit 1 |
| `test_log_preserves_other_fields` | `add → refine → log` 后 raw / refined / refinement_log / log 全部并存正确 |

`store.py` 层不需新增测试——`append_log` 在 todo 测试里已覆盖,idea/dao 复用同一 primitive。

### 6.2 验收清单(done definition)

- [ ] `make test` 全绿
- [ ] AGENTS.md §5 表格 `log[]` 行、§6.3 已按本 spec §4.4 修订
- [ ] `skills/idea/SKILL.md` 含:Verbs 段加 `log`、新增 Discussion protocol 段(含 log 写作守则 + 好/坏示范)、Examples 加 log 用法
- [ ] `skills/dao/SKILL.md` 同上(开头小注 dao 讨论侧重不同)
- [ ] `skills/idea/scripts/idea.py`、`skills/dao/scripts/dao.py` 各加一个 `log` 子命令(薄编排,调 `store.append_log`)
- [ ] 本 spec 已 commit
- [ ] 手工烟测:跑一段完整流程 `add → refine → log×3 → list`,肉眼读 log[] 能复原讨论画面

### 6.3 不在范围内(YAGNI)

- ❌ 不为 tip 加 log(讨论场景稀薄)
- ❌ 不加 `idea show <id>` / `dao show <id>` 糖(`list` 已够)
- ❌ 不加自动续聊触发(reflect 在穿透时可能主动建议续聊,但不在本次范围;reflect 仍只读)
- ❌ 不在 log 元素加结构化字段(`{at, note}` 不变)
- ❌ 不为讨论会话边界设计字段(log `at` 时间戳间隔可推断)

---

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| agent 写 log 密度低 / 漂移 | SKILL.md 用好/坏示范钉死参考点;柔性指引而非强模板 |
| 单条 idea 讨论几十轮后 jsonl 行膨胀 | `read_all` 一次性读全文件到内存,单行几十 KB 仍 OK;真到几百 KB 再考虑(YAGNI) |
| 用户跨设备 / 换 agent,新 agent 读 log 困惑 | §5.3 "数据语法 / 去人称"守则直接缓解 |
| AGENTS.md §6.3 旧措辞被遗留 agent 缓存 | §4.4 修订显式同步,commit 信息说清楚动机 |

---

## 8. 备选方案与否决理由

讨论过程中评估过的替代设计:

### 8.1 方案 B:伴随 markdown 对话文件(`~/aha/chats/<skill>-<id>.md`)

- 概念:JSONL 不动,每条 idea/dao 配一个 append-only md 文件,逐 turn 写入用户与 agent 原话
- **否决理由**:稀释"JSONL 是唯一事实源",引入新文件类型;agent 直接读写 md 缺 store.py 兜底易破坏;价值密度低(含口水话和未确认内容)

### 8.2 方案 c:log 元素结构升级 `{at, note, focus?, next?}`

- 概念:log 元素内嵌 focus / next 可选字段,显式取当前态,演变天然在流里
- **否决理由**:用户洞察——讨论中可能涌现非 focus/next 的其它维度(突发联想、外部参考、情绪/直觉),结构化字段是"过早 commit 我们今天能想到的维度"。让 note 自由文本最大化 agent 表达柔性

### 8.3 方案 b:顶层 mutable focus / next 字段

- 概念:idea/dao 顶层加 focus + next 两个 mutable string 字段
- **否决理由**:破 AGENTS.md §2.5 加新字段高门槛;且参照 `refined` 的设计,可变状态丢失演变历史是损失认知足迹

### 8.4 完全不增设机制(纯靠 Claude Code transcript)

- **否决理由**:用户明确说 transcript 会被搅乱、跨设备/跨 agent 用不了

---

## 9. 实施步骤

实施步骤由后续 `writing-plans` 阶段产出独立的 plan 文件(`docs/superpowers/plans/2026-05-19-idea-dao-discussion.md`)。本 spec 只定终态。
