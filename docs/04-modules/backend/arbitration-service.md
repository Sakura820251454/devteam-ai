# 冲突仲裁模块

**版本**: v1.0
**最后更新**: 2026-05-14

---

## 概述

- **功能定位**：多 Agent 结论冲突的检测、投票、裁决
- **所属层级**：backend
- **代码路径**：`backend/app/services/collaboration/arbitrator.py`

---

## 功能特性

- 自动冲突检测（多 Agent 对同一任务产生不同结论时触发）
- 多轮投票机制（Agree/Disagree/Abstain）
- 元 Agent 裁决（多数反对时由架构师 LLM 做出最终决定）
- 死锁升级人工（投票平局时自动升级）
- 完整仲裁记录（议题、投票、决议全部可追溯）

---

## 核心组件

### ConflictArbitrator

| 方法 | 说明 |
|------|------|
| `detect_conflict(task_id, agent_results)` | 检测结论冲突并创建仲裁议题 |
| `start_arbitration(issue_id)` | 启动仲裁流程，通知相关 Agent |
| `cast_vote(issue_id, agent_id, vote, reasoning)` | Agent 投票 |
| `escalate_to_human(issue_id)` | 将死锁议题升级给人工 |
| `get_issue(issue_id)` | 获取仲裁议题详情 |
| `list_issues(status, task_id)` | 列出仲裁议题 |
| `manually_resolve(issue_id, resolution, resolved_by)` | 人工裁决死锁 |

### ArbitrationStatus 枚举

| 状态 | 说明 |
|------|------|
| `PENDING` | 待处理 |
| `VOTING` | 投票中 |
| `RESOLVED` | 已裁决 |
| `DEADLOCKED` | 死锁，需人工裁决 |

### 仲裁流程

```
检测冲突 → 创建议题 → 启动投票 → Agent 投票 → 裁决
                                              ├── 多数同意 → 通过
                                              ├── 多数反对 → 元 Agent 裁决
                                              └── 平局 → 升级人工
```

---

## 依赖关系

- 依赖：LLM 服务（元 Agent 裁决）、消息总线、Pipeline 编排器
- 被依赖：Pipeline 编排器（Review 阶段）

---

## 相关文档

- [仲裁 API](../../05-api/arbitration.md)
- [团队协作设计](../../02-design/collaboration.md)
