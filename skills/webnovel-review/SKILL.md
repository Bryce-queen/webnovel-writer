---
name: webnovel-review
description: 使用审查 Agent 评估章节质量，生成报告并写回审查指标。
allowed-tools: read_text shell_executor write_file edit Agent AskUserQuestion
argument-hint: "[章号或范围，如 5 或 1-5]"
---

# Quality Review Skill

## 目标

- 解析真实书项目根，调度统一 `reviewer` 完成结构化审查并落库。
- 主链事实以 `.story-system/reviews/chapter_{NNN}.review.json` 与 latest accepted `CHAPTER_COMMIT` 为准；`.webnovel/state.json` 仅为兼容投影。
- 有 `blocking=true` 问题时交用户裁决。

## 红线

- 必须通过 `Agent` 工具调用 `reviewer`，禁止主流程伪造结论或口头总结代替 subagent 输出。
- reviewer 只返回严格 JSON；主流程负责把返回值写入 `{PROJECT_ROOT}/.webnovel/tmp/review_results.json`，随后由 `review-commit` 原子完成报告/指标/投影/日志。
- 报告与 metrics 只由 `review-commit` 产出；主流程不伪造 `overall_score`。
- 项目根不合法 / 缺 `.webnovel/state.json` / 缺待审正文 → 阻断。

## 执行流程

### Step 1：解析项目根

```bash
export PROJECT_ROOT="$(python "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" where)"
```

`PROJECT_ROOT` 必须包含 `.webnovel/state.json`，否则阻断。

### Step 2：目标章缺合同时刷新 runtime 合同

目标章缺 runtime 合同时，先用详细大纲的真实本章目标刷新（`CHAPTER_GOAL` 禁止 `{章纲目标}` / `第N章章纲目标` 占位文本）：

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

```bash
cat "{PROJECT_ROOT}/.webnovel/state.json"
```

确认当前章节号与对应正文文件；缺正文或缺兼容状态文件立即阻断。

### Step 5：调用统一审查 Agent

必须通过 `Agent` 工具调用 `reviewer`。审查方法与维度细则由 reviewer 自带，本 Skill 不展开。

```text
Use the Agent tool to run `webnovel-writer:reviewer`.

Prompt: chapter={chapter_num}; chapter_file={chapter_file}; project_root={PROJECT_ROOT}; scripts_dir={SKILL_ROOT}/scripts。严格输出 reviewer schema JSON，不评分，不口头总结。
```

reviewer 返回后，主流程把严格 JSON 写入 `{PROJECT_ROOT}/.webnovel/tmp/review_results.json`（reviewer 不持 Write，是这份 artifact 的非写入方）。`review-commit` 必须把同一路径覆盖为标准 review_result artifact（含 `blocking_count`）。

调用后主流程必须记录 `SubagentRun` 汇总（仅供最终报告使用）：

```json
{
  "name": "reviewer",
  "user_label": "写作检查",
  "status": "completed | partial | failed | skipped",
  "problems": [],
  "auto_handled": [],
  "needs_user_action": false,
  "duration_ms": 0,
  "outputs": []
}
```

reviewer 跳过、失败、输出不完整、正文为空、维度跳过、blocking issue 或耗时异常，必须写入 `problems` / `auto_handled`，不得在最终报告中静默。

### Step 6：原子审查提交（review-commit）⭐

单次调用自动执行：审查报告+指标落库 → 兼容投影写入 → 运行日志 → 最终报告。物理杜绝漏跑。

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" review-commit \
  --chapter {chapter_num} \
  --review-results "{PROJECT_ROOT}/.webnovel/tmp/review_results.json" \
  --metrics-out "{PROJECT_ROOT}/.webnovel/tmp/review_metrics.json" \
  --report-file "审查报告/第{chapter_num}章审查报告.md"
```

> ⚠️ **已修复**：v1.0.16 起 `review-commit` 为原子操作，内部依次执行 review-pipeline 报告/指标落库 → update-state 兼容投影 → run-log → user-report 最终报告，调用即全量执行。

### Step 7：处理阻断

存在任意 `blocking=true` 问题时，用 `AskUserQuestion` 裁决：立即修复 / 仅保存报告稍后处理 / 放弃本次审查。

## 成功标准

1. 已解析真实书项目根。
2. 已通过 `reviewer` 输出结构化问题 JSON，落盘到 `.webnovel/tmp/review_results.json`。
3. `review-commit` 已完成（报告/指标/兼容投影/日志/用户报告全部自动执行）。
4. 存在阻断问题时，用户已明确选择处理策略。

## 作者友好过程提示与恢复契约

审查开始前先说明本次会经历：定位待审正文 -> 刷新缺失合同 -> 写作检查 -> 原子审查提交（报告/指标/投影/日志）。过程提示用作者语言，不直接输出原始 JSON、traceback 或长命令日志；技术详情写入 `.webnovel/logs/run_last.log`（`review-commit` 内部自动记录）。

过程提示每次不超过两行，只说当前动作和影响。少打扰确认策略：无阻断时不询问；存在 blocking issue、缺待审正文、用户要求是否立即修改时才询问。

需要用户裁决时使用有限选项，并说明影响。卡住时必须说明卡点、已完成内容和恢复建议，例如"reviewer 结果已保存，review-commit 失败；重新运行 `/webnovel-review {chapter_num}` 会从原子提交继续"。

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
- reviewer 跳过、失败或输出不完整时，最终状态不得写"已完成"。

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
