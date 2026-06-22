---
name: webnovel-review
description: 使用审查 Agent 评估章节质量，生成报告并写回审查指标。
allowed-tools: read_text shell_executor write_file edit Agent AskUserQuestion use_skill
argument-hint: "[章号或范围，如 5 或 1-5]"
---

# Quality Review Skill

## 目标

- 解析真实书项目根，调度统一 `file-agent` 完成结构化审查并落库。
- 主链事实以 `.story-system/reviews/chapter_{NNN}.review.json` 与 latest accepted `CHAPTER_COMMIT` 为准；`.webnovel/state.json` 仅为兼容投影。
- 有 `blocking=true` 问题时交用户裁决。

## 红线

- 必须通过 `dispatch_task` 派发给 `file-agent`，禁止主流程伪造结论或口头总结代替 subagent 输出。
- file-agent 只返回严格 JSON；主流程负责用 `shell_executor` + `python -c` 直接覆写到 `{PROJECT_ROOT}/.webnovel/tmp/review_results.json`，随后由 `review-commit` 原子完成报告/指标/投影/日志。
- 报告与 metrics 只由 `review-commit` 产出；主流程不伪造 `overall_score`。
- 项目根不合法 / 缺 `.webnovel/state.json` / 缺待审正文 → 阻断。

## Jwynia 创作技法融合（审查阶段）

> 以下 jwynia 技能由 review 主流程在对应步骤按需 `use_skill` 调用。每次调用产出诊断/指导文本，不落盘。结果作为 file-agent 审查的补充输入。

| Step | 触发条件 | 调用 | 产出 |
|------|---------|------|------|
| Step 5 审查前 | always | `use_skill("prose-critique", task="对本章正文进行对抗性阅读：寻找不奏效的地方，而非确认有效之处")` | 对抗性阅读笔记（薄弱点清单） |
| Step 5 审查前 | always | `use_skill("story-sense", task="诊断本章叙事健康度：节奏/逻辑/情感三个维度")` | 叙事诊断报告 |
| Step 5 审查前 | 章内新增设定或势力 | `use_skill("worldbuilding", task="诊断本章新增设定的合理性：与已有世界观是否兼容")` | 设定兼容性校验 |
| Step 6 review-commit 后 | 审查报告有中高 severity 问题 | `use_skill("revision", task="基于本章审查报告给出结构化修改策略：优先级排序、连锁影响分析")` | 修改策略建议 |
| Step 7 阻断裁决 | 存在 blocking issue | `use_skill("genre-conventions", task="校验本章是否违反题材={genre}的类型红线")` | 类型合规报告 |

> 调用规则：Step 5 的三个 jwynia 诊断必须在 `dispatch_task("file-agent")` 之前完成；file-agent 的审查 prompt 中需包含 jwynia 诊断摘要。

## 流水线文件依赖链

> 每一步的执行必要条件是：上一步的产出文件必须存在。以文件为基准，缺上一步落盘文件直接拒绝执行当前步骤。

| 步骤 | 上一步产出物（本步入口硬校验） | 本步产出物 | 校验方 |
|------|---------------------------|-----------|--------|
| Step 1 | — | 确认 `PROJECT_ROOT` 含 `.webnovel/state.json` | `webnovel.py where` |
| Step 2 | Step 1: `PROJECT_ROOT` 已解析 | runtime contracts | —（条件触发） |
| Step 3 | —（知识加载） | 无文件 | — |
| Step 4 | `.webnovel/state.json` + 章节正文文件 | 确认章节正文存在 | Agent（读文件 / 无则阻断） |
| Step 5 | 章节正文文件 | `prose_check.txt`, `prose_critique.txt`, `story_sense.txt` | Agent（按 step 写盘） |
| Step 6 | Step 5 三份诊断产物 | `review_results.json` | **Agent 前置检查诊断产物** |
| Step 7 | Step 5 诊断 + Step 6 `review_results.json` | 报告/指标/投影/日志 | `_validate_review_results` + `_validate_diagnostics`（脚本硬阻断） |
| Step 8 | Step 7 审查完成 | 用户裁决 | — |

> **硬阻断点**：Step 7（review-commit / review-pipeline）在脚本层强制校验 `review_results.json` 存在+非空 + 三份诊断产物存在+非空。缺任一直接 `sys.exit`，不可能绕过。

## 执行流程

### Step 1：解析项目根

```bash
export PROJECT_ROOT="$(python "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" where)"
```

`PROJECT_ROOT` 必须包含 `.webnovel/state.json`，否则阻断。

### Step 2：目标章缺合同时刷新 runtime 合同

目标章缺 runtime 合同时，先用详细大纲的真实本章目标刷新（`CHAPTER_GOAL` 禁止 `{章纲目标}` / `第N章章纲目标` 占位文本）：

**前置硬校验**：确认 `.webnovel/state.json` 可读。若非 `CHAPTER_GOAL` 占位符但 state.json 损坏或不存在 → 阻断。

```bash
GENRE="$(python -X utf8 -c "import json; s=json.load(open('{PROJECT_ROOT}/.webnovel/state.json',encoding='utf-8')); pi=s.get('project_info',{}); print(pi.get('genre') or s.get('project',{}).get('genre',''))")"

python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" \
  story-system "${CHAPTER_GOAL}" --genre "${GENRE}" --chapter {chapter_num} --persist --emit-runtime-contracts --format both
```

### Step 3：按需加载参考

| Trigger | Reference |
|---------|-----------|
| always | `../../references/shared/core-constraints.md` |
| always | `../../references/review-schema.md` |
| 审查涉及爽点或钩子 | `../../references/shared/cool-points-guide.md` |
| 审查涉及多线交织 | `../../references/shared/strand-weave-pattern.md` |
| blocking issue 需用户裁决 | `../../references/review/blocking-override-guidelines.md` |

### Step 4：加载投影状态与待审正文

**前置硬校验**：先用 `shell_executor` 逐项确认：

```bash
# 1. 状态文件存在
test -f "{PROJECT_ROOT}/.webnovel/state.json" || echo "阻断：state.json 不存在"

# 2. chapter_file 文件存在且非空
test -s "{chapter_file}" || echo "阻断：章节正文文件不存在或为空"
```

任一失败 → 阻断，输出明确原因后终止。

通过后读取状态文件确认当前章节号与对应正文：

```bash
cat "{PROJECT_ROOT}/.webnovel/state.json"
```

确认当前章节号与对应正文文件；缺正文或缺兼容状态文件立即阻断。

### Step 5：prose-check 前置检测（新增）

**前置硬校验**：确认章节正文文件存在且非空（若 Step 4 已通过则自动满足，但 Step 5 独立运行时必须自查）：

```bash
test -s "{chapter_file}" || echo "阻断：章节正文文件不存在或为空（请先完成 Step 4）"
```

通过后执行以下检测。

在审查前运行项目级 prose 检测脚本，扫描已知的 AI 写作反模式。当前覆盖：

| 检测项 | 脚本 | 阈值 | 超阈值处理 |
|--------|------|------|-----------|
| 「不是A，是B」句式密度 | `references/prose_check_not_a_but_b.py` | 6 处/千字 | 告警后纳入审查 issue，建议作者先修复再审查 |

```bash
python -X utf8 "{SKILL_ROOT}/references/prose_check_not_a_but_b.py" "{chapter_file}" --threshold 6
```

- 退出码 0：密度正常，继续审查。
- 退出码 1：密度超标，将检测输出追加到审查 prompt 的补充输入中（不作为独立 issue，而是提醒 reviewer 在 ai_flavor 维度中关注此模式）。
- 脚本不存在则跳过（非阻断）。

> 新增检测项时：在 `references/` 下添加独立脚本 → 在本表中追加一行 → 保持阈值可配置。

**▸ prose-check 产物写盘**：prose-check 的输出必须写入 `{PROJECT_ROOT}/.webnovel/tmp/diagnostics/ch{chapter_num}/prose_check.txt`。

**▸ jwynia 诊断产物写盘**（以下三个必做，缺一则 review-commit 阻断）：

| 诊断 | use_skill | 输出文件 | 条件 |
|------|-----------|----------|------|
| prose-critique | `use_skill("prose-critique", ...)` | `{PROJECT_ROOT}/.webnovel/tmp/diagnostics/ch{chapter_num}/prose_critique.txt` | 必做 |
| story-sense | `use_skill("story-sense", ...)` | `{PROJECT_ROOT}/.webnovel/tmp/diagnostics/ch{chapter_num}/story_sense.txt` | 必做 |
| worldbuilding | `use_skill("worldbuilding", ...)` | `{PROJECT_ROOT}/.webnovel/tmp/diagnostics/ch{chapter_num}/worldbuilding.txt` | 条件：章节内容涉及新设定时触发 |

诊断输出必须用 `shell_executor` + `python -c` 直接覆写到目标文件（不得用 `write_file`，理由同 Step 6）。

### Step 6：调用统一审查（file-agent）

**前置硬校验（Agent 执行，不可跳过）**：调用 `dispatch_task` 之前，先用 `shell_executor` 确认以下三个文件存在且非空：

```bash
ls -l "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/ch{chapter_num}"/{prose_check.txt,prose_critique.txt,story_sense.txt}
```

任一缺失或为空 → **阻断**，拒绝派发 file-agent，提示用户先执行 Step 5。

通过后再执行以下步骤。

必须通过 `dispatch_task` 派发给 `file-agent`。审查方法与维度细则见已加载的参考文件（core-constraints、review-schema）。

调用前准备：
1. 确保 Step 3 中已阅读 `../../references/shared/core-constraints.md` 和 `../../references/review-schema.md`，并记录 memory_ids。
2. 确认本章正文文件路径 `chapter_file`。
3. 若 Step 5 prose-check 超阈值，将检测输出作为审查 prompt 的补充输入。

派发 `dispatch_task(agent_name="file-agent", task="<overall_goal>用户原始需求</overall_goal><current_task>读取正文文件 {chapter_file}，对照上下文中的审查 schema 和核心约束进行全面审查。严格输出 reviewer schema JSON，不评分，不口头总结。</current_task>", memory_ids=[...])`

file-agent 返回后，主流程用 `shell_executor` + `python -c` 把严格 JSON **直接覆写**到 `{PROJECT_ROOT}/.webnovel/tmp/review_results.json`（file-agent 不持 Write，是这份 artifact 的非写入方）。`review-commit` 必须把同一路径覆盖为标准 review_result artifact（含 `blocking_count`）。

> ⚠️ **禁止使用 `write_file`**：`write_file` 遇同名文件会自增后缀，使下游找不到。必须用 `shell_executor` + `python -c` 直接覆写。绝不允许先 `delete` 再 `write_file`。

调用后主流程必须记录 `SubagentRun` 汇总（仅供最终报告使用）：

```json
{
  "name": "file-agent",
  "user_label": "写作检查",
  "status": "completed | partial | failed | skipped",
  "problems": [],
  "auto_handled": [],
  "needs_user_action": false,
  "duration_ms": 0,
  "outputs": []
}
```

file-agent 跳过、失败、输出不完整、正文为空、维度跳过、blocking issue 或耗时异常，必须写入 `problems` / `auto_handled`，不得在最终报告中静默。

### Step 7：原子审查提交（review-commit）⭐

单次调用自动执行：审查报告+指标落库 → 兼容投影写入 → 运行日志 → 最终报告。物理杜绝漏跑。

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" review-commit \
  --chapter {chapter_num} \
  --review-results "{PROJECT_ROOT}/.webnovel/tmp/review_results.json" \
  --metrics-out "{PROJECT_ROOT}/.webnovel/tmp/review_metrics.json" \
  --report-file "审查报告/第{chapter_num}章审查报告.md" \
```

> ⚠️ **默认强制校验**：`review-commit` 和 `review-pipeline` 会自动执行两道校验：
> 1. 检查 `--review-results` 指向的审查结果 JSON 存在且非空（缺则阻断：Step 6 未完成）
> 2. 检查 `{PROJECT_ROOT}/.webnovel/tmp/diagnostics/ch{chapter_num}/` 下 `prose_check.txt`、`prose_critique.txt`、`story_sense.txt` 三个必需产物存在且非空（缺则阻断：Step 5 未完成）
>
> 正常情况下无需任何额外参数即可生效。仅在批处理重算等非审查场景可传 `--skip-diagnostics-check` 豁免（同时跳过两道校验）。

### Step 8：处理阻断

存在任意 `blocking=true` 问题时，用 `AskUserQuestion` 裁决：立即修复 / 仅保存报告稍后处理 / 放弃本次审查。

## 成功标准

1. 已解析真实书项目根。
2. 已通过 `file-agent` 输出结构化问题 JSON，落盘到 `.webnovel/tmp/review_results.json`。
3. `review-commit` 已完成（报告/指标/兼容投影/日志/用户报告全部自动执行）。
4. 存在阻断问题时，用户已明确选择处理策略。

## 作者友好过程提示与恢复契约

审查开始前先说明本次会经历：定位待审正文 -> 刷新缺失合同 -> 写作检查 -> 原子审查提交（报告/指标/投影/日志）。过程提示用作者语言，不直接输出原始 JSON、traceback 或长命令日志；技术详情写入 `.webnovel/logs/run_last.log`（`review-commit` 内部自动记录）。

过程提示每次不超过两行，只说当前动作和影响。少打扰确认策略：无阻断时不询问；存在 blocking issue、缺待审正文、用户要求是否立即修改时才询问。

需要用户裁决时使用有限选项，并说明影响。卡住时必须说明卡点、已完成内容和恢复建议，例如"file-agent 结果已保存，review-commit 失败；重新运行 `/webnovel-review {chapter_num}` 会从原子提交继续"。

不可恢复故障才在最终报告提示 `.webnovel/logs/run_last.log`；平时只保留日志，不打扰作者。`review-commit` 已内置 `user-report`，无需单独调用。

## 作者友好最终报告契约

最终回复必须面向作者，不输出原始 JSON、traceback 或长命令日志。使用固定三段式，并以一句总状态开头：

```text
总状态：已完成 / 部分完成 / 需要你处理 / 未完成。

一、产生的文件与完成情况
- ...

二、过程中遇到的问题与异常耗时
- 已自动处理：...
- 建议确认：...
- 必须处理：...

三、下一步建议
- ...
```

必须汇报：
- 审查报告文件、`.webnovel/tmp/review_results.json`、`.webnovel/tmp/review_metrics.json`。
- 阻断问题数量、用户裁决状态。
- 如果无阻断，明确可以继续写作。

状态规则：
- 有 blocking 问题且用户未选择处理策略时，最终状态为"需要你处理"。
- file-agent 跳过、失败或输出不完整时，最终状态不得写"已完成"。

异常分类：
- 已自动处理：review-commit 自动重试报告/指标/投影落库。
- 建议确认：非阻断但高收益修改建议、命名或设定细节建议看一眼。
- 必须处理：blocking issue、缺待审正文、reviewer 输出不完整、review-commit 失败。

下一步建议必须使用任务化语言 + 可复制命令，例如：

```text
- 审查无阻断，可以继续写下一章：
  /webnovel-write {next_chapter}
```

不写 token 统计；如需排查故障，只给日志路径或建议运行 `/webnovel-doctor`。
