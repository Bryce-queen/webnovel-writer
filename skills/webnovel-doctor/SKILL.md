---
name: webnovel-doctor
description: 对网文项目做只读体检/诊断（/webnovel-doctor）——检查目录、文件、JSON、SQLite、RAG 配置、依赖与 Dashboard 构建产物是否完整。
version: 0.1.0
allowed-tools: read_text shell_executor use_skill
argument-hint: "[--chapter N] [--deep]"
---

# Webnovel Doctor

## 目标

只读诊断当前书项目：确认所处阶段应有的目录、文件、JSON、SQLite、RAG 配置、Python 依赖与 Dashboard 构建产物是否完整。

## 原则

1. 只读诊断：不写项目文件、不自动修复、不安装依赖、不启动 Dashboard。
2. 先 `project-status` 取短状态，再 `doctor` 做阶段感知检查。
3. 统一用 `python -X utf8`，避免中文路径编码问题。
4. 缺失项按 runtime 推导的阶段解释影响与修复建议，不把 init 刚结束的项目按已写多章项目检查。

## 执行

短状态：

```bash
python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" project-status --format summary
```

标准体检：

```bash
python -X utf8 "../webnovel-writer/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" doctor --format text
```

指定章节加 `--chapter {chapter_num}`，深度体检加 `--deep`。

## Jwynia 深度内容诊断（--deep）

> `--deep` 模式下，除标准技术体检外，额外运行以下 jwynia 内容级诊断。每项只读，不落盘。

| 诊断维度 | 触发条件 | 调用 | 产出 |
|---------|---------|------|------|
| 叙事健康度 | `--deep` always | `use_skill("story-sense", task="扫描项目已有的全部章节，按节奏/逻辑/情感三维输出叙事健康度报告")` | 按章节列出的弱点清单 |
| 世界厚度 | `--deep` + 设定集存在 | `use_skill("worldbuilding", task="诊断当前设定集的世界观厚度与一致性：检查是否有设计感缺失、制度非自然演化等问题")` | 世界观诊断报告 |
| 类型合规 | `--deep` + MASTER_SETTING 存在 | `use_skill("genre-conventions", task="校验当前项目是否满足题材的类型惯例，列出差距")` | 类型差距清单与补救建议 |
| 结构完整性 | `--deep` + 多卷/章完成 | `use_skill("plot-structure", task="对已完成卷的剧情弧线做结构诊断：起承转合是否完整、子线是否回收")` | 结构弱点清单 |

> 调用规则：`--deep` 模式下 jwynia 诊断在标准体检之后、最终汇报之前执行；诊断结果与文件级问题合并输出，不单独分段。

## 输出方式

汇报包含：当前 `phase` 与 `target_chapter`、是否有 blocker、缺失或异常文件路径、RAG / Python / Dashboard 配置是否缺失、每个问题的影响和建议修复动作。

不执行真实修复，不展示或要求粘贴 API key。
