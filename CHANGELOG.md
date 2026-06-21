# 更新日志

## v1.0.19 - 废弃 Sub-Agent 独立定义，迁移至 dispatch_task("file-agent")

### 给作者看的变化

- 移除了 4 个废弃的独立 Sub-Agent 定义文件（context-agent / reviewer / data-agent / deconstruction-agent），全部改为 dispatch_task("file-agent") + memory_ids 传递审查约束知识。
- webnovel-write、webnovel-review 的审查与事实提取全部由 file-agent 执行，无需独立 agent 定义。
- README 同步更新：Skills 数量修正为 8，移除 Agent 章节。
- 部署脚本 deploy_to_market.py 移除 agents/ 符号链接逻辑。

### 是否需要改旧项目

不需要。

### 给维护者

- `agents/` 目录已删除。
- `deploy_to_market.py` 中 agents 符号链接代码已移除。
- `_meta.json` / `meta.json` 版本号 bump 至 1.0.19。

### 验证

- `find . -name 'context-agent.md' -o -name 'reviewer.md' -o -name 'data-agent.md' -o -name 'deconstruction-agent.md'` 无结果。
- `grep -rn 'agents/' SKILL.md README.md deploy_to_market.py` 无匹配。

## v1.0.18 - 补回 scripts/ 核心代码目录

发版范围：`v1.0.17..v1.0.18`。

### 给作者看的变化

- 修复 v1.0.17 zip 包缺失 scripts/ 核心代码目录的问题，恢复全部 Python 代码库及 Marvis 适配。

### 是否需要改旧项目

不需要。

### 给维护者

- 从 GitHub 仓库同步补回 scripts/、references/、hooks/、skills/、templates/ 等缺失目录。
- 确保 project_locator.py / config.py 的 Marvis 适配完整保留。

### 验证

- scripts/project_locator.py 包含 MARVIS_PROJECT_DIR / MARVIS_HOME / CURRENT_PROJECT_POINTER_MARVIS。
- scripts/data_modules/config.py 包含 MARVIS_HOME / ~/.marvis 兜底。

## v1.0.17 - 补回 RAG 降级提示表

发版范围：`v1.0.16..v1.0.17`。

### 给作者看的变化

- SKILL.md 补回丢失的 RAG 降级提示表，Agent 可在降级时向用户输出配置引导。

### 是否需要改旧项目

不需要。

### 给维护者

- 从 v1.0.11 已安装版本恢复 SKILL.md 末尾的 RAG 降级提示强制输出表。

### 验证

- SKILL.md 包含 `degraded_mode_reason: "missing_embed_api_key"` 和 `degraded_mode_reason: "rerank_auth_failed"` 两条降级提示。

## v1.0.16 - 打包纯净化

发版范围：v1.0.15..v1.0.16。

- 移除 `assets/dashboard/` 重复构建产物（17 个文件，与 `dashboard/frontend/dist/` 完全重复）。
- 移除被打入 zip 的 `.coveragerc`、`.gitignore`、`scripts/.coveragerc` 等仓库配置私货。
- 打包方式恢复为 `git ls-files` 严格取源，杜绝非 track 文件混入。
- 文件数从 558 减至 459，体积从 6.96 MB 降至约 1.89 MB。

## v1.0.15 - CSV BOM 修复与发布说明补齐

发版范围：`v1.0.14..v1.0.15`。

### 给作者看的变化

- 修复中文 CSV 文件在 zip 打包后丢失 UTF-8 BOM 的问题，现在与源项目完全一致。

### 是否需要改旧项目

不需要。

### 给维护者

- 从源项目同步 references/csv/ 下 9 个中文 CSV 的 BOM 字节。
- 补齐 releases/ 目录缺失的 v1.0.13 / v1.0.14 发布说明。

### 验证

- 9 个中文 CSV 文件与源项目逐字节一致。

## v1.0.14 - 中文文件名编码修复

发版范围：v1.0.13..v1.0.14。

- 修复 zip 打包时中文路径编码损坏问题（templates/genres、references/csv、agents/evals 等目录下的中文文件名经 latin-1/utf-8 误编码后导致文件缺失）
- 新增打包验证脚本，确保中文文件名在 zip 中与源仓库一致

## v1.0.13 - 清理打包污染

发版范围：`v1.0.12..v1.0.13`。

- 移除 22 个外来 skill 目录（v1.0.12 zip 中不慎混入）
- 移除冗余 webnovel-writer 子目录嵌套

这里记录每个正式版本对作者和维护者的影响。发布说明优先面向中文网文作者：先说写作体验有什么变化，再补维护者关心的技术细节。

## v1.0.12 - Marvis 运行时适配与 Rerank 降级检测

发版范围：`v1.0.11..v1.0.12`。

### 给作者看的变化

- 在 Marvis 环境中可直接通过自然语言触发所有创作能力，无需斜杠命令。
- Rerank 不可用时 Agent 会主动提示推荐平台（硅基流动/阿里百炼/Jina AI），不再静默降级。
- 安装包体积精简，仅包含 webnovel-writer 本身。

### 是否需要改旧项目

不需要。

### 给维护者

- **Marvis 运行时适配**（7 处修复）：`project_locator.py` 新增 `MARVIS_PROJECT_DIR` / `MARVIS_HOME` / `WEBNOVEL_MARVIS_HOME` 环境变量识别；`write_current_project_pointer` 双路径写指针（`.webnovel-current-project` 同时写 Marvis 和 Claude Code 位置）；`dashboard/server.py` 双路径读指针；`_pointer_candidates` 加 Marvis 候选；`session_start.py` 环境变量链 `MARVIS_PROJECT_DIR → CLAUDE_PROJECT_DIR → cwd`；`config.py` 兜底路径 `~/.marvis`；`_get_user_claude_root` 兜底路径统一。
- **Rerank 降级检测四层闭环**：`api_client.py` RerankAPIClient 加 `last_error_status` 字段；`rag_adapter.py` `_update_degraded_mode()` 扩展 rerank 检测（主动检测无 Key Jina/Cohere URL + 运行时 rerank 失败追踪）；`extract_chapter_context.py` 输出 `degraded_mode_reason` 字段；`SKILL.md` 新增 `rerank_auth_failed` 降级提示行，推荐硅基流动（月送 200 万 token）、阿里百炼（0.0005 元/千 token）、Jina AI（月送 100 万 token）。
- 清理过时 `.claude` 残留引用，全网扫描确认误伤数为 0。

### 验证

- 7 项 Marvis 适配检查全部通过（导入正常、`_find_workspace_root_with_claude` 优先走 `MARVIS_PROJECT_DIR`、兜底路径正确、`_pointer_candidates` 产出 Marvis pointer、三条核心链路以 `MARVIS_PROJECT_DIR` 为标识）。
- Rerank 降级检测验证：默认配置触发 `rerank_auth_failed`，有 Key 不触发，硅基/百炼 URL 无 Key 不误触发。
- `extract_chapter_context.py` 输出中成功透传 `degraded_mode_reason: rerank_auth_failed`。

## v1.0.11 - 写章结果更清楚，失败后更好恢复

发版范围：`v1.0.10..v1.0.11`。

### 给作者看的变化

- 写章、审查、规划和初始化结束后，最终报告更像写作助手的汇报：会说明已完成、部分完成、需要你处理或未完成。
- `/webnovel-write` 中断后，重复执行同一章会优先检查可信断点，尽量从失败位置继续，减少重写和误覆盖。
- 写章过程减少技术细节打扰；只有创作方向、事实取舍、文件覆盖风险或阻断问题需要裁决时才询问。
- 写作流程的上下文读取更克制，初始化、规划、写章、审查、查询等命令更聚焦，减少无关资料塞满上下文。
- 章节提交前后的中间结果校验更稳，能更早发现缺失的审查、事实提取或故事资料同步结果。
- 文档补充了最终报告读法、恢复边界、日志用途和常见运维入口。

### 是否需要改旧项目

不需要。已有书项目可以继续使用，不需要迁移 `.story-system/` 或 `.webnovel/` 数据。

### 给维护者

- 新增作者术语表、异常目录、审查作者视图、最终报告 helper、写章 run ledger、脱敏 run log。
- 新增 `user-report`、`run-ledger`、`run-log` 统一 CLI 子命令。
- 收紧 commit artifacts、projection writers、write-gate 和 postcommit 的结构化校验。
- 轻量化多个 Skill / Agent 的提示词，补充 reference loading map 和 region-read 规则。
- 增加 prompt integrity、unit tests、behavior eval，覆盖 artifact ownership、最小写章模式、projection retry、blocking review、断点续跑和日志脱敏。
- `Plugin Release` 工作流改为推送到 `master` 后自动发版，并保留手动兜底入口。

### 验证

- 相关 pytest 通过。
- behavior eval 通过。
- `compileall` 通过。
- `git diff --check` 通过。
- 版本同步和插件包校验通过。

## v1.0.10 - 项目体检更稳，出问题更容易定位

- 增加 doctor、project-status、write-gate、projection 重放、hooks、行为评估和插件包校验。
- 强化 Story System 运行时健康检查和 Marketplace 发布校验。

## v1.0.9 - Story System 主链上线，长篇事实更不容易写乱

- 上线合同种子、运行时合同、章节提交、事件审计和投影链路。
- 补齐主链相关集成测试。
