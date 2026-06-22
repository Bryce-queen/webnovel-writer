---
name: webnovel-learn
description: 从当前会话提取成功写作模式并写入 project_memory.json
allowed-tools: read_text shell_executor use_skill
argument-hint: "[要记住的写作经验]"
---

# /webnovel-learn

## Project Root Guard（必须先确认）

- 必须在项目根目录执行（需存在 `.webnovel/state.json`）
- 用统一入口解析项目根，避免写错目录：

```bash
export PROJECT_ROOT="$(python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" where)"
```

## 目标

提取可复用的写作模式（钩子/节奏/对话/微兑现等），追加到 `.webnovel/project_memory.json`。

## 执行流程

1. 读取 `"$PROJECT_ROOT/.webnovel/state.json"` 的 `progress.current_chapter` 作为当前章节号；缺失则用 `source_chapter: null`，不阻断。
2. 解析用户输入（`/webnovel-learn` 后的经验文本；为空则取本次对话中用户认可的写法），归类 `pattern_type`（hook/pacing/dialogue/payoff/emotion/format/other，无法归类用 `other`）。
3. 调用 `project-memory add-pattern` 写入，不得手写或拼接 JSON：

```bash
python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" project-memory add-pattern \
  --pattern-type "{pattern_type}" \
  --description "{用户输入或提炼后的完整描述}" \
  --category "{分类，可空}" \
  --importance "{high|medium|low}"
```

## Jwynia 模式分析与提炼

> 每次 `add-pattern` 写入后，根据 pattern_type 调用对应 jwynia 技能反向分析「为什么这个模式奏效」，将分析结果追加为 pattern 的 `analysis` 字段，把经验归档升级为结构化创作知识。

| pattern_type | 分析技能 | 调用 |
|-------------|---------|------|
| hook | story-sense | `use_skill("story-sense", task="分析这个钩子模式为何奏效：{pattern_description}")` |
| pacing | scene-sequencing | `use_skill("scene-sequencing", task="分析这个节奏模式为何奏效：{pattern_description}")` |
| dialogue | dialogue | `use_skill("dialogue", task="分析这段对话模式的技法：{pattern_description}")` |
| prose / payoff | prose-style | `use_skill("prose-style", task="分析这个写法模式的文笔特点：{pattern_description}")` |
| worldbuilding / setting | worldbuilding | `use_skill("worldbuilding", task="分析这个世界观设定手法的有效性：{pattern_description}")` |
| emotion | story-sense | `use_skill("story-sense", task="分析这个情感处理模式的叙事效果：{pattern_description}")` |
| format / structure | plot-structure | `use_skill("plot-structure", task="分析这个结构模式的效力：{pattern_description}")` |
| other / 无法归类 | story-sense | `use_skill("story-sense", task="从叙事角度分析这个写作模式为何有效：{pattern_description}")` |

> 调用规则：`add-pattern` 写入成功后立即触发对应 jwynia 分析；分析结果以 `## 技法解析` 追加到 pattern 的 `description` 字段末尾；两次调用（add-pattern → jwynia 分析 → 再次 add-pattern 更新）完成一条知识的完整归档。

## 约束

- 不删除旧记录，仅追加。
- 追加前扫描已有 `patterns`；`pattern_type` + `description` 完全相同则跳过并告知用户，部分相似不去重。
- 禁止使用 `Write` 或手工编辑 `.webnovel/project_memory.json`。

## 成功标准

- `project_memory.json` 存在且格式合法，新 pattern 已追加到 `patterns` 数组。
- 输出包含 `status: success` 和完整 `learned` 对象。

## 失败恢复

| 故障 | 恢复方式 |
|------|---------|
| `project_memory.json` 不存在 | 脚本自动初始化 `{"patterns": []}` 后继续 |
| JSON 解析失败 | 不写入脏数据，告知用户文件损坏并建议手动修复 |
| `state.json` 缺失无法取章节号 | 用 `source_chapter: null`，不阻断 |
