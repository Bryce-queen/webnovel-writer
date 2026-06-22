---
name: webnovel-plan
description: 基于总纲生成卷纲、时间线和章纲，并把新增设定增量写回现有设定集。
allowed-tools: read_text write_file edit shell_executor AskUserQuestion use_skill
argument-hint: "[卷号，如 1]"
---

# Outline Planning

主 agent 职责：基于总纲增量细化卷纲/时间线/章纲，把新增设定写回设定集，并刷新 Story System 写作合同。不重做全局故事，不重写整份总纲或设定集。

## 执行原则

1. 只做增量补齐，不重写整份总纲或设定集。
2. 先锁定卷级节奏，再批量拆章。
3. 时间线是硬约束，所有章纲必须带时间字段。
4. 若发现总纲与设定冲突，先阻断，再等用户裁决。
5. 优先级链：用户明确要求 > 总纲核心冲突与卷末高潮 > 时间线硬约束 > skill 默认流程 > reference 建议。

## 阻断条件

- 项目根不合法或总纲缺失。
- 总纲缺少卷名 / 章节范围 / 核心冲突 / 卷末高潮 → 阻断并请求用户补全。
- Step 2 / Step 8 发现设定冲突 → 标记 `BLOCKER`，等待用户裁决。
- 批量拆章时时间回跳且未标注闪回 → 阻断当前批次。
- Step 9 验证失败 → 只重做失败批次，不覆盖整卷。

## 环境准备

```bash
export WORKSPACE_ROOT="{PROJECT_ROOT}"
export SKILL_ROOT="../webnovel-writer"
export SCRIPTS_DIR="../webnovel-writer/scripts"
export PROJECT_ROOT="$(python "../webnovel-writer/scripts/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"

python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" placeholder-scan --format text
```

规划开始 / 结束都运行 `placeholder-scan`；plan 阶段发现占位先警告并补齐相关文件，进入写章前不得保留当前章相关实体的 `[待...]` / `暂名` / `{占位}`。

## 读取策略（按阶段触发，不预读全部 reference）

每个 reference 只在对应 Step 触发时读取，且优先区段读：先用 `Grep` 匹配 `^#{2,4} ` 定位标题锚点行号，再用 `Read` 的 offset/limit 取目标段。

| 触发 | 读取方式 | 文件 |
|------|---------|------|
| Step 4 | 全文 | `$../webnovel-writer/templates/output/大纲-卷节拍表.md` |
| Step 5 | 全文 | `$../webnovel-writer/templates/output/大纲-卷时间线.md` |
| Step 6 always | 区段 | `$../webnovel-writer/references/genre-profiles.md`（仅当前 genre 的 `### 2.x` 段） |
| Step 6 always | 全文 | `$../webnovel-writer/references/shared/strand-weave-pattern.md` |
| 章纲拆分 always | 区段 | `$../webnovel-writer/references/outlining/plot-signal-vs-spoiler.md` |
| Step 6 需要爽点 | 区段 | `$../webnovel-writer/references/shared/cool-points-guide.md` |
| Step 6/7 需要冲突 | 区段 | `$../webnovel-writer/references/outlining/conflict-design.md` |
| Step 6/7 特定节奏 | 区段 | `$../webnovel-writer/references/outlining/genre-volume-pacing.md` |
| Step 7 追读力分析 | 区段 | `$../webnovel-writer/references/reading-power-taxonomy.md` |
| Step 7 章纲细化 + 节点规范 | 区段 | `$../webnovel-writer/references/outlining/chapter-planning.md` |

CSV 创作参考用检索读，不 `cat` 整表：

```bash
python -X utf8 "../webnovel-writer/scripts/reference_search.py" --skill plan --table 爽点与节奏 --query "{卷级核心冲突}" --genre "${GENRE}"
python -X utf8 "../webnovel-writer/scripts/reference_search.py" --skill plan --table 桥段套路 --query "{卷级核心冲突}" --genre "${GENRE}"
python -X utf8 "../webnovel-writer/scripts/reference_search.py" --skill plan --table 命名规则 --query "角色命名" --genre "${GENRE}"
```

## Jwynia 创作技法融合（规划阶段）

> 以下 jwynia 技能由 plan 主流程在对应步骤按需 `use_skill` 调用。**每次调用 task 中均要求以 JSON 格式输出**。产物落盘到 `{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/`，落盘前对 JSON 做 schema 校验（字段/类型），不通过则阻断；下游步骤以 `test -f` + JSON 字段校验双重硬阻断。

| Step | 触发条件 | 调用 | 落盘产物 | 产出描述 |
|------|---------|------|---------|---------|
| Step 2 设定基线补齐 | always | `use_skill("worldbuilding", task="诊断当前设定集（世界观+力量体系）的厚度与一致性，以JSON输出")` | `worldbuilding.json` | 设定诊断（缺漏清单、自然/设计感评估） |
| Step 4 卷节拍表 | 生成节拍表后 | `use_skill("scene-sequencing", task="对第{volume}卷节拍表做场景-续篇节奏分析，以JSON输出")` | `scene_sequencing.json` | 节奏诊断（哪些节拍需要补 Sequel、哪些过于密集） |
| Step 6 卷纲骨架 | 卷纲骨架初稿后 | `use_skill("plot-structure", task="对第{volume}卷的剧情骨架进行结构诊断：卷级起承转合是否完整、Strand交错是否清晰，以JSON输出")` | `plot_structure.json` | 结构弱点清单与修复建议 |
| Step 7 章纲拆分 | 整卷章纲完成后 | `use_skill("story-sense", task="诊断第{volume}卷第{start}-{end}章的叙事健康度，以JSON输出")` | `story_sense.json` | 叙事问题汇总（节奏/逻辑/情感） |
| 卷末收尾 | 卷末钩子设计时 | `use_skill("genre-conventions", task="核定卷末钩子是否满足题材惯例")` | —（不入流水线依赖链） | 类型合规性校验 |

### JSON Schema（落盘时校验，不通过即阻断）

**worldbuilding.json** 必需字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| `assessment` | string | 一致 / 薄弱 / 矛盾 |
| `gaps` | array\[string\] | 设定缺漏清单 |
| `consistency_issues` | array\[string\] | 设定矛盾列表 |
| `recommendations` | array\[string\] | 补全/修复建议 |

**scene_sequencing.json** 必需字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| `pacing_assessment` | string | 过密 / 过疏 / 均衡 |
| `sequels_needed` | array\[string\] | 需要补 Sequel 的节拍 |
| `overdense_scenes` | array\[string\] | 节奏过于密集的节拍 |
| `recommendations` | array\[string\] | 调整建议 |

**plot_structure.json** 必需字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| `arc_completeness` | string | 完整 / 缺失起 / 缺失承 / 缺失转 / 缺失合 |
| `strand_clarity` | string | 清晰 / 混杂 |
| `weak_points` | array\[string\] | 结构弱点 |
| `fixes` | array\[string\] | 修复建议 |

**story_sense.json** 必需字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| `narrative_health` | string | 健康 / 警告 / 严重 |
| `pacing_issues` | array\[string\] | 节奏问题 |
| `logic_gaps` | array\[string\] | 逻辑断层 |
| `emotional_issues` | array\[string\] | 情感断裂 |
| `recommendations` | array\[string\] | 修复建议 |

> 调用规则：Step 触发时主流程必须先 `use_skill` 获取诊断，再将结果纳入后续生成；绝不可跳过诊断直接产出。
> **落盘规则**：前 4 个 jwynia 调用完成后，主流程先对返回文本做 JSON 提取 + `json.load` + schema 字段/类型校验，通过后才写入对应 `.json` 文件。具体落盘命令见各 Step 末尾的 `▸ 诊断产物落盘` 节。未落盘或 schema 失败则下游步骤阻断。

## 流水线文件依赖链

> 每一步的执行必要条件是：上一步的产出文件必须存在。以文件为基准，缺上一步落盘文件直接拒绝执行当前步骤。

| 步骤 | 入口硬校验（上一步产出物） | 本步产出物 | 校验方 |
|------|--------------------------|-----------|--------|
| Step 1 | — | 确认 `state.json`、`总纲.md`、设定集可读 | Agent |
| Step 2 | Step 1 数据已加载 | 更新后设定集文件 | — |
| Step 3 | —（确认范围） | 卷名/范围/核心冲突 | — |
| Step 4 | 总纲 + 设定集数据 | `大纲/第{volume}卷-节拍表.md` | Agent（生成后校验） |
| **Step 5** | **`大纲/第{volume}卷-节拍表.md`**（Step 4 产出） | `大纲/第{volume}卷-时间线.md` | **Agent: `test -f` 节拍表** |
| **Step 6** | **节拍表 + 时间线**（Step 4+5 产出） | 卷纲骨架（内容输入 Step 7） | **Agent: `test -f` 两份文件** |
| **Step 7** | **节拍表 + 时间线 + 卷纲骨架**（Step 4-6 产出） | `大纲/第{volume}卷-详细大纲.md` | **Agent: `test -f` 节拍表+时间线** |
| **Step 8** | **`大纲/第{volume}卷-详细大纲.md`**（Step 7 产出） | 更新后设定集文件 | **Agent: `test -f` 详细大纲** |
| Step 9 | Steps 4-8 全部产出 | plan-commit（原子操作，内置 placeholder-scan + 合同刷新） | `plan-commit` 脚本 + 硬失败条件 |

> **Agent 阻断点（粗体行）**：Step 5/6/7/8 执行前，Agent 必须 `test -f` 校验上一步产出文件存在。不通过则拒绝执行，提示用户先完成上一步。
> **脚本阻断点**：`plan-commit`（Step 9）内置 placeholder-scan 和合同刷新，产出文件缺失会触发硬失败条件。

## 执行流程

### Step 1：加载项目数据并确认前置条件

```bash
# 项目配置/投影状态（兼容读取，不作为写后事实真源）
cat "$PROJECT_ROOT/.webnovel/state.json"

# 总纲（全局蓝图）；确认卷名/章节范围/核心冲突/卷末高潮，不足则阻断
cat "$PROJECT_ROOT/大纲/总纲.md"

# 题材（来自 init 配置快照，后续 CSV 检索和裁决匹配依赖此值）；写后主链真源仍是 .story-system/
GENRE="$(python -X utf8 -c "import json; s=json.load(open('{PROJECT_ROOT}/.webnovel/state.json',encoding='utf-8')); pi=s.get('project_info',{}); print(pi.get('genre') or s.get('project',{}).get('genre',''))")"
```

按需读取设定集：`设定集/世界观.md`、`设定集/力量体系.md`、`设定集/主角卡.md`、`设定集/反派设计.md`、`.webnovel/idea_bank.json`。

**跨卷状态读取**（已有已完成卷，即 `.webnovel/summaries/` 下有文件时必须执行）：

```bash
# 最近 5 章摘要
for ch in $(seq $((START_CH - 5)) $((START_CH - 1))); do
  cat "$PROJECT_ROOT/.webnovel/summaries/ch$(printf '%04d' $ch).md" 2>/dev/null
done

# 核心角色当前状态 / 核心关系当前状态 / 活跃伏笔（跨卷未回收）
python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" knowledge query-entity-state --entity "{protagonist_id}" --at-chapter {上一卷最后章}
python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" knowledge query-relationships --entity "{protagonist_id}" --at-chapter {上一卷最后章}
python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" memory-contract get-open-loops
```

### Step 2：补齐设定基线

让设定集从骨架进入"可规划、可写作"。增量补齐，不清空、不重写整文件；发现冲突先列出并阻断。

- `设定集/世界观.md`：世界边界、社会结构、关键地点用途。
- `设定集/力量体系.md`：境界链、限制、代价与冷却。
- `设定集/主角卡.md`：欲望、缺陷、初始资源与限制。
- `设定集/反派设计.md`：小/中/大反派层级与镜像关系。

**▸ 诊断产物落盘**（worldbuilding 诊断完成后执行）：

```bash
python -c "
import json, sys
raw = '''{use_skill 返回的诊断文本}'''
if raw.strip().startswith('\`\`\`'):
    raw = raw.strip().split('\`\`\`')[1]
    if raw.lower().startswith('json'): raw = raw[4:]
    raw = raw.strip()
data = json.loads(raw)
required = {'assessment', 'gaps', 'consistency_issues', 'recommendations'}
assert required.issubset(data.keys()), f'worldbuilding.json 缺少必需字段，当前: {sorted(data.keys())}'
for k in ['gaps', 'consistency_issues', 'recommendations']:
    assert isinstance(data[k], list), f'worldbuilding.{k} 应为array，实际: {type(data[k]).__name__}'
from pathlib import Path
d = Path('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}')
d.mkdir(parents=True, exist_ok=True)
d.joinpath('worldbuilding.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('worldbuilding.json schema 校验通过，已落盘')
" || { echo "阻断：worldbuilding 诊断 JSON schema 校验失败或落盘异常"; exit 1; }
```

### Step 3：选择目标卷并确认范围

确认卷名、章节范围、核心冲突，以及是否有特殊要求（视角、情感线、题材偏移）。

### Step 4：生成卷节拍表

加载模板 `$../webnovel-writer/templates/output/大纲-卷节拍表.md`。

硬要求：必须填写中段反转，确无则写"无（理由：...）"；危机链至少 3 次递增；卷末新钩子必须能落到最后一章的章末未闭合问题。

输出文件：`大纲/第{volume_id}卷-节拍表.md`

**▸ 诊断产物落盘**（scene-sequencing 诊断完成后执行）：

```bash
python -c "
import json, sys
raw = '''{use_skill 返回的诊断文本}'''
if raw.strip().startswith('\`\`\`'):
    raw = raw.strip().split('\`\`\`')[1]
    if raw.lower().startswith('json'): raw = raw[4:]
    raw = raw.strip()
data = json.loads(raw)
required = {'pacing_assessment', 'sequels_needed', 'overdense_scenes', 'recommendations'}
assert required.issubset(data.keys()), f'scene_sequencing.json 缺少必需字段，当前: {sorted(data.keys())}'
for k in ['sequels_needed', 'overdense_scenes', 'recommendations']:
    assert isinstance(data[k], list), f'scene_sequencing.{k} 应为array，实际: {type(data[k]).__name__}'
from pathlib import Path
d = Path('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}')
d.mkdir(parents=True, exist_ok=True)
d.joinpath('scene_sequencing.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('scene_sequencing.json schema 校验通过，已落盘')
" || { echo "阻断：scene-sequencing 诊断 JSON schema 校验失败或落盘异常"; exit 1; }
```

### Step 5：生成卷时间线表

**前置硬校验**：

```bash
test -f "{PROJECT_ROOT}/大纲/第{volume_id}卷-节拍表.md" || echo "阻断：节拍表不存在（请先完成 Step 4）"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/worldbuilding.json" || echo "阻断：worldbuilding 诊断产物不存在（请先完成 Step 2）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/worldbuilding.json')); assert {'assessment','gaps','consistency_issues','recommendations'}.issubset(d.keys()), 'worldbuilding.json schema不完整'" || echo "阻断：worldbuilding.json schema 校验失败"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/scene_sequencing.json" || echo "阻断：scene-sequencing 诊断产物不存在（请先完成 Step 4）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/scene_sequencing.json')); assert {'pacing_assessment','sequels_needed','overdense_scenes','recommendations'}.issubset(d.keys()), 'scene_sequencing.json schema不完整'" || echo "阻断：scene_sequencing.json schema 校验失败"
```

任一不通过 → 阻断。

加载模板 `$../webnovel-writer/templates/output/大纲-卷时间线.md`。

硬要求：必须明确时间体系与本卷时间跨度；有倒计时事件时列出并标记 D-N。

输出文件：`大纲/第{volume_id}卷-时间线.md`

### Step 6：生成卷纲骨架

**前置硬校验**：

```bash
test -f "{PROJECT_ROOT}/大纲/第{volume_id}卷-节拍表.md" || echo "阻断：节拍表不存在（请先完成 Step 4）"
test -f "{PROJECT_ROOT}/大纲/第{volume_id}卷-时间线.md" || echo "阻断：时间线不存在（请先完成 Step 5）"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/worldbuilding.json" || echo "阻断：worldbuilding 诊断产物不存在（请先完成 Step 2）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/worldbuilding.json')); assert {'assessment','gaps','consistency_issues','recommendations'}.issubset(d.keys()), 'worldbuilding.json schema不完整'" || echo "阻断：worldbuilding.json schema 校验失败"
```

任一不通过 → 阻断。

必读 `$../webnovel-writer/references/genre-profiles.md` 与 `$../webnovel-writer/references/shared/strand-weave-pattern.md`；按需读取爽点 / 冲突 / 节奏 reference（见读取策略表）。

卷纲必须明确：卷摘要、关键人物与反派层级、Strand 分布、爽点密度规划、伏笔规划、约束触发规划。

跨卷一致性检查（非首卷必须执行）：

- 上一卷未回收的伏笔必须出现在新卷伏笔规划中（继续推进或标记回收）。
- 角色关系变化必须延续，不能当上一卷没发生过。
- 主角能力 / 境界必须承接，不回退也不跳级（除非有剧情解释）。

**▸ 诊断产物落盘**（plot-structure 诊断完成后执行）：

```bash
python -c "
import json, sys
raw = '''{use_skill 返回的诊断文本}'''
if raw.strip().startswith('\`\`\`'):
    raw = raw.strip().split('\`\`\`')[1]
    if raw.lower().startswith('json'): raw = raw[4:]
    raw = raw.strip()
data = json.loads(raw)
required = {'arc_completeness', 'strand_clarity', 'weak_points', 'fixes'}
assert required.issubset(data.keys()), f'plot_structure.json 缺少必需字段，当前: {sorted(data.keys())}'
for k in ['weak_points', 'fixes']:
    assert isinstance(data[k], list), f'plot_structure.{k} 应为array，实际: {type(data[k]).__name__}'
from pathlib import Path
d = Path('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}')
d.mkdir(parents=True, exist_ok=True)
d.joinpath('plot_structure.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('plot_structure.json schema 校验通过，已落盘')
" || { echo "阻断：plot-structure 诊断 JSON schema 校验失败或落盘异常"; exit 1; }
```

### Step 7：批量生成章纲

**前置硬校验**：

```bash
test -f "{PROJECT_ROOT}/大纲/第{volume_id}卷-节拍表.md" || echo "阻断：节拍表不存在（请先完成 Step 4）"
test -f "{PROJECT_ROOT}/大纲/第{volume_id}卷-时间线.md" || echo "阻断：时间线不存在（请先完成 Step 5）"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/worldbuilding.json" || echo "阻断：worldbuilding 诊断产物不存在（请先完成 Step 2）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/worldbuilding.json')); assert {'assessment','gaps','consistency_issues','recommendations'}.issubset(d.keys()), 'worldbuilding.json schema不完整'" || echo "阻断：worldbuilding.json schema 校验失败"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/scene_sequencing.json" || echo "阻断：scene-sequencing 诊断产物不存在（请先完成 Step 4）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/scene_sequencing.json')); assert {'pacing_assessment','sequels_needed','overdense_scenes','recommendations'}.issubset(d.keys()), 'scene_sequencing.json schema不完整'" || echo "阻断：scene_sequencing.json schema 校验失败"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/plot_structure.json" || echo "阻断：plot-structure 诊断产物不存在（请先完成 Step 6）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/plot_structure.json')); assert {'arc_completeness','strand_clarity','weak_points','fixes'}.issubset(d.keys()), 'plot_structure.json schema不完整'" || echo "阻断：plot_structure.json schema 校验失败"
```

任一不通过 → 阻断。

批次规则：默认 `10章/批`；复杂题材或多线并进降到 `8章/批`；简单升级流放宽到 `12章/批`；不建议单批超过 `12章`。

按需读取 `$../webnovel-writer/references/reading-power-taxonomy.md` 与 `$../webnovel-writer/references/outlining/chapter-planning.md`。

每章必须包含：目标、阻力、代价、时间锚点、章内时间跨度、与上章时间差、倒计时状态、爽点、Strand、反派层级、视角/主角、关键实体、本章变化、章末未闭合问题、钩子，以及结构化节点 `CBN`、`CPNs`、`CEN`、`必须覆盖节点`、`本章禁区`。

#### 结构化节点

节点格式统一为 `主体 | 动作/变化 | 对象/结果`（写作执行骨架，不追求严格语法 SVO）。完整格式说明、字段细则与示例见 `$../webnovel-writer/references/outlining/chapter-planning.md` 的「结构化节点规范」，按需区段读，不在本文件内联。

核心约束：

- 每章固定 1 个 `CBN`、`2-4 个 CPN`、固定 1 个 `CEN`；`CPNs` 按时间顺序排列。
- 相邻章节 `CEN -> 下一章 CBN` 必须逻辑承接（首章和末章除外）。
- `必须覆盖节点`最多 4 个，建议 `CBN + CEN + 1~2 个核心 CPN`；可选节点只作建议，不作 fail 主依据。
- `本章禁区`不超过 5 条，只写本章绝对不能发生的硬禁区，不写风格类建议。
- 向后兼容：旧项目章纲缺失上述字段时，下游流程正常执行，仅跳过结构化检查。

输出文件：`大纲/第{volume_id}卷-详细大纲.md`

**▸ 诊断产物落盘**（story-sense 诊断完成后执行）：

```bash
python -c "
import json, sys
raw = '''{use_skill 返回的诊断文本}'''
if raw.strip().startswith('\`\`\`'):
    raw = raw.strip().split('\`\`\`')[1]
    if raw.lower().startswith('json'): raw = raw[4:]
    raw = raw.strip()
data = json.loads(raw)
required = {'narrative_health', 'pacing_issues', 'logic_gaps', 'emotional_issues', 'recommendations'}
assert required.issubset(data.keys()), f'story_sense.json 缺少必需字段，当前: {sorted(data.keys())}'
for k in ['pacing_issues', 'logic_gaps', 'emotional_issues', 'recommendations']:
    assert isinstance(data[k], list), f'story_sense.{k} 应为array，实际: {type(data[k]).__name__}'
from pathlib import Path
d = Path('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}')
d.mkdir(parents=True, exist_ok=True)
d.joinpath('story_sense.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('story_sense.json schema 校验通过，已落盘')
" || { echo "阻断：story-sense 诊断 JSON schema 校验失败或落盘异常"; exit 1; }
```

### Step 8：把新增设定写回现有设定集

**前置硬校验**：

```bash
test -f "{PROJECT_ROOT}/大纲/第{volume_id}卷-详细大纲.md" || echo "阻断：详细大纲不存在（请先完成 Step 7）"
test -f "{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/story_sense.json" || echo "阻断：story-sense 诊断产物不存在（请先完成 Step 7）"
python -c "import json; d=json.load(open('{PROJECT_ROOT}/.webnovel/tmp/diagnostics/plan_v{volume}/story_sense.json')); assert {'narrative_health','pacing_issues','logic_gaps','emotional_issues','recommendations'}.issubset(d.keys()), 'story_sense.json schema不完整'" || echo "阻断：story_sense.json schema 校验失败"
```

不通过 → 阻断。

输入：卷节拍表、卷时间线表、卷详细大纲、现有设定集文件。

写回规则：只增量补充相关段落；新角色写入角色卡或角色组；新势力 / 地点 / 规则写入世界观或力量体系；新反派层级写入反派设计。

硬规则：若发现与总纲或既有设定冲突，标记 `BLOCKER` 并停止后续更新。

### Step 9：原子规划提交（plan-commit）⭐

单次调用自动执行：占位扫描 → 总纲写回 → 逐章刷新 Story System 合同 → 更新投影状态 → 运行日志 → 最终报告。物理杜绝漏跑。

```bash
GENRE="$(python -X utf8 -c "import json; s=json.load(open('{PROJECT_ROOT}/.webnovel/state.json',encoding='utf-8')); pi=s.get('project_info',{}); print(pi.get('genre') or s.get('project',{}).get('genre',''))")"

python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" plan-commit \
  --volume {volume_id} \
  --chapters-range "{start}-{end}" \
  --writeback-file "大纲/第{volume_id}卷-总纲写回.json" \
  --genre "${GENRE}"
```

> ⚠️ **已修复**：v1.0.16 起 `plan-commit` 为原子操作，内部依次执行 placeholder-scan → master-outline-sync → 逐章 story-system --emit-runtime-contracts → update-state → run-log → user-report，调用即全量执行。合约刷新失败会打印警告并计数。

## 硬失败条件

- 节拍表 / 时间线表 / 详细大纲不存在或为空。
- 中段反转缺失且未给出理由。
- 任一章节缺少时间字段；时间回跳且未标注闪回；倒计时算术冲突。
- 与总纲核心冲突或卷末高潮明显冲突。
- 存在 `BLOCKER` 未裁决。

## 恢复规则

1. 只重做失败批次，不覆盖整卷文件。
2. 最后一个批次无效时，只删除并重写该批次。
3. 仅在全部验证通过后更新状态。

## 作者友好过程提示与恢复契约

规划开始前先说明本次会经历：检查总纲与设定 -> 生成节拍表 -> 生成时间线 -> 拆章纲 -> 写回新增设定 -> 原子规划提交（合同/投影/日志）。过程提示用作者语言，不直接输出原始 JSON、traceback 或长命令日志；技术详情写入 `.webnovel/logs/run_last.log`（`plan-commit` 内部自动记录）。

过程提示每次不超过两行，只说当前动作和影响，例如"正在拆本卷章纲：会把每章目标、时间锚点和禁区写清楚"。少打扰确认策略：默认继续推进；只有总纲 / 设定冲突、时间线回跳、卷末钩子取舍、需要覆盖已有规划时才询问。

需要用户裁决时使用有限选项，并说明影响。卡住时必须说明卡点、已完成内容和恢复建议，例如"节拍表和时间线已保留，plan-commit 失败；重新运行 `/webnovel-plan {volume_id}` 会从原子提交继续"。

不可恢复故障才在最终报告提示 `.webnovel/logs/run_last.log`；平时只保留日志，不打扰作者。`plan-commit` 已内置 `user-report`，无需单独调用。
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
- `大纲/第{volume_id}卷-节拍表.md`、`大纲/第{volume_id}卷-时间线.md`、`大纲/第{volume_id}卷-详细大纲.md`。
- 新增设定写回了哪些设定集文件。
- `plan-commit` 完成情况（占位/总纲写回/合同刷新/投影更新/日志）。
- 占位符、时间线、节点承接是否通过，合同刷新成功/失败计数。

异常分类：
- 已自动处理：只重做失败批次、补齐非阻断占位、plan-commit 自动重试失败步骤。
- 建议确认：新增角色名、势力名、卷末钩子需要作者看一眼。
- 必须处理：总纲 / 设定冲突、时间线回跳、`BLOCKER` 未裁决、当前章相关占位残留、plan-commit 合同刷新计数异常。

下一步建议必须使用任务化语言 + 可复制命令，例如：

```text
- 接下来可以写第一章：
  /webnovel-write 1
```

不写 token 统计；如需排查故障，只给日志路径或建议运行 `/webnovel-doctor`。
