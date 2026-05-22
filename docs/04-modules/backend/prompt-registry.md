# Prompt Registry

**Total prompts**: 46  
**Last updated**: 2026-05-22  
**Version**: 1.0.0  

::: warning 自动生成
本文档由 `scripts/prompt_doc_gen.py` 从 `backend\app\prompts\registry.yaml` 自动生成。
请勿手动编辑。修改 prompt 请编辑 registry.yaml 后重新运行脚本。
:::

## 概述

Prompt Registry 是 DevTeam-AI 中所有 LLM prompt 的**唯一真相源**。
所有 prompt 模板集中管理在此 YAML 文件中，代码通过 `registry.render(id, vars)` 调用。

### 使用方式

```python
from app.services.shared.prompt_registry import registry

prompt = registry.render("agent.executor.plan_steps", {
    "task_title": task.title,
    "task_description": task.description,
})
```

### 命名规范

`{module}.{file_short}.{purpose}[.{variant}]`

---

## Agent Module (17 prompts)

| ID | Description | Variables | Output | Source |
|----|-------------|-----------|--------|--------|
| `agent.executor.plan_steps` | 任务步骤规划用户提示词 — 将任务拆解为 3-8 个步骤，要求 JSON 输出 | task_title, task_description | json | _plan_task_steps |
| `agent.executor.plan_steps_system` | 任务步骤规划 system prompt | — | text | _plan_task_steps |
| `agent.executor.step_prompt.first` | 单步执行用户提示词 — 无前置步骤（第一个步骤） | task_title, step_index, total_steps, step_name, step_description, expected_output | text | _build_step_prompt |
| `agent.executor.step_prompt.continue` | 单步执行用户提示词 — 基于前置步骤继续（有 accumulated_output） | task_title, step_index, total_steps, step_name, step_description, expected_output, accumulated_output | text | _build_step_prompt |
| `agent.executor.task_execution` | 任务执行兜底用户提示词 — 无步骤规划时的完整执行 prompt | task_title, task_description, task_tags | text | _build_task_execution_prompt |
| `agent.executor.fallback_system` | 单步执行 / 兜底执行的回退 system prompt | — | text | _fallback_single_execution |
| `agent.service.chat_fallback` | agent_chat 的回退 system prompt | — | text | agent_chat |
| `agent.service.chat_stream_fallback` | agent_chat_stream 的回退 system prompt | — | text | agent_chat_stream |
| `agent.template.generic` | 通用开发团队成员兜底模板 — 不预设角色 | — | text | get_preset_templates |
| `agent.trait.generate` | Agent 特质分析用户提示词 — 从 soul 定义提取结构化能力特征 | agent_name, principles, rules | json | _generate_trait |
| `agent.trait.generate_system` | Agent 特质分析 system prompt | — | text | _generate_trait |
| `agent.model.intro` | Agent 动态 system prompt — 开篇（姓名/角色/性格） | name, role, title, personality, style | text | build_system_prompt |
| `agent.model.backstory` | Agent 动态 system prompt — 背景（可选段） | backstory | text | build_system_prompt |
| `agent.model.skills` | Agent 动态 system prompt — 专业技能（可选段） | skills_text | text | build_system_prompt |
| `agent.model.knowledge` | Agent 动态 system prompt — 知识领域（可选段） | areas_text | text | build_system_prompt |
| `agent.model.footer` | Agent 动态 system prompt — 结尾 | — | text | build_system_prompt |

### Code-Managed Prompts

以下 prompt 由于逻辑复杂，模板主体保留在 Python 代码中，注册表仅记录信息和位置。

| ID | Description | Source |
|----|-------------|--------|
| `agent.executor.feedback_context` | 可执行反馈上下文 — 失败重试时注入的上下文（code-managed） | _build_feedback_context |

## Collaboration Module (24 prompts)

| ID | Description | Variables | Output | Source |
|----|-------------|-----------|--------|--------|
| `collaboration.pipeline.requirement_analysis` | 需求分析用户提示词 — 单 LLM 兜底方案 | project_name, project_description, requirements | text | _build_requirement_analysis_prompt |
| `collaboration.pipeline.requirement_analysis_system` | 需求分析 system prompt | — | text | _single_llm_requirement_analysis |
| `collaboration.pipeline.merge_analysis_system` | 多 Agent 讨论合并为需求分析报告 — system prompt | — | text | _merge_discussion_into_analysis |
| `collaboration.pipeline.merge_analysis` | 多 Agent 讨论合并为需求分析报告 — 用户提示词 | project_name, project_description, requirements, transcript_text | text | _merge_discussion_into_analysis |
| `collaboration.pipeline.task_breakdown_system` | 任务拆解 system prompt | — | json | _stage_task_breakdown |
| `collaboration.pipeline.task_breakdown` | 任务拆解用户提示词 | project_name, requirements, previous_analysis, agent_info | json | _build_task_breakdown_prompt |
| `collaboration.pipeline.review_system` | 审查 system prompt | — | text | _single_llm_review |
| `collaboration.pipeline.review` | 审查用户提示词 | tasks_summary | text | _build_review_prompt |
| `collaboration.pipeline.merge_review_system` | 多 Agent 审查合并 — system prompt | — | text | _merge_discussion_into_review |
| `collaboration.pipeline.merge_review` | 多 Agent 审查合并 — 用户提示词 | tasks_text, transcript_text | text | _merge_discussion_into_review |
| `collaboration.discussion.agent_speak` | Agent 讨论发言用户提示词 — 主模板（不含最终轮次指令） | topic, context_text, agent_name, role_label, trait_summary, history_text, current_round, max_rounds, final_instruction | text | _build_agent_speak_prompt |
| `collaboration.discussion.agent_speak_fallback_system` | Agent 发言讨论回退 system prompt | — | text | _agent_speak |
| `collaboration.discussion.consensus_check_system` | 共识检查 system prompt | — | text | _check_consensus |
| `collaboration.discussion.consensus_check` | 共识检查用户提示词 | topic, positions_text | json | _check_consensus |
| `collaboration.discussion.summarize_system` | 讨论总结 system prompt | — | text | _summarize_discussion |
| `collaboration.discussion.summarize` | 讨论总结用户提示词 | topic, history, conclusion_type | text | _summarize_discussion |
| `collaboration.discussion.election_system` | Coordinator 选举 system prompt | — | text | _make_election_decision |
| `collaboration.discussion.election` | Coordinator 选举用户提示词 | project_name, project_description, agents_text, speakers_text | json | _make_election_decision |
| `collaboration.arbitrator.meta_resolve_system` | 元 Agent 仲裁 system prompt | — | text | _meta_agent_resolve |
| `collaboration.arbitrator.meta_resolve` | 元 Agent 仲裁用户提示词 | issue_title, issue_description, proposals_text, votes_text | text | _meta_agent_resolve |
| `collaboration.pipeline_templates.adjustment_system` | Pipeline 阶段模板调整 system prompt | — | text | suggest_stage_adjustments |
| `collaboration.pipeline_templates.adjustment` | Pipeline 阶段模板调整用户提示词 | project_name, project_description, template_name, template_description, current_stages | json | suggest_stage_adjustments |
| `collaboration.strategy_recommender.system` | 策略推荐 system prompt | — | text | recommend |
| `collaboration.strategy_recommender.recommend` | 策略推荐用户提示词 | project_name, project_description, requirements, agents_text | json | recommend |

## Execution Module (1 prompts)

| ID | Description | Variables | Output | Source |
|----|-------------|-----------|--------|--------|
| `execution.checkpoint.resume_context` | 检查点恢复执行提示词 | step_index, step_name, partial | text | build_resume_context |

## Shared Module (4 prompts)

| ID | Description | Variables | Output | Source |
|----|-------------|-----------|--------|--------|
| `shared.soul.header` | soul_to_system_prompt — 标题 | — | text | soul_to_system_prompt |
| `shared.soul.core_principles` | soul_to_system_prompt — Core Principles 段落（可选） | principles_lines | text | soul_to_system_prompt |
| `shared.soul.execution_rules` | soul_to_system_prompt — Execution Rules 段落（可选） | rules_lines | text | soul_to_system_prompt |
| `shared.soul.fallback` | soul_to_system_prompt — 无灵魂数据时的回退 | — | text | soul_to_system_prompt |

---

## 版本历史

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2026-05-22 | 从源码迁移，初始注册表创建 |
