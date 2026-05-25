---
name: keep
description: 当用户触发 /keep、声明一个要保持/坚持的习惯或仪式(向自我的行为承诺)、要求修订已有 keep、或翻阅过往 keep 时使用。区别于 dao(向内顿悟/信念,无行为承诺)、tip(必须绑定实践域的捷径)、todo(一次性带 deadline 的任务)。判定规则——是行为承诺还是认知顿悟?「我要每天 X」「我决定保持 Y」「这是我的仪式」是 keep;「我悟到 X」「我相信 X」是 dao。**不要**因为「我觉得 X 重要」「最近想多做 X」等模糊表达自动触发。
---

# Keep — 自我承诺的习惯与仪式

记录"我决定要保持/坚持"的习惯与仪式(向自我的行为承诺),每条一个文件。无状态、无 check-in——agent 不替用户判断"还在坚持吗",只在用户主动修订时更新。

## Triggers(示例,非穷举)

- 中文:「我要保持」「我要坚持」「这是我的仪式」「养成习惯」「我决定每天/每周/每年 X」「记下来:不熬夜」「以后都要 X」
- English: "I commit to", "make this a habit", "my ritual is", "I want to keep doing"
- Slash: `/keep`

### 路由判定

> 是**行为承诺**还是**认知顿悟**?
> - **行为承诺**(「我要每天 X」「我决定保持 Y」「这是我每年的仪式」)→ **keep**
> - **认知顿悟 / 信念**(「我悟到 X」「我相信复利」「慢就是快」)→ **dao**

> 是 ongoing 节奏还是一次性任务?
> - **ongoing 无 deadline** → **keep**
> - **一次性带 deadline**(「这周三前交」「今天要做」)→ **todo**

> 是关乎自我节奏还是关乎实践域?
> - **自我节奏**(「每天读书」「每周复盘」)→ **keep**
> - **绑定具体实践域**(「调试时先去散步」「review 长 PR 先看 test」)→ **tip**

**不**触发:「我觉得 X 重要」「最近想多做 X」「X 挺好的」(模糊偏好,非承诺)。Agent 也**不**主动建议「要不要存成 keep」——除非用户已经表达了承诺意图。

## Storage

```
~/aha-data/keep/
└── keep-YYYYMMDD-HHMMSS-<slug>.md
```

每条 keep 一个文件。首次写入时 Agent 用 `mkdir -p ~/aha-data/keep` 创建目录。

## Markdown Shape

### Frontmatter

```yaml
---
id: keep-YYYYMMDD-HHMMSS-<slug>
created_at: YYYY-MM-DDTHH:MM:SS+08:00
updated_at: YYYY-MM-DDTHH:MM:SS+08:00
---
```

keep 没有 status——没有生命周期状态。中断/重启/放弃由用户自行决定要不要修订 Summary 或新建一条。

### Body

```markdown
# <根据 Raw 提炼的简明标题>

## Raw
<用户原话,永不被覆盖>

## Summary
<最新提炼版;开头用自然语言锚定节奏("每天:..." / "每周日晚:..." / "每年元旦:..." / "不定期:...")>

## Context
<可选:为什么决定要坚持——触发情境 / 动机>

## Summary Log
- YYYY-MM-DD (v1): <旧版 Summary,修订时归档到此>
```

### 示例文件

```markdown
---
id: keep-20260525-220000-laptop-closed-by-eleven
created_at: 2026-05-25T22:00:00+08:00
updated_at: 2026-05-25T22:00:00+08:00
---

# 每晚 11 点前合电脑

## Raw
记下来:以后每天 11 点前必须合上电脑,不管做没做完。

## Summary
每天:晚上 11 点前合上电脑,不以"任务未完成"为例外。把"是否合上"作为硬边界,把"做没做完"留到第二天判断。

## Context
最近连续几周熬到一两点,第二天状态很差,真正高价值的事反而推迟。

## Summary Log
```

## Workflow

### 捕捉

1. 用户**显式**声明一个行为承诺(见 Triggers)
2. Agent 用 Bash 运行 `date +%Y%m%d-%H%M%S` 取时间戳,从原话概括 1-3 个英文小写单词作 slug
3. Agent 用 `mkdir -p ~/aha-data/keep` 后用 Write 创建 `~/aha-data/keep/keep-<TS>-<slug>.md`,把原话原样写进 `## Raw`
4. Agent 立即起草 `## Summary`——**开头用自然语言锚定节奏**("每天:..." / "每周 X:..." / "每年:..." / "不定期:...")
5. 如果触发情境/动机在原话之外被提到,填 `## Context`
6. 完成。不主动追踪、不主动询问是否还在坚持。

### 修订 Summary

当用户说"重新整理一下这个 keep" / "我想改一下" / "这条要调整":
1. Agent 用 Grep/Read 找到该 keep
2. 把当前 `## Summary` 追加到 `## Summary Log`:`- YYYY-MM-DD (vN): <旧内容>`
3. 用新版本覆盖 `## Summary`
4. 更新 frontmatter `updated_at`

### 翻旧

当用户说"翻翻我之前坚持的事" / "回顾一下 keep":
- Agent 用 `ls ~/aha-data/keep/` 或 `grep` 找到记录
- 选一条,读出 `## Summary`
- 提供选项:「要修订?加注?还是放着。」
- 一次只处理一条——回顾是慢的

**不**主动问"这个还在坚持吗"——是否在坚持只有用户能判断。

## Red Flags

| 看到自己想 | 实际是 |
|---|---|
| "用户说'我相信复利'我顺手存进 keep" | 那是认知/信念 → **dao**。提示「听起来更像 dao,要换吗?」 |
| "用户说'今天要早睡'我存进 keep" | 那是一次性任务 → **todo**。提示用户。 |
| "用户说'review 长 PR 先看 test'我存进 keep" | 那是实践域捷径 → **tip**。提示用户。 |
| "Raw 不通顺,帮他改一下" | **永远不动 Raw**。要更清晰就改 Summary |
| "用户只是说'最近想多读书',我顺手建一条" | 模糊偏好不是承诺。必须显式声明才建文件 |
| "加个 status: paused 字段标记暂停" | 结构里没有 status。要表达暂停就修订 Summary 写进去 |
| "用户好久没提这条 keep,我提醒一下" | 不主动 check-in。回顾必须由用户发起 |
| "Summary 写'要坚持读书',不锚节奏" | Summary 开头必须锚定节奏,否则与 dao 难区分 |

## Output Style

每次操作后告诉用户:

- 文件路径
- 一句话:发生了什么变更
- 至多一个具体的下一步建议

Markdown 文件是唯一事实源。
