---
name: webnovel-writer
description: 长篇网文辅助创作系统，提供从初始化设定、卷纲规划、章节写作、质量审查到状态查询的完整创作流程。基于 Story System（合同-提交链）维持长篇一致性，内置 37 个网文题材模板和追读力系统。当用户提到写网文、写小说、写章节、网文大纲、小说设定、角色设计、世界观搭建、网文审查、追读力分析、章节润色、网文题材等时触发。
---

# Webnovel Writer for Marvis

基于 [Bryce-queen/webnovel-writer-marvis](https://github.com/Bryce-queen/webnovel-writer-marvis) 1.0.19的网文创作 skill。

> **如果你是正在安装本技能的 Marvis Agent**，安装流程不可仅复制本目录到 skills/custom/。完整安装步骤：
> ```
> 1. 将本技能目录整体放入 skills/custom/webnovel-writer/
> 2. 执行 bash {SKILL_ROOT}/scripts/install-jwynia-deps.sh — 这会将 deps/jwynia/skills/ 下的 10 个技能写入 skills/market/，缺此步 webnovel 管线无法运行
> 3. 执行 python -m pip install -r {SKILL_ROOT}/scripts/requirements.txt
> 4. 告知用户重启 Marvis
> ```

## 前置依赖：jwynia 技法技能

webnovel-writer 在初始化、规划、写作、审查、学习和体检阶段会调用 jwynia 创作技法技能进行诊断。**安装本技能后，必须同步安装以下 10 个依赖技能**，否则 `use_skill` 调用将失败：

| 技能 | 用途 |
|------|------|
| `story-idea-generator` | 故事核创意发散、金手指差异化 |
| `worldbuilding` | 世界观厚度与一致性诊断 |
| `genre-conventions` | 题材类型惯例校验 |
| `dialogue` | 对话调性、角色声音一致性诊断 |
| `scene-sequencing` | 场景-续篇节奏诊断 |
| `plot-structure` | 剧情弧线结构诊断 |
| `story-sense` | 叙事健康度三维诊断（节奏/逻辑/情感） |
| `prose-style` | 文笔句子层面诊断 |
| `prose-critique` | 对抗性阅读（寻找不奏效之处） |
| `revision` | 修改策略与连锁影响分析 |

> **Agent 行为约束**：首次执行 webnovel 管线前，必须检查以上 10 个技能是否已安装。检查方式：对任一技能（如 `worldbuilding`）调用 `use_skill`，若返回「skill 不可用」或类似错误，说明依赖未安装，**立即停止后续步骤**，向用户输出以下信息后等待用户确认：
> ```
> 检测到 jwynia 创作技法技能未安装。请执行以下命令安装 10 个依赖技能，完成后重启 Marvis：
> 
>   bash {SKILL_ROOT}/scripts/install-jwynia-deps.sh
> 
> 或手动：将 {SKILL_ROOT}/deps/jwynia/skills/ 下各子目录的 SKILL.md 复制到
> ~/Library/Application Support/com.tencent.mac.marvis/MarvisData/User/*/skills/market/{skill-name}/
> 
> 安装完成并重启后，请再次触发创作命令。
> ```

**手动安装方式**：

```bash
bash {SKILL_ROOT}/scripts/install-jwynia-deps.sh
```

## 系统架构

```
用户（作者）→ Marvis（LLM 执行创作）→ CLI 脚本（story-system / chapter-commit / doctor / RAG）
                                    → 文件系统（.story-system / .webnovel / 正文 / 大纲 / 设定集）
```

- **LLM 直接负责**：交互式问答（初始化）、写作（起草章节）、审查（质量评估）、分析（状态查询）
- **Python CLI 负责**：数据持久化（state/index/summary/memory/vector projections）、预检（preflight/doctor）、项目管理（init scaffold）
- **Story System**：`.story-system/` 为唯一事实源头，`accepted CHAPTER_COMMIT` 驱动 `.webnovel/` 投影

## 技能根目录

本 skill 安装后，所有脚本和资源路径以 skill 根目录为基准。引用脚本时使用 `{SKILL_ROOT}/scripts/`，引用参考时使用 `{SKILL_ROOT}/references/`，引用模板时使用 `{SKILL_ROOT}/templates/`。

## 8 大核心能力

### 1. 深度初始化（webnovel-init）

触发：用户说"初始化一本书"、"创建新小说项目"、"帮我搭书框架"等。

流程：
1. 询问书名、题材、核心卖点、目标字数
2. 询问角色、世界观、力量体系（分批交互，每次只问缺失项）
3. 询问是否提供参考书拆解（灵感来源）
4. 收集充分后执行脚手架初始化：
   ```bash
   python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" init --name "{书名}" --genre "{题材}" --word-count {目标字数}
   ```
5. 交互生成设定集/总纲/角色卡并写入对应目录

产出目录结构：
```
{项目根}/
├── .story-system/        # 合同、章节提交和事件审计
├── .webnovel/            # 状态、索引、摘要、备份和长期记忆
├── 正文/                  # 章节正文
├── 大纲/                  # 总纲、卷纲、时间线和章纲
├── 设定集/                # 世界观、角色、力量体系等设定
└── 审查报告/              # 章节审查报告
```

### 2. 卷纲规划（webnovel-plan）

触发：用户说"规划第X卷"、"拆卷纲"、"写大纲"等。

流程：
1. 执行预检确认项目根合法
2. 读取已有总纲和设定集
3. 基于总纲拆解指定卷的章节目录、时间线和节奏
4. 写入 `大纲/卷_{NNN}纲.md` 和各章章纲
5. 如有新增设定，写回设定集
6. 执行：
   ```bash
   python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" update-master-outline
   ```

### 3. 章节创作（webnovel-write）

触发：用户说"写第X章"、"继续下一章"、"写一章关于..."等。

完整流水线：
1. **预检**：项目根、Story System 健康、占位符扫描
2. **刷新合同**：解析详细大纲获取本章目标，刷新 runtime contract
3. **准备上下文**：提取前章摘要、相关设定、伏笔状态、RAG 检索
4. **起草正文**：基于写作任务书（章纲约束 > 禁区 > 风格指引 > 动态上下文）起草 2000-2500 字
5. **质量审查**：从爽点、一致性、节奏、OOC、连贯性、追读力等维度审查
6. **润色与排雷**：排版、Anti-AI 终检
7. **提交事实**：提取新事实，执行原子提交链（预检→评分落库→提交→投影→后检→日志→备份→最终报告，7 步全自动）：
   ```bash
   python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" chapter-commit --chapter {章号} --commit-file "{commit_path}"
   ```

章节字数：默认 2000-2500 字，用户另有要求从之。

### 4. 质量审查（webnovel-review）

触发：用户说"审查第X章"、"检查质量"、"review 一下"等。

审查维度：爽点密度、一致性（战力/时间线/规则）、节奏张力、OOC 检测、连贯性、追读力指标。

流程：
1. 加载目标章节正文
2. 加载相关设定和章纲约束
3. 逐维度评分（1-10），标记 blocking issues
4. 生成结构化审查报告
5. 写入审查指标：
   ```bash
   python -X utf8 "{SKILL_ROOT}/scripts/review_pipeline.py" --project-root "{PROJECT_ROOT}" --chapter {章号} --save-metrics
   ```

### 5. 状态查询（webnovel-query）

触发：用户问"XX角色现在什么状态"、"有哪些未回收的伏笔"、"战力体系总结"等。

流程：
1. 读取 `.webnovel/state.json` 获取项目全局状态
2. 查询指定实体（角色/伏笔/地点/物品）信息
3. 可用 CLI 辅助：
   ```bash
   python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" story-events --entity "{实体名}"
   python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" memory --query "{关键词}"
   ```

### 6. 项目学习（webnovel-learn）

触发：用户说"记住这个写法"、"这段经验不错，存下来"等。

将好的写作经验存入项目长期记忆：
```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" memory --add "{经验内容}"
```

### 7. 可视化面板（webnovel-dashboard）

触发：用户说"打开面板"、"看dashboard"、"项目概览"等。

Dashboard 只读，展示项目状态、实体关系图、章节内容和追读力数据：
```bash
# 启动本地 HTTP 服务
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" dashboard-serve --port 0
```

### 8. 项目体检（webnovel-doctor）

触发：用户说"检查项目健康"、"体检"、"为什么报错了"等。

```bash
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" preflight
python -X utf8 "{SKILL_ROOT}/scripts/webnovel.py" --project-root "{PROJECT_ROOT}" doctor --format text
```

## 关键资源

### 命令行入口

所有运维命令统一从 `scripts/webnovel.py` 进入。常用子命令：

| 子命令 | 说明 |
|--------|------|
| `where` | 打印当前解析出的书项目根目录 |
| `preflight` | 校验插件路径、项目根、Story System 健康状态 |
| `project-status` | 输出机器可读短状态、phase 和下一步 |
| `doctor` | 阶段感知项目体检 |
| `write-gate` | 写前/提交前/提交后三个边界校验 |
| `projections` | 基于已有 commit 补跑或重放投影 |
| `story-system` | 生成合同种子和 runtime contracts |
| `chapter-commit` | 提交章节事实并驱动投影 |
| `story-events` | 查询章节事件或检查事件链健康 |
| `memory` | 查看、查询、导出和回填长期记忆 |
| `rag` | 管理向量索引和检索状态 |

### 37 个内置题材

参见 `templates/genres/`。写作时根据选中题材加载对应模板作为风格参考。

### RAG 配置

项目根目录下 `.env` 文件配置 Embedding 和 Rerank API（可选，无配置时自动退回 BM25 关键词检索）：

```
EMBED_BASE_URL=https://your-embed-api
EMBED_MODEL=your-model
EMBED_API_KEY=your-key
RERANK_BASE_URL=https://your-rerank-api
RERANK_MODEL=your-model
RERANK_API_KEY=your-key
```

## 创作原则

1. **事实不可漂移**：每章写完必须提取事实、过审、存档，写入 Story System
2. **约束优先**：章纲约束 > 禁区 > 风格指引 > 动态上下文
3. **用户裁决**：创作方向、事实一致性、文件覆盖风险、blocking issue 需要用户确认
4. **只写一章**：每次 `/webnovel-write` 只写一章，不并步不跳步
5. **失败不盲重试**：失败时先诊断原因，补跑失败步骤，不回退已完成的步骤

## 参考文档索引

| 场景 | 参考文件 |
|------|----------|
| 初始化采集字段 | `skills/webnovel-init/references/init-collection-schema.md` |
| 题材模板详情 | `templates/genres/{题材名}.md` |
| 审查维度详解 | `references/review-schema.md` / `references/review/blocking-override-guidelines.md` |
| 追读力系统 | `references/shared/cool-points-guide.md` |

| RAG 配置详解 | `docs/guides/rag-and-config.md` |

## 环境依赖

首次使用前需安装 Python 依赖：
```bash
pip install -r {SKILL_ROOT}/scripts/requirements.txt
```

核心依赖：Python 3.10+，无需 GPU。

## RAG 降级提示（强制）

**Agent 必须在以下任一降级发生时，向用户输出对应提示**（同会话首次降级提示一次，后续不重复）：

| 检测标记 | 含义 | Agent 必须输出的提示 |
|----------|------|---------------------|
| `degraded_mode_reason: "missing_embed_api_key"` | 未配置 Embedding API Key，语义检索不可用 | 「未检测到 Embedding API Key，RAG 已降级为 BM25 关键词检索（精确匹配，不支持语义扩展）。如需语义检索，可配置免费 API：Jina AI（月送 100 万 token，`jina-embeddings-v3`）或硅基流动（月送 200 万 token，`BAAI/bge-m3`）。配置方式见 `docs/guides/rag-and-config.md`。」 |
| `degraded_mode_reason: "rerank_auth_failed"` | 未配置或 Rerank API Key 无效，精排不可用 | 「未检测到有效的 Rerank API Key，RAG 精排已降级为 RRF 融合（排序精度下降，但检索仍可用）。建议配置以下任一免费平台恢复精排：\n- **硅基流动**（`RERANK_BASE_URL=https://api.siliconflow.cn/v1`，`RERANK_MODEL=BAAI/bge-reranker-v2-m3`，月送 200 万 token）\n- **阿里百炼**（`RERANK_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1`，`RERANK_MODEL=qwen3-rerank`，0.0005 元/千 token）\n- **Jina AI**（`RERANK_BASE_URL=https://api.jina.ai/v1`，`RERANK_MODEL=jina-reranker-v3`，月送 100 万 token）\n\n配置方式：在项目根目录创建 `.env` 文件并写入上述环境变量，见 `docs/guides/rag-and-config.md`。」 |
| `mode: "bm25_fallback"` | RAG 当前工作在 BM25 模式 | 同上 |
| `reason: "missing_embed_api_key"` | 同 `degraded_mode_reason` | 同上 |
| `reason` 含 `auto_failed` | 自动模式失败后回退到 BM25 | 「RAG 自动模式异常（{reason}），已自动回退为 BM25 关键词检索，本轮结果可能不完整。」 |

**检测规则**：`extract_chapter_context.py` 输出 JSON 中包含 `"mode": "bm25_fallback"` 或 `"reason": "missing_embed_api_key"` 或 `"degraded_mode_reason": "missing_embed_api_key"` 或 `"degraded_mode_reason": "rerank_auth_failed"` 任一字段时触发。Agent 需逐条解析工具输出并匹配上述规则。
