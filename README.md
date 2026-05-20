# aha-skills

一组轻量级 AI agent skill，用于把易逝的认知瞬间留下并持续生长。适配 Claude Code 等支持 SKILL.md 的 host。

---

## 设计哲学

`aha-skills` 不是一个工具集合，而是关于「如何把易逝的认知瞬间留下并持续生长」的分工：

- **idea** — 从灵光一闪的创意想法，到执行落地的实际项目，向外的行动直觉：捕捉 → 孵化 → 决策成行
- **dao** — "道"、"感悟"、"方法论"、"认知"，向内的领悟：记下原话 → 提炼沉淀 → 必要时深谈
- **tip** — "小妙招"、"小技巧"、"邪修方法"，行动上总结的捷径，高效的方法：记录 → 复用 → 如有可能泛化推广
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
| 一个绑定实践域的高效方法 / "小妙招" / "这招好用" | `tip` |
| 有 deadline 的待办 / "今天要做" / "推迟到" / "完成了" | `todo` |

**tip vs dao 判定**：能不能剥离任何具体实践/工具/域还完整说出来？能 → dao；不能 → tip。

## 仓库结构

```
aha-skills/
├── README.md
└── skills/
    ├── idea/SKILL.md
    ├── dao/SKILL.md
    ├── tip/SKILL.md
    └── todo/SKILL.md
```

## 数据存储

所有运行时数据放在 `~/aha-data/`：

```
~/aha-data/
├── idea/   idea-YYYYMMDD-HHMMSS-<slug>.md
├── dao/    dao-YYYYMMDD-HHMMSS-<slug>.md
├── tip/    tip-YYYYMMDD-HHMMSS-<slug>.md
└── todo/   todo-YYYYMMDD-HHMMSS-<slug>.md
```

绑定家目录消除了 cwd 碎片化——认知记录跨项目共享。

## 安装

把 `skills/` 目录（或其中任意子目录）链接/复制到 host 的 skill 加载路径：

- **Claude Code**：`ln -s "$(pwd)/skills/idea" ~/.claude/skills/idea`（每个 skill 独立）
- 无外部依赖，无 Python，无构建步骤
