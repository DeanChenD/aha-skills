# aha-skills

一组轻量级 AI agent skill，用于把易逝的认知瞬间留下并持续生长。

---

## 设计哲学

`aha-skills` 不是一个工具集合，而是关于「如何把易逝的认知瞬间留下并持续生长」的分工：

- **idea** — 从灵光一闪的创意想法，到执行落地的实际项目，向外的行动直觉：捕捉 → 孵化 → 决策成行
- **dao** — "道"、"感悟"、"方法论"、"认知"，向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- **insight** — 对外部现象的解读：记下解读 → agent 给视角 → 必要时深谈
- **tip** — "小妙招"、"小技巧"、"邪修方法"，行动上总结的捷径，高效的方法：记录 → 复用 → 如有可能泛化推广
- **note** — 日常杂项的低摩擦备忘：事实、信息、链接、临时上下文、经历片段，记录 → 补充 → 找回
- **keep** — "我要保持/坚持"的习惯与仪式，向自我的行为承诺：记录 → 修订
- **todo** — 从待办事项，到时候复盘提升，维持节奏：任务（带 due / 状态 / 推迟记录）

## 设计公约

1. **Markdown 是唯一事实源和数据源**。Agent 和人读同一份 `.md`。
2. **来自人的原始输入不可变**。`## Raw` 永远保留用户原话；提炼写在 `## Summary`，旧版进 `## Summary Log`。
3. **Agent 自行读取和编辑 `.md` 文件**。使用已有工具（Read / Edit / Write / Bash），不额外提供脚本。
4. **不强加 workflow**。Agent 适时给出状态建议，用户做决定。

## 设计约束

1. **第一性原理**：所有实现必须服务于核心目标——把易逝的认知瞬间留下并持续生长。
2. **奥卡姆剃刀**：选择能解决当前问题的最简单方案。
3. **YAGNI**：不为假设中的未来需求提前设计。
4. **数据优先于程序**：Markdown 是核心资产，程序脚本只是辅助工具。
5. **透明性优先**：人和 Agent 必须能读懂同一份数据。
6. **Agent 不越权**：Agent 可以建议、提炼、归类、关联。不得擅自覆盖 Raw、删除记录、推进状态、顺延任务。

## 该用哪个 skill

| 用户在说 | 用哪个 skill |
|---|---|
| 一个外部行动方向，需要孵化、研究、决策 / "我有个想法" | `idea` |
| 一个内省式领悟、一句话顿悟 / "我悟到了" | `dao` |
| 对外部现象的解读 / "记录一个洞察" / "记录一个观察" | `insight` |
| 一个绑定实践域的高效方法 / "小妙招" / "这招好用" | `tip` |
| 明确说"记一笔" / "备忘一下" / "随手记"，且不是其他类型的日常杂项 | `note` |
| 一个我决定要保持/坚持的习惯或仪式 / "记下这个仪式" / "我要养成 X" | `keep` |
| 有 deadline 的待办 / "今天要做" / "推迟到" / "完成了" | `todo` |

**tip vs dao 判定**：能不能剥离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。

**insight vs dao 判定**：解读对象是**外部现象** → `insight`；解读对象是**自己/价值观** → `dao`。

**keep vs dao 判定**：是行为承诺还是认知顿悟？「我要每天 X」「我决定保持 Y」是 keep；「我悟到 X」「我相信 X」是 dao。信念归 dao，只有升级为行为承诺才进 keep。

## 仓库结构

```
aha-skills/
├── README.md
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── insight/SKILL.md
    ├── tip/SKILL.md
    ├── note/SKILL.md
    ├── keep/SKILL.md
    └── todo/SKILL.md
```

## 数据存储

所有运行时数据放在 `~/aha-data/`：

```
~/aha-data/
├── idea/    idea-YYYYMMDD-HHMMSS-<slug>.md
├── dao/     dao-YYYYMMDD-HHMMSS-<slug>.md
├── insight/ insight-YYYYMMDD-HHMMSS-<slug>.md
├── tip/     tip-YYYYMMDD-HHMMSS-<slug>.md
├── note/    note-YYYYMMDD-HHMMSS-<slug>.md
├── keep/    keep-YYYYMMDD-HHMMSS-<slug>.md
└── todo/    todo-YYYYMMDD-HHMMSS-<slug>.md
```

绑定家目录消除了 cwd 碎片化——认知记录跨项目共享。
