---
name: webnovel-write
description: 产出可发布章节，完整执行上下文→起草→审查→润色→提交→备份。
allowed-tools: read_text write_file edit shell_executor Agent AskUserQuestion use_skill
argument-hint: "[章号] [--fast|--minimal]"
---

# 写章流程

## 目标

产出可发布章节到 `正文/第{NNNN}章-{title}.md`。默认 2000-2500 字，用户/大纲另有要求时从之。

## 模式

| 模式 | 流程 |
|------|------|
| 默认 | Step 1→2→3→4→5→6 |
| `--fast` | Step 1→2→3(轻量)→4→5→6 |
| `--minimal` | Step 1→2→3(写 no-review artifact)→4(仅排版)→5→6 |

## 硬规则

- 禁止并步、跳步、伪造审查
- 必须使用 `dispatch_task` 派发给 `file-agent`；不得用主流程口头代替 subagent 输出
- 审查只跑一轮；blocking issue 定点修复或经用户裁决后才进 Step 4/5
- 失败只补跑失败步骤，不回退
- 参考资料按步骤按需加载

## 优先级

用户要求 > 状态机硬门槛 > 项目约束（总纲/设定/记忆）> skill 流程 > reference 建议

## CSV 检索（Step 2 按需）

```bash
python -X utf8 "{SKILL_ROOT}/scripts/reference_search.py" --skill write --table {表名} --query "{关键词}" --genre {题材}
```

触发条件：新角色→命名规则，战斗→场景写法，多角色对话→写作技法，情感描写→写作技法，高频桥段→场景写法。

## 强制脚本调用清单（每次写章必须逐条执行，禁止跳过）

> 执行本 skill 时，你必须在下表中逐条打勾。未完成当前步骤不得进入下一步。
> 不读此表、凭记忆跳步执行是本 skill 已知最高频故障模式。

| # | 步骤 | 命令 / dispatch_task 调用 | 打勾 |
|---|------|------------------|------|
| 0 | 预检 | `webnovel.py preflight` + `placeholder-scan` | [ ] |
| 0 | 刷新合同 | `story-system ...` + `write-gate --stage prewrite` | [ ] |
| 1 | 生成任务书 | `dispatch_task` → file-agent | [ ] |
| 2 | 起草正文 | 主流程直接写 | [ ] |
| 3 | 审查 | `dispatch_task` → file-agent → 返回 JSON | [ ] |
| 4 | 润色 | 修复 issue + 排版 + Anti-AI 终检 | [ ] |
| 5a | 提取事实 | `dispatch_task` → file-agent → 三份 JSON | [ ] |
| 5b | Git diff | `git diff --name-status -- .` | [ ] |
| 5c | 原子提交 ⭐ | `chapter-commit ...`（内置 预检→评分→提交→投影→后检→日志→备份→最终报告，7 步打包执行） | [ ] |
| 5d | 补投影 | `projections retry`（仅失败时） | [ ] |
| 6 | 备份 | ✅ 已由 chapter-commit 覆盖 | [ ] |
| R | 最终报告 | ✅ 已由 chapter-commit 覆盖 | [ ] |

> ⚠️ **已修复**：v1.0.15 起 `chapter-commit` 为原子操作，内部依次执行 write-gate precommit → review-pipeline 评分落库 → 提交 → 投影 → write-gate postcommit → run-log → backup → user-report，调用即全量执行，物理杜绝漏跑。Step 6 和 R 由 atomic chain 自动覆盖，无需单独调用。

## Jwynia 创作技法融合（写章阶段）

> 以下 jwynia 技能由 write 主流程在对应步骤按需 `use_skill` 调用。每次调用产出诊断/指导文本，不落盘。

| # | 步骤 | 触发条件 | 调用 | 产出 |
|---|------|---------|------|------|
| 2a | 起草前诊断 | always | `use_skill("story-sense", task="诊断本章（第{chapter_num}章）写作任务书中的叙事健康度：检查 CBN→CPNs→CEN 链条是否完整、章末钩子是否自然")` | 叙事弱点清单，起草时规避 |
| 4a | 润色-对话 | 正文含对话场景 | `use_skill("dialogue", task="诊断本章对话：是否所有角色声音一致、是否有潜台词层、是否有功能性对话")` | 对话修复清单 |
| 4b | 润色-文笔 | always（`--minimal` 跳过） | `use_skill("prose-style", task="诊断本章文笔：句子节奏单调点、用词重复、语态问题")` | 文笔修复清单 |
| 4c | 场景节奏 | 章内场景数≥3 | `use_skill("scene-sequencing", task="诊断本章场景节奏：是否有缺 Sequel 的场景、场景转换是否机械")` | 节奏调整建议 |

> 调用规则：每个 jwynia 调用必须先于相应润色子步骤执行；诊断结果作为润色的输入清单；`--minimal` 模式下跳过所有 jwynia 诊断。

## 流水线文件依赖链

> 每一步的执行必要条件是：上一步的产出文件必须存在。以文件为基准，缺上一步落盘文件直接拒绝执行当前步骤。

| 步骤 | 入口硬校验（上一步产出物） | 本步产出物 | 校验方 |
|------|--------------------------|-----------|--------|
| 准备:预检 | — | `PROJECT_ROOT` 解析 | `webnovel.py preflight` |
| 准备:刷新合同 | `.webnovel/state.json` | runtime contracts + `MASTER_SETTING.json`/`volume_NNN.json`/`chapter_NNN.review.json`（必备，缺则阻断） | 脚本内校验 |
| Step 1 | 合同文件（准备产出） | 写作任务书 | Agent |
| Step 2 | 写作任务书（Step 1 产出） | 章节正文 `CHAPTER_FILE` | Agent |
| **Step 3** | **章节正文** `CHAPTER_FILE`（Step 2 产出） | `review_results.json` + `review_metrics.json` + 审查报告 | **Agent: `test -s CHAPTER_FILE`** |
| **Step 4** | **`review_results.json`**（Step 3 产出） | 润色后章正文 | **Agent: `test -s review_results.json`** |
| **Step 5.1** | **`review_results.json` + `CHAPTER_FILE`**（Step 3+2 产出） | `fulfillment_result.json` / `disambiguation_result.json` / `extraction_result.json` | **Agent: `test -s` 两份文件** |
| Step 5.2 | Step 3+5.1 全部产出 | chapter-commit（原子操作，内含 write-gate precommit 门控） | `chapter-commit` 脚本 |
| Step 5.3 | Step 5.2 提交成功 | 投影写入 | `write-gate --stage postcommit` |

> **Agent 阻断点（粗体行）**：Step 3 和 Step 5.1 在派发 file-agent 前，Agent 必须执行 `test -s` 校验上一步落盘文件存在且非空。不通过则拒绝派发，提示用户先完成上一步。
> **脚本阻断点**：`review-pipeline`（Step 3 内）已内置 `_validate_review_results` + `_validate_diagnostics` 两道硬校验。`chapter-commit` 内置 write-gate precommit 门控。

## 执行流程

### 准备：预检

```bash
export WORKSPACE_ROOT="{PROJECT_ROOT}"
export SCRIPTS_DIR="{SKILL_ROOT}/scripts"
export SKILL_ROOT="{SKILL_ROOT}/skills/webnovel-write"

python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight
export PROJECT_ROOT="$(python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"

python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" placeholder-scan --format text
```

### 准备：刷新合同树

genre 从 `.webnovel/state.json` 的初始化配置快照读取，用于刷新合同树；写前主链真源仍是 `.story-system/` 合同。调用 story-system 前必须先从详细大纲解析真实本章目标，禁止传 `{章纲目标}`、`第N章章纲目标` 等占位 query。

```bash
GENRE="$(python -X utf8 -c "import json,sys; s=json.load(open('{PROJECT_ROOT}/.webnovel/state.json',encoding='utf-8')); pi=s.get('project_info',{}); print(pi.get('genre') or s.get('project',{}).get('genre',''))")"

python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" \
  story-system "${CHAPTER_GOAL}" --genre "${GENRE}" --chapter {chapter_num} --persist --emit-runtime-contracts --format both

python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" \
  write-gate --chapter {chapter_num} --stage prewrite --format json
```

必备文件：`MASTER_SETTING.json`（调性/禁忌）、`volume_{NNN}.json`（卷级节奏）、`chapter_{NNN}.review.json`（必须节点/禁区）。缺失则阻断。

`chapter_{NNN}.json` 必须优先检查顶层 `chapter_directive`。`chapter_focus` 只能来自 `chapter_directive.goal` 或真实 query，不得从 `dynamic_context` 的参考摘要继承。

写作任务书排序必须固定为：
1. 本章硬性约束：`chapter_directive.goal/time_anchor/chapter_span/countdown/chapter_end_open_question`
2. CBN/CPNs/CEN 与 `must_cover_nodes`
3. 本章禁区：`forbidden_zones`，违反即不通过
4. 风格指引：reasoning、主角卡 OOC 警戒、anti_patterns
5. 场景写法补充：`dynamic_context`，仅作风格参考，不能覆盖章纲约束

### Step 1：file-agent 生成写作任务书

必须使用 `dispatch_task` 派发给 `file-agent`，不得由主流程自行整理任务书。

调用前准备：
1. 先阅读以下参考文件并记录 memory_ids：
   - `{SKILL_ROOT}/references/shared/core-constraints.md`（核心约束）
   - `{SKILL_ROOT}/references/shared/cool-points-guide.md`（爽点指引）
   - `{PROJECT_ROOT}/.webnovel/state.json`（项目状态）
2. 运行 `extract_chapter_context.py` 获取本章上下文数据，记录 memory_id。

派发 `dispatch_task(agent_name="file-agent", task="<overall_goal>用户原始需求</overall_goal><current_task>读取 {PROJECT_ROOT} 项目第 {chapter_num} 章的相关文件（章纲、前章摘要、设定集、合同文件），结合上下文中的核心约束和写作指引，生成一份五段写作任务书，按以下顺序组织：1)本章硬性约束 2)CBN/CPNs/CEN与must_cover_nodes 3)本章禁区 4)风格指引 5)dynamic_context补充参考。上下文不足时返回 blocker 说明。</current_task>", memory_ids=[...])`

产物：一份写作任务书文本，能独立支撑 Step 2 起草。用于向用户展示并进入下一步。

调用后主流程必须记录 `SubagentRun` 汇总（仅供最终报告使用）：

```json
{
  "name": "file-agent",
  "user_label": "整理写作依据",
  "status": "completed | partial | failed | skipped",
  "problems": [],
  "auto_handled": [],
  "needs_user_action": false,
  "duration_ms": 0,
  "outputs": []
}
```

上下文不足、legacy fallback、伏笔数据缺失、任务书不完整或耗时异常，必须写入 `problems` / `auto_handled`，不得在最终报告中静默。

### Step 2：起草正文

只根据任务书起草。不加载 core-constraints/anti-ai-guide（已内化到任务书）。只输出纯正文，无占位符。有结构化节点时围绕 CBN→CPNs→CEN 展开。中文思维写作。

### Step 3：审查

**前置硬校验（Agent 执行，不可跳过）**：调用 `dispatch_task` 之前，先用 `shell_executor` 确认章节正文存在且非空：

```bash
test -s "{CHAPTER_FILE}" || echo "阻断：章节正文文件不存在或为空（请先完成 Step 2 起草）"
```

不通过 → **阻断**，拒绝派发 file-agent。

必须使用 `dispatch_task` 派发给 `file-agent`，不得由主流程伪造审查 JSON。

调用前准备：
1. 先阅读审查规则文件并记录 memory_ids：
   - `{SKILL_ROOT}/references/shared/core-constraints.md`（核心约束）
   - `{SKILL_ROOT}/references/review-schema.md`（审查 schema 定义）
   - `{SKILL_ROOT}/references/shared/cool-points-guide.md`（爽点指引，如涉及）
2. 确认本章正文文件路径 `CHAPTER_FILE`。

派发 `dispatch_task(agent_name="file-agent", task="<overall_goal>用户原始需求</overall_goal><current_task>读取正文文件 {CHAPTER_FILE}，对照上下文中的审查 schema 和核心约束进行全面审查。只返回严格的 JSON，格式参照 review-schema.md 定义，包含 chapter/blocking_count/issues 等字段。不写任何文件，不评分，不口头总结。</current_task>", memory_ids=[...])`

file-agent 只返回 JSON；主流程负责用 `shell_executor` + `python -c` 把返回的 JSON **直接覆写**到 `{PROJECT_ROOT}/.webnovel/tmp/review_results.json`（file-agent 不持 Write，是这份 artifact 的非写入方）。随后必须运行 review-pipeline；review-pipeline 会把同一路径覆盖为标准 review_result artifact（含 `blocking_count`），供 precommit gate 与后续提交命令使用。

> ⚠️ **禁止使用 `write_file` 写入 temp 文件**：`write_file` 遇同名文件会自增后缀（如 `review_results_20260620.json`），导致下游按固定路径找不到 artifact。必须用 `shell_executor` + `python -c` 直接覆写，例如：
> ```bash
> python -c "import json; from pathlib import Path; p=Path('{PROJECT_ROOT}/.webnovel/tmp/review_results.json'); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps({...file-agent返回的JSON...},ensure_ascii=False,indent=2),encoding='utf-8')"
> ```
> 绝不允许先 `delete` 再 `write_file`。

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

file-agent 跳过、失败、输出不完整、`--minimal` 写 no-review artifact、blocking issue、维度跳过或耗时异常，必须写入 `problems` / `auto_handled`，不得在最终报告中静默。

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" review-pipeline \
  --chapter {chapter_num} \
  --review-results "{PROJECT_ROOT}/.webnovel/tmp/review_results.json" \
  --metrics-out "{PROJECT_ROOT}/.webnovel/tmp/review_metrics.json" \
  --report-file "审查报告/第{chapter_num}章审查报告.md" \
  --save-metrics
```

审查只跑一轮，file-agent 只调用一次。`blocking=true` 的问题在不改剧情、不破设定的前提下定点修复后直接进 Step 4，不重新调用 file-agent；确实无法修复的 blocking 问题用 `AskUserQuestion` 让用户裁决（接受当前版本 / 手动修复 / 放弃）。非 blocking issue 交给 Step 4 处理。`--fast` 只检查 setting/timeline/continuity。

`--minimal` 不调用 file-agent 与 `review-pipeline`，但必须**覆盖写入**本章新的 no-review `review_results.json`（禁止复用旧 artifact），使 Step 5 提交链有有效 `--review-result`（成功标准“审查已落库”对 `--minimal` 的豁免仍成立）：

```bash
python -X utf8 -c "import json,os; from pathlib import Path; root=Path(os.environ['PROJECT_ROOT']); ch=int('{chapter_num}'); p=root/'.webnovel'/'tmp'/'review_results.json'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps({'chapter':ch,'issues':[],'issues_count':0,'blocking_count':0,'has_blocking':False,'summary':'minimal mode: file-agent skipped by user-selected --minimal flow','review_skipped':True,'review_mode':'minimal'},ensure_ascii=False,indent=2),encoding='utf-8')"
```

### Step 4：润色

**前置硬校验**：确认审查结果存在（`--minimal` 模式下跳过）：

```bash
test -s "{PROJECT_ROOT}/.webnovel/tmp/review_results.json" || echo "阻断：review_results.json 不存在或为空（请先完成 Step 3 审查）"
```

不通过 → **阻断**，拒绝润色（`--minimal` 模式下跳过此校验）。

`references/polish-guide.md` 区段读：先用 `shell_executor` grep 匹配 `^#{1,3} ` 定位锚点行号，再 `read_text` 的 offset/limit 取段——主路径取 `## 2. 执行顺序（必须按序）`；Anti-AI 终检单独区段取 `## 2A. Anti-AI 检测细则` 与 `## Phase 1 增补：Anti-AI 规范（7层，原版）`（词库段），不全文读。`references/writing/typesetting.md`、`references/style-adapter.md` 短文件，全文 `read_text`。

顺序：修复非 blocking issue → 风格适配 → 排版 → Anti-AI 终检。

只改表达不改事实。`anti_ai_force_check=fail` 时不进 Step 5。`--minimal` 仅排版。

> **Marvis 说明**：本 skill 中提到的工具名对应 Marvis 运行时：`read_text`（读文件）、`write_file`（写文件）、`shell_executor`（执行命令，替代 Bash/Grep）、Agent（子代理，替代 Claude Code Agent）。

### Step 5：提交

#### 5.1 file-agent 提取事实

**前置硬校验（Agent 执行，不可跳过）**：调用 `dispatch_task` 之前，先用 `shell_executor` 确认审查结果和正文存在：

```bash
test -s "{PROJECT_ROOT}/.webnovel/tmp/review_results.json" || echo "阻断：review_results.json 不存在或为空（请先完成 Step 3 审查）"
test -s "{CHAPTER_FILE}" || echo "阻断：章节正文文件不存在或为空（请先完成 Step 2 起草）"
```

任一不通过 → **阻断**，拒绝派发 file-agent。

必须使用 `dispatch_task` 派发给 `file-agent`，产出 fulfillment_result / disambiguation_result / extraction_result 三份 JSON，并复用 Step 3 的 review_results。

调用前准备：
1. 确认本章正文文件路径 `CHAPTER_FILE`、review_results 路径、output_dir 路径。
2. 将 Step 3 审查结果 review_results 的 memory_id 传入。

派发 `dispatch_task(agent_name="file-agent", task="<overall_goal>用户原始需求</overall_goal><current_task>读取正文文件 {CHAPTER_FILE} 和审查结果 {PROJECT_ROOT}/.webnovel/tmp/review_results.json，提取本章事实产出三份 JSON artifact 到 {PROJECT_ROOT}/.webnovel/tmp/：①fulfillment_result.json（章纲履行情况）②disambiguation_result.json（消歧结果）③extraction_result.json（本章新增实体/关系/伏笔提取）。你是这三份 artifact 的唯一产出者；不直接写 state/index/summaries/memory/vectors/projection。</current_task>", memory_ids=[...])`

⚠️ 主流程必须用 `shell_executor` + `python -c` 将 file-agent 返回的 JSON 写入 output_dir 下的对应文件（直接覆写），禁止用 `write_file`（会自增后缀导致 chapter-commit 找不到文件）。禁止先 `delete` 再写入。

artifact 字段 schema 由 file-agent 自身定义、runtime validator 校验；主流程只检查文件存在与 schema，不重写、不补写、不口头替代。

调用后主流程必须记录 `SubagentRun` 汇总（仅供最终报告使用）：

```json
{
  "name": "file-agent",
  "user_label": "保存本章故事事实",
  "status": "completed | partial | failed | skipped",
  "problems": [],
  "auto_handled": [],
  "needs_user_action": false,
  "duration_ms": 0,
  "outputs": []
}
```

三份 artifact 写入状态、schema 不合格、pending 消歧、长时间无进展或输出不完整，必须写入 `problems`；自动重跑或降级处理必须写入 `auto_handled`。

#### 5.2 提交前校验与 CHAPTER_COMMIT

先跑 precommit gate：

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" \
  write-gate --chapter {chapter_num} --stage precommit --format json
```

precommit 通过后，运行提交前只读 `git diff` 变更面校验（写入所有权 sanity check，只读、不 stage、不提交）：

```bash
if git -C "{PROJECT_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "{PROJECT_ROOT}" diff --name-status -- .
  git -C "{PROJECT_ROOT}" diff --check -- .
fi
```

变更面不得出现插件目录、其他书项目、其他章节正文或不属于本章流程的手写状态文件；`git diff` 只覆盖 git 可见文件，SQLite / `.webnovel/` 内部语义由 5.3 postcommit 与 runtime 只读查询验证。若项目根不是 git worktree，记录“跳过 git diff 校验”，不得因此跳过 precommit gate。本步只读，禁止在此执行 `git add`/`git commit`。

校验通过后运行 chapter-commit：

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" chapter-commit \
  --chapter {chapter_num} \
  --review-result "{PROJECT_ROOT}/.webnovel/tmp/review_results.json" \
  --fulfillment-result "{PROJECT_ROOT}/.webnovel/tmp/fulfillment_result.json" \
  --disambiguation-result "{PROJECT_ROOT}/.webnovel/tmp/disambiguation_result.json" \
  --extraction-result "{PROJECT_ROOT}/.webnovel/tmp/extraction_result.json"
```

自动判定：blocking_count>0 或 missed_nodes 非空 或 pending 非空 → rejected，否则 accepted。

#### 5.3 验证投影

projection_status 五项（state/index/summary/memory/vector）全部 done 或 skipped。

chapter_status 由 projection writer 自动推进：accepted→committed，rejected→rejected。

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" \
  write-gate --chapter {chapter_num} --stage postcommit --format json
```

#### 5.4 失败隔离

commit 未生成→重跑 5.2。projection 失败→只补跑 projection，不回退 Step 1-4。

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" \
  projections retry --chapter {chapter_num} --format json
```

### Step 6：Git 备份 ✅ 已由 chapter-commit 覆盖

`chapter-commit` 已内置 `GitBackupManager.backup(chapter, title)`，无需单独调用。

## 作者友好过程提示与恢复契约

开始写章前先用作者语言说明本次目标、主要阶段和是否需要守在旁边，不承诺固定耗时。过程提示只说当前在做什么和会产生什么，不直接输出原始 JSON、traceback 或长命令日志；技术详情写入 `.webnovel/logs/run_last.log`：

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" run-log \
  --event write-start \
  --payload-json "{\"chapter\": {chapter_num}, \"mode\": \"{mode}\"}" \
  --format text
```

写章过程节点（最多 6 个）：

1. 检查项目环境：确认项目、占位符和本章要求可用。
2. 整理写作依据：读取章纲、最近剧情和未回收伏笔。
3. 起草正文：根据写作任务书生成本章正文。
4. 写作检查：审查阻断问题和高收益修改建议。
5. 保存本章故事事实：提取本章目标完成情况、歧义和新事实。
6. 提交备份：把本章事实入账、更新故事资料并备份。

重复执行同一章时，先读取可信断点：

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" run-ledger write-resume \
  --chapter {chapter_num} \
  --mode "{mode}" \
  --format json
```

`run-ledger write-resume` 只给续跑建议，不自动覆盖文件。它会根据正文、审查结果、data artifacts、commit、projection 和备份状态判断从哪里继续。正文被手动改过、章纲更新晚于正文、本章已 accepted 又重跑时，必须停下用有限选项询问：沿用当前正文 / 重新起草 / 只查看状态；不得覆盖作者手改。

每个关键步骤完成后记录 `run-ledger record-write-step`，至少记录 step、status、输入/输出文件路径、problems、auto_handled 和 duration_ms，供下一次续跑和最终报告使用。

少打扰确认策略：默认继续推进；只有创作方向、事实一致性、文件覆盖风险或 blocking issue 无法定点处理时才问。需要用户裁决时给 2-3 个有限选项，并说明每个选项影响。

卡住时必须说明卡点、已完成内容和恢复建议：例如“正文和审查报告已保留，保存本章故事事实失败；重新运行 `/webnovel-write {chapter_num}` 会从 file-agent 继续”。不可恢复故障才在最终报告提示 `.webnovel/logs/run_last.log`；平时只保留日志，不打扰作者。

收尾报告已由 `chapter-commit` 自动生成（`build_user_report` → `format_user_report`），章节 payload 中包含 `_user_report` 字段。主流程直接读取该字段组织最终回复，无需单独调用 `user-report`。

## 充分性闸门

1. 正文文件存在且非空
2. 审查已落库（`--minimal` 除外）
3. blocking=true 必须在 Step 3 定点修复或经用户裁决
4. anti_ai_force_check=pass（`--minimal` 除外）
5. accepted CHAPTER_COMMIT，projection 五项 done/skipped
6. chapter_status=committed（projection 自动推进）
7. `write-gate` 的 prewrite / precommit / postcommit 均通过

## 失败恢复

审查缺失→重跑 Step 3。摘要/状态/记忆缺失→重跑 Step 5。润色失真→回 Step 4 修复后重跑 Step 5。

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
- 正文文件路径。
- 审查报告路径。
- `.webnovel/tmp/review_results.json`。
- `.webnovel/tmp/fulfillment_result.json`。
- `.webnovel/tmp/disambiguation_result.json`。
- `.webnovel/tmp/extraction_result.json`。
- `.story-system/commits/chapter_{NNN}.commit.json`。
- state / index / summary / memory / vector 更新状态。
- 备份状态。
- 是否可以继续写下一章。

状态规则：
- `chapter-commit rejected`、任一 `write-gate` failed、projection failed 时，最终状态不得写“已完成”。
- `--fast` 和 `--minimal` 的跳过项必须说明；`--minimal` 跳过审查时归入“已自动处理”或“建议确认”，不得假装已完成完整审查。
- projection retry 发生时必须说明已自动处理和最终结果。

异常分类：
- 已自动处理：projection retry 成功、RAG 临时降级但不影响结果、旧 no-review artifact 被本章新 artifact 覆盖。
- 建议确认：新增角色名 / 设定名、低置信歧义但不阻断、非阻断审查建议。
- 必须处理：blocking issue 未裁决、data artifacts 缺失或 schema 不完整、commit rejected、projection failed。

下一步建议必须使用任务化语言 + 可复制命令，例如：

```text
- 接下来可以写下一章：
  /webnovel-write {next_chapter}
```

不写 token 统计；如需排查故障，只给日志路径或建议运行 `/webnovel-doctor`。
